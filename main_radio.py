#!/usr/bin/python3

import json
import time
import serial
import serial.threaded
import threading
from queue import Queue
import receiver
import sender
from radio_commands import *


def split_to_chunks(data: bytes, chunksize: int):
    """"
    takes data (type bytes) and chunksize (type int)
    splits data into chunks with max. size of chunksize
    yields a chunk (type bytes)
    """

    # type checking
    if type(data) is not bytes or type(chunksize) is not int:
        raise TypeError("type(data)={} type(chunksize)={}".format(type(data), type(chunksize)))

    for i in range(0, len(data), chunksize):
        yield data[i:i + chunksize]


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
# sender_q = Queue(maxsize=0)
#
# # Setting up th reader thread
# protocol = serial.threaded.ReaderThread(ser, receiver.NexedgePacketizer)
#
# with protocol as receiver:
#     # Setting up sender thread
#     sender_thread = threading.Thread(target=sender.send_worker,
#                                      args=(sender_q, protocol, receiver.channel_status, receiver.transmission_queue,)
#                                      )
#     sender_thread.setDaemon(True)
#     sender_thread.start()
#
#     # queue up a message
#     sender_q.put(longMessage2Unit(b"00011", testnachricht.encode()))
#
#     # loop until the answer_queue is None, this never happens
#     for m in iter(receiver.answer_queue.get, None):
#         # if we got a message, reply!
#         if "hallo" not in m.decode():  # do not produce a infinite loop
#             # 3 items to check if sending part works with multiple items in queue
#             sender_q.put(("\x02" + "g" + "G" + "U" + "00011" + "hallo alice" + "\x03").encode())
#             sender_q.put(("\x02" + "g" + "G" + "U" + "00011" + "hallo bob" + "\x03").encode())
#             sender_q.put(("\x02" + "g" + "G" + "U" + "00011" + "hallo carol" + "\x03").encode())
#
#         # debugging output
#         print("message: {}". format(m.decode()))
#         print("channel free: {}".format(receiver.channel_status.is_free()))
#         print("queue size: answer={}\tsender={}".format(receiver.answer_queue.qsize(), sender_q.qsize()))


class Radio(object):
    # setting up sender queue
    sender_queue = Queue(maxsize=0)

    # setting up data queue, json data goes here
    data_queue = Queue(maxsize=0)

    def __init__(self, ser: serial.Serial, max_chunk_size: int=4096):
        self.serial_connection = ser
        self.max_chunk_size = max_chunk_size

        # Setting up th reader thread
        self.protocol = serial.threaded.ReaderThread(self.serial_connection, receiver.NexedgePacketizer)

        # get the instance
        self.receiver = self.protocol.__enter__()

        # Setting up sender thread
        self.sender_thread = threading.Thread(target=sender.send_worker,
                                              args=(self.sender_queue,
                                                    self.protocol,
                                                    self.receiver.channel_status,
                                                    self.receiver.transmission_queue,
                                                    )
                                              )
        self.sender_thread.setDaemon(True)
        self.sender_thread.start()

        # mapping queue
        self.answer_queue = self.receiver.answer_queue
        self.status_queue = self.receiver.status_queue

        # the answer_queue consists of json chunks, we need a thread to unite the chunks to valid json data
        # checksum validation would go there
        # Setting up unite thread
        self.unite_thread = threading.Thread(target=receiver.unite_worker,
                                             args=(self.answer_queue,
                                                   self.data_queue,
                                                   )
                                             )
        self.unite_thread.setDaemon(True)
        self.unite_thread.start()

    def send(self, data: dict, target: bytes):
        # get str representation of data
        data_str = json.dumps(data, separators=(',', ':'))  # compact
        data_bytes = data_str.encode()

        chunks = [c for c in split_to_chunks(data=data_bytes, chunksize=(self.max_chunk_size-8))]  # make room for flag

        # first chunk starts with b'json' and last chunk ends with b'json'
        chunks[0] = b'json' + chunks[0]
        chunks[-1] = chunks[-1] + b'json'

        for c in chunks:
            command = longMessage2Unit(unitID=target, message=c)
            self.sender_queue.put(command)

    def get(self) -> dict or None:
        return None if self.data_queue.empty() else self.data_queue.get()
