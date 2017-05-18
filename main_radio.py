#!/usr/bin/python3

import json
import time
import serial
import serial.threaded
import threading
from queue import Queue
import receiver
import sender
import radio_commands


testnachricht = "Hallo Welt hier spricht EvoCount"

# load serial configuration from json formatted file
with open("config.json", "r") as fpointer:
    config = json.load(fpointer)

ser = serial.Serial(config["serial"]["port"])  # as str in config.json
ser.baudrate = config["serial"]["baudrate"]  # as int in config.json
ser.parity = eval(config["serial"]["parity"])  # we have to evaluate the code in the file
ser.stopbits = eval(config["serial"]["stopbits"])
ser.bytesize = eval(config["serial"]["bytesize"])

# Setting up queueing
sender_q = Queue(maxsize=0)

# Setting up th reader thread
protocol = serial.threaded.ReaderThread(ser, receiver.NexedgePacketizer)

with protocol as receiver:
    # Setting up sender thread
    sender_thread = threading.Thread(target=sender.send_worker,
                                     args=(sender_q, protocol, receiver.channel_status, receiver.transmission_queue,)
                                     )
    sender_thread.setDaemon(True)
    sender_thread.start()

    # queue up a message
    sender_q.put(radio_commands.longMessage2Unit(b"00011", testnachricht.encode()))

    # loop until the answer_queue is None, this never happens
    for m in iter(receiver.answer_queue.get, None):
        # if we got a message, reply!
        if "hallo" not in m.decode():  # do not produce a infinite loop
            # 3 items to check if sending part works with multiple items in queue
            sender_q.put(("\x02" + "g" + "G" + "U" + "00011" + "hallo alice" + "\x03").encode())
            sender_q.put(("\x02" + "g" + "G" + "U" + "00011" + "hallo bob" + "\x03").encode())
            sender_q.put(("\x02" + "g" + "G" + "U" + "00011" + "hallo carol" + "\x03").encode())

        # debugging output
        print("message: {}". format(m.decode()))
        print("channel free: {}".format(receiver.channel_status.is_free()))
        print("queue size: answer={}\tsender={}".format(receiver.answer_queue.qsize(), sender_q.qsize()))
