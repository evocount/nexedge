"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

import serial.threaded
from queue import Queue
import receiver
import threading


def send_worker(
        sender_queue: Queue,
        protocol: serial.threaded.ReaderThread,
        channel_status: receiver.ChannelStatus,
        transmission_queue: Queue,
        stop_event = threading.Event):
    """
    For use in a thread, reads the sender queue objects and writes to the serial port via the ReaderThread, but only
    if the channel is free.
    :param sender_queue: 
    :param protocol: 
    :param channel_status: 
    :param transmission_queue:
    :return: 
    """
    while not stop_event.is_set():
        for m in iter(sender_queue.get, None):
            # print(m)
            command_send = False
            """
            Explaining this loop here a bit:
            we like to send a command, but the the channel can be occupied -> case 1 wait time t
            command was sent but there is no confirmation yet -> case 2.1 wait time t
            queue is empty and command was not sent yet -> case 2.2 sent command and change variable to True
            we got an error message -> case 3 sent again in next iteration by setting the flag to False
            
            In the first iteration case 2.2 should be triggered!
            """
            while True:
                # channel is not free, do not attempt to send
                if not channel_status.is_free():
                    # print("waiting for channel to become free")
                    stop_event.wait(timeout=0.1)
                    continue

                # command is sent, but no success or error message yet
                if transmission_queue.empty() and command_send:
                    # print("waiting for sending conformation")
                    stop_event.wait(timeout=0.1)
                    continue
                elif transmission_queue.empty() and not command_send:
                    protocol.write(m)
                    command_send = True
                    # print("sending {}".format(m))
                    continue

                # we got an error, send again in next loop
                if not transmission_queue.get():
                    command_send = False
                    # print("sending error")
                    continue
                else:  # command was successful
                    # print("sending successful")
                    break

        #  wait time t before looking at the queue again/it ran empty before
        stop_event.wait(timeout=0.1)
