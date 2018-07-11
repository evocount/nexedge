"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

# pyserial
import serial.threaded
import asyncio
import serial_asyncio
from six import iterbytes, int2byte
from functools import partial
import logging

# compression
import zlib
from zlib import compress, decompress
# from lzma import compress, decompress
import base64

# timer
import time

# data model
import json

# queues
import queue
from asyncio import Queue

# local stuff
from . import exceptions
from .exceptions import *


class ChannelStatus:
    """
    This class contains the status of the radio channel as indicated by the led.
    """
    _channel_free = True
    _radio_status = "unknown"
    _time_unfree = time.time()
    # when did we receive a package for the last time
    _time_last_updated = 0

    def __init__(self, free_threshold: int = 2):
        """
        Initialize Object.
        Threshold sets the time in seconds in which the channel has to be clear before it is considered really free.
        :param free_threshold: int
        """
        self.free_threshold = free_threshold

    def update(self):
        """
        Update the time on this object.
        """
        self._time_last_updated = time.time()

    def free(self):
        """
        True if channel is free (led off) and was free for the last self.free_threshold seconds (default = 2s).
        :return: bool
        """
        return self._channel_free and \
               (time.time() - self.free_threshold > self._time_unfree)

    def set_free(self):
        self._channel_free = True
        self._radio_status = "off"

    def set_unfree(self, status):
        """
        Sets self.channel_free to False and the radio status to a human readable string, the time when the channel goes
        unfree is stored.
        :param status: str
        :return:
        """
        self._channel_free = False
        self._time_unfree = time.time()
        self._radio_status = status

    def set_red(self):
        self.set_unfree("sending")

    def set_green(self):
        self.set_unfree("receiving")

    def set_orange(self):
        self.set_unfree("idle")


class Output(asyncio.Protocol):

    START = b'\x02'
    STOP = b'\x03'

    _buffer = b""

    _transport = None

    _channel = None
    _queue = None

    def __init__(self, queue: asyncio.Queue,  logger: logging.Logger=None):
        # get a logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        # queue setup
        self._queue = asyncio.Queue()

        # set up a channel object
        self._channel = ChannelStatus()

    @property
    def queue(self):
        if self._queue is None:
            raise Exception
        return self._queue

    @property
    def transport(self):
        if self._transport is None:
            raise Exception
        return self._transport

    @property
    def channel(self):
        return self._channel

    def _increase_baud(self):
        self.logger.debug("increasing baud rate to 57600 (max of device)")
        self.transport.write(b"\x02" + b"O" + b"8" + b"\x03")
        self.transport.serial.baudrate = 57600

    def connection_made(self, transport):
        """
        This is explicitly made blockking, so that is executed directly after
        a connection is established
        :param transport:
        :return:
        """
        self.logger.debug('port opened')
        self.transport = transport

        # manipulate Serial object via transport
        self.transport.serial.parity = serial.PARITY_NONE
        self.transport.serial.stopbits = serial.STOPBITS_TWO
        self.transport.serial.bytesize = serial.EIGHTBITS

        # now increase baud rate
        self._increase_baud()

        # log port settings
        self.logger.debug(transport)


    def data_received(self, data):
        for p in iterbytes(data):
            particle = int2byte(p)
            if particle == self.STOP:
                self.logger.debug("STOP received")
                self.logger.debug(self._buffer)
                asyncio.ensure_future(self.queue.put(self._buffer))
            if particle == self.START:
                self.logger.debug("START received, clearing buffer")
                self._buffer = b""
            else:
                self._buffer += particle

    def connection_lost(self, exc):
        self.logger.error('port closed, stopping loop')
        self.transport.loop.stop()

    def pause_writing(self):
        self.logger.warning('pause writing')
        self.logger.warning(self.transport.get_write_buffer_size())

    def resume_writing(self):
        self.logger.warning(print('resume writing'))
        self.logger.warning(self.transport.get_write_buffer_size())


class NexedgePacketizer(serial.threaded.FramedPacket):
    """
    This class makes use of the built-in threading functionality of pySerial.
    See https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.threaded.Packetizer for reference.
    
    FramedPacket forwards Packets defined start (b'\x02') and stop sequences (b'\x03') to the handle_packet method.
    """
    START = b'\x02'
    STOP = b'\x03'

    # there will be 3 queues. 1 manages the messages, 1 for the status messages and 1 for the transmission reports
    answer_queue = Queue(maxsize=0)
    status_queue = Queue(maxsize=0)
    transmission_queue = Queue(maxsize=1)  # there should only be 1 entry in this queue at a given time

    # radio channel status object
    channel_status = ChannelStatus()

    def __init__(self):

        """"
        At the moment this only invoces the __init__() of the parent class.
        """
        super(NexedgePacketizer, self).__init__()

    def handle_packet(self, packet: bytes):
        """
        Manages a packet of the form b'JA\x90\x80\x80\x81'.
        Since the parent class does everything for us we just pass packet to the old method.
        """
        # the packet has the form b'CONTENT'
        # print(packet)
        self.channel_status.time_last_updated = time.time()
        self.handle_data(packet)

    def process_message(self, message: bytes):
        """
        Processes long and short messages send directly to the unit (SDM and LDM).
        :param message: bytes
        :return: test: bytes
        """
        sender = message[3:8]  # extract sender ID
        text = message[14:]  # extract message
        # print("Sender-ID: {}".format(sender))
        # print("Message: {}".format(text))
        return text

    def process_status(self, message: bytes):
        """
        Processes status messages.
        :param message: bytes
        :return: status: str
        """
        sender = message[3:8]
        status = message[14:]
        # print("Sender-ID: {}".format(sender))
        # print("Status: {}".format(status))
        return status

    def process_device(self, message: bytes):
        """
        We want to now if the channel is free, this is indicated by the state of the front led of the device.
        messages is in bytes format and the information is encoded in the last byte.
        See https://gitlab.com/evocount/nexedge/wikis/transceiver_status for further info.
        :param message: bytes
        :return: : str
        """
        # information is encoded in the last byte
        led = message[-1]

        # the hex status values (see gitlab wiki) are converted to int
        if led == int(0x82):  # receiving/green
            self.channel_status.set_green()

        elif led == int(0x81):  # sending/red
            self.channel_status.set_red()

        elif led == int(0x84):  # idle/orange
            self.channel_status.set_orange()

        elif led == int(0x80):  # free/led off
            self.channel_status.set_free()

        else:
            pass

    def handle_data(self, message: bytes):
        """
        Case selection of different message types.
        :param message: bytes
        :return: answer: str or None
        """
        try:
            if message[0] == b'g'[0] and message[1] == b'F'[0]:  # SDM
                answer = self.process_message(message)
                self.answer_queue.put(answer)

            elif message[0] == b'g'[0] and message[1] == b'G'[0]:  # LDM
                answer = self.process_message(message)
                self.answer_queue.put(answer)

            elif message[0] == b'g'[0] and message[1] == b'E'[0]:  # StatusMessage
                answer = self.process_status(message)
                self.status_queue.put(answer)

            elif message[0] == b'J'[0] and message[1] == b'A'[0]:  # Device status
                self.process_device(message)

            elif message[0] == b'J'[0] and message[1] == b'E'[0]:  # DisplayContent
                pass

            elif message[0] == b'0'[0]:  # transmission success
                self.transmission_queue.put(True)

            elif message[0] == b'1'[0]:  # transmission error
                self.transmission_queue.put(False)

            else:
                pass
        except IndexError:
            pass
        


def unite_chunks(chunks: [bytes, ]) -> bytes:
    """
    Concats a list of chunks (consiting of bytes)
    :param chunks: [bytes, ]
    :return: bytes
    """
    data = b''
    for c in chunks:
        data = data + c

    return data


def unite(answer_queue: Queue, compression: bool, timeout: int = 60) -> dict:
    """
    To be used in a ThreadPool.
    Takes the answer_queue and pops items until the starting chunk is found (starts with b'json'), until the stopping
    chunk is found (ends with b'json'), all chunks are appended to a list.
    If compression is enabled on class level, the joined chunks are decompressed and the checksum is verified.
    :param answer_queue: Queue
    :param compression: bool
    :param timeout: int = 60
    :return: dict
    """
    startchunk = False
    stopchunk = False
    chunks = []

    # get all chunks from the queue
    while not stopchunk:
        # the timeout is set per chunk
        #  if the timeout is reached the queue.Empty exception is raised and catched
        try:
            chunk = answer_queue.get(timeout=timeout)
        except queue.Empty:
            raise ReceiveTimeout

        # this is the first chunk
        if chunk[:4] == b'json':
            startchunk = True
            # print("start")
            # clear the list in chunks in case a previous transmission was not complete!
            chunks = []
            # strip the identifier
            chunk = chunk[4:]

        # this is the last chunk of a full transmission because startchunk is set
        if startchunk and chunk[-4:] == b'json':
            stopchunk = True
            # print("end")
            # strip the identifier
            chunk = chunk[:-4]
            # # strip the checksum and convert from hex to int
            # cs_received_int = int.from_bytes(chunk[-4:], "big")
            # chunk = chunk[:-4]

        if startchunk:
            chunks.append(chunk)

    data_encoded = unite_chunks(chunks)

    data_compressed = base64.b64decode(data_encoded)

    # decompression
    if compression:
        data_bytes = decompress(data_compressed)
    else:
        data_bytes = data_compressed

    # # data integrity check
    # data_cs_int = zlib.crc32(data_bytes)

    # # the foobar is used because of some int signing issue, see https://docs.python.org/3/library/zlib.html#zlib.crc32
    # if (data_cs_int & 0xffffffff) != (cs_received_int & 0xffffffff):
    #     raise VerificationError

    data_str = data_bytes.decode()
    data = json.loads(data_str)

    return data
