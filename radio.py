"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

import json
import serial
import serial.threaded
import threading
from queue import Queue
import receiver
from sender import send_command
from pcip_commands import *
import concurrent.futures


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
    # setting up data queue, json data goes here
    data_queue = Queue(maxsize=0)

    def __init__(self,
                 serialcon: serial.Serial,
                 max_chunk_size: int):
        self.serial_connection = serialcon
        self.max_chunk_size = max_chunk_size

        # Setting up th reader thread
        self.protocol = serial.threaded.ReaderThread(self.serial_connection, receiver.NexedgePacketizer)

        # get the instance
        self.receiver = self.protocol.__enter__()

        self.channel_status = self.receiver.channel_status
        self.transmission_queue = self.receiver.transmission_queue

        # setting up a pool for sending, only 1 worker because only one send at a given time
        self.send_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        # mapping queue
        self.answer_queue = self.receiver.answer_queue
        self.status_queue = self.receiver.status_queue

        # the answer_queue consists of json chunks, we need a thread to unite the chunks to valid json data
        # checksum validation would go there
        # Setting up unite thread
        self.unite_stop = threading.Event()
        self.unite_thread = threading.Thread(target=receiver.unite_worker,
                                             args=(self.answer_queue,
                                                   self.data_queue,
                                                   self.unite_stop)
                                             )
        self.unite_thread.setDaemon(True)
        self.unite_thread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # stop threads
        self.stop()
        # exit ReaderThread
        self.protocol.__exit__(exc_type, exc_val, exc_tb)

    def stop(self):
        # stop unite_worker
        self.unite_stop.set()

        # stop the sender pool
        self.pool.shutdown()

        # stop ReaderThread
        self.protocol.stop()

    def send(self, data: dict, target: bytes, **kwargs) -> concurrent.futures.Future:
        # get str representation of data
        data_str = json.dumps(data, separators=(',', ':'))  # compact
        data_bytes = data_str.encode()

        chunks = [c for c in
                  split_to_chunks(data=data_bytes, chunksize=(self.max_chunk_size - 8))]  # make room for flag

        # first chunk starts with b'json' and last chunk ends with b'json'
        chunks[0] = b'json' + chunks[0]
        chunks[-1] = chunks[-1] + b'json'

        future = self.send_pool.submit(send_command,
                                       [longMessage2Unit(unitID=target, message=c) for c in chunks],
                                       self.protocol,
                                       self.channel_status,
                                       self.transmission_queue,
                                       **kwargs)

        return future

    def get(self) -> dict or None:
        return None if self.data_queue.empty() else self.data_queue.get()
