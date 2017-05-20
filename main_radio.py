#!/usr/bin/python3

import json
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


class Radio(object):
    # setting up sender queue
    sender_queue = Queue(maxsize=0)

    # setting up data queue, json data goes here
    data_queue = Queue(maxsize=0)

    def __init__(self, serialcon: serial.Serial, max_chunk_size: int=4096):
        self.serial_connection = serialcon
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.protocol.__exit__()

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
