"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

# pyserial
import serial.threaded

# queues
from queue import Queue

# local stuff
from . import receiver, exceptions
from .exceptions import *

# timer
import time
from random import randint


def send_command(
        commandlist: [bytes],
        protocol: serial.threaded.ReaderThread,
        channel_status: receiver.ChannelStatus,
        transmission_queue: Queue,
        max_retries: int = 2,
        channel_timeout: int = 30,
        confirmation_timeout: int = 60,
        occupied_snooze: int = 1,
        confirmation_snooze: int = 1,
        retry_snooze: int = 20) -> bool:
    """
    Sends a List of radio commands via serial. Returns True if success, else an exception is raised.
    :param commandlist:
    :param protocol: 
    :param channel_status:
    :param transmission_queue:
    :param max_retries:
    :param channel_timeout:
    :param confirmation_timeout:
    :param occupied_snooze:
    :param confirmation_snooze:
    :param retry_snooze:
    :return: 
    """
    for command in commandlist:
        success = False
        command_send = False

        # number of tries for sending
        send_tries = -1

        # since when do we try to get a free channel
        time_channel = time.time()

        while not success:
            # optimal start condition -> send command
            if not command_send and channel_status.is_free_timed():
                protocol.write(command)
                command_send = True
                send_tries += 1
                time_send = time.time()
                # print("sending {}".format(m))
                continue
            # channel_status is False -> check for timeout
            elif not command_send:
                # channel is timed out -> abort
                if (time_channel + channel_timeout) <= time.time():
                    # raise Error
                    raise ChannelTimeout
                # no timeout -> go to sleep
                else:
                    time.sleep(occupied_snooze)
                    print("channel occupied, slept for {}s".format(occupied_snooze))
                    continue

            # at this point command_send is always True, because the above catches all cases for False

            # no confirmation yet -> check for timeout
            if transmission_queue.empty():
                # confirmation is times out -> abort
                if (time_send + confirmation_timeout) <= time.time():
                    # raise Error
                    raise ConfirmationTimeout
                # no timeout -> got to sleep
                else:
                    time.sleep(confirmation_snooze)
                    print("no confirmation yet, slept for {}s".format(confirmation_snooze))
                    continue
            # confirmation error -> check for max_retries
            elif not transmission_queue.get():
                # print("sending error")
                # max_retries reached -> abort
                if send_tries >= max_retries:
                    # raise Error
                    raise SendMaxRetries
                # -> try again in the next loop
                else:
                    command_send = False
                    # wait for a random fraction of 20 seconds
                    snooze = randint(1, retry_snooze*10)/10
                    time.sleep(snooze)
                    # reset the channel timeout
                    time_channel = time.time()
                    print("retry after {}s".format(snooze))
                    continue
            # confirmation success -> success
            else:
                # a sign of success!
                success = True

    # we got through the loop!
    return True
