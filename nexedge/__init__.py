"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

# data format
import json

# compression
import zlib
from zlib import compress, decompress
# from lzma import compress, decompress
import base64

# future
import concurrent.futures

# pyserial
import serial
import serial.threaded

# local stuff
from . import receiver, sender, pcip_commands, exceptions
from .sender import send_command
from .pcip_commands import *
from .exceptions import *


# the requests library returns a future with the method raise for status which raises the HTTP error code
# we do not need such fuzz here, future.result() will raise if there was a problem, but the method has to be implemented
# code is commented out because it is not clear if needed
def raise_for_status(future):
    """
    Mimic futures returned by requests.
    Raise the exception if future.result() ends in one.
    """

    if future.exception() is not None:
        raise future.exception()
    else:
        return None

# patch it to concurrent.futures.Future in runtime
# setattr(concurrent.futures.Future, "raise_for_status", classmethod(raise_for_status))


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
    """
    Main radio communication object. Can be used in a with statement.

    Example:
        with Radio(serialcon=ser, max_chunk_size=4096) as radio:
            do_something()
    """

    def __init__(self,
                 serial_port: str = "/dev/ttyUSB0",
                 max_chunk_size: int = 4096,
                 compression: bool = True):
        """
        This method starts all threads and maps the queues.
        If no serial port is given, the default configuration for raspberry pi will be used (/dev/ttyAMA0).
        :param serial_port: str
        :param max_chunk_size: int
        :param compression: bool = True
        """

        # setting up serial connection
        self.serial_connection = serial.Serial(serial_port)
        self.serial_connection.baudrate = 9600
        self.serial_connection.parity = serial.PARITY_NONE
        self.serial_connection.stopbits = serial.STOPBITS_TWO
        self.serial_connection.bytesize = serial.EIGHTBITS

        self.max_chunk_size = max_chunk_size
        self.compression = compression


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
        # setting up a pool for unifying received chunks, there should be only 1 worker working at a time
        self.unite_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def __enter__(self):
        """
        Necessary for usage in with clause
        :return: self
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Teardown method.
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        # stop threads
        self.stop()
        # exit ReaderThread
        self.protocol.__exit__(exc_type, exc_val, exc_tb)

    def stop(self):
        """
        Stops ReaderThread and the pools.
        :return:
        """
        # stop unifying pool
        self.unite_pool.shutdown()

        # stop the sender pool
        self.send_pool.shutdown()

        # stop ReaderThread
        self.protocol.stop()

    def send(self, data: dict, target: bytes, **kwargs) -> concurrent.futures.Future:
        """
        Send json encoded data via radio. The target uid is expected as bytes.
        The method returns a future with will resolve once the sending is finished.
        It resolves to either a bool or raises an exception.
        :param data: dict
        :param target: bytes
        :param kwargs:
        :return: concurrent.futures.Future
        """
        # get str representation of data
        data_str = json.dumps(data, separators=(',', ':'))  # compact
        data_bytes = data_str.encode()

        # # checksum generation
        # data_cs_int = zlib.crc32(data_bytes)
        #
        # # checksum encoding to 4 bytes
        # data_cs_bytes = data_cs_int.to_bytes(4, "big")

        # compression with zlib or lzma
        if self.compression:
            data_compressed = compress(data_bytes)
        else:
            data_compressed = data_bytes

        data_encoded = base64.b64encode(data_compressed)

        chunks = [c for c in
                  # split_to_chunks(data=data_compressed, chunksize=(self.max_chunk_size - 8 - 4))]  # make room for flag
                  split_to_chunks(data=data_encoded, chunksize=(self.max_chunk_size - 8))]  # make room for flag

        # first chunk starts with b'json' and last chunk ends with b'json'
        chunks[0] = b'json' + chunks[0]
        # chunks[-1] = chunks[-1] + data_cs_bytes + b'json'
        chunks[-1] = chunks[-1] + b'json'

        future = self.send_pool.submit(send_command,
                                       [longMessage2Unit(unitID=target, message=c) for c in chunks],
                                       self.protocol,
                                       self.channel_status,
                                       self.transmission_queue,
                                       **kwargs)

        return future

    def get(self, **kwargs) -> concurrent.futures.Future:
        """
        Receive data via radio.
        The method returns a future with will resolve once a complete data set is received in the anwer_queue.
        It resolves to either a dict or raises an exception.
        :param kwargs:
        :return: concurrent.futures.Future
        """
        # submit a task to the pool, when a complete data set is retrieved, the future will resolve
        # if the timeout (default 60s) per chunk is reached, the queue.Empty exception will be raised in the future
        future = self.unite_pool.submit(receiver.unite,
                                        self.answer_queue,
                                        self.compression,
                                        **kwargs)

        return future

    def is_alive(self, **kwargs):
        """
        Determines if the Radio connection is alive.
        :return: bool
        """

        # try to send a dumb getChannelStatus with small timeout, catch error
        # we ignore a channel status here

        future = self.send_pool.submit(send_command,
                                       [getChannelStatus()],
                                       self.protocol,
                                       self.channel_status,
                                       self.transmission_queue,
                                       max_retries=1,
                                       channel_timeout=2,
                                       confirmation_timeout=10,
                                       force_send=True,
                                       **kwargs)

        try:
            # will be true if successful
            return future.result()
        except exceptions.SenderException:
            # serial port is open
            return True
        except serial.SerialException:
            return False
        except:
            # something happened
            return False
