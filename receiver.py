"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

import serial.threaded
import zlib
from zlib import compress, decompress
# from lzma import compress, decompress
import base64
import time
import json
import queue
from queue import Queue
from custom_exceptions import *


class ChannelStatus(object):
    """
    This class contains the status of the radio channel as indicated by the led.
    """
    channel_free = True
    radio_status = "unknown"
    time_unfree = time.time()

    def __init__(self, free_threshold: int = 2):
        """
        Initialize Object.
        Threshold sets the time in seconds in which the channel has to be clear before it is considered really free.
        :param free_threshold: int
        """
        self.free_threshold = free_threshold

    def is_free(self):
        """
        True if channel is free (led off).
        :return: bool
        """
        return self.channel_free

    def is_free_timed(self):
        """
        True if channel is free (led off) and was free for the last self.free_threshold seconds (default = 2s).
        :return: bool
        """
        return self.channel_free and time.time() - self.free_threshold > self.time_unfree

    def set_free(self):
        self.channel_free = True
        self.radio_status = "off"

    def set_unfree(self, status):
        """
        Sets self.channel_free to False and the radio status to a human readable string, the time when the channel goes
        unfree is stored.
        :param status: str
        :return:
        """
        self.channel_free = False
        self.time_unfree = time.time()
        self.radio_status = status

    def set_red(self):
        self.set_unfree("sending")

    def set_green(self):
        self.set_unfree("receiving")

    def set_orange(self):
        self.set_unfree("idle")


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


def unite(answer_queue: Queue, compression: bool, receive_timeout: int = 60) -> dict:
    """
    To be used in a ThreadPool.
    Takes the answer_queue and pops items until the starting chunk is found (starts with b'json'), until the stopping
    chunk is found (ends with b'json'), all chunks are appended to a list.
    If compression is enabled on class level, the joined chunks are decompressed and the checksum is verified.
    :param answer_queue: Queue
    :param compression: bool
    :param receive_timeout: int = 60
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
            chunk = answer_queue.get(timeout=receive_timeout)
        except queue.Empty:
            raise ReceiveTimeout

        # this is the first chunk
        if chunk[:4] == b'json':
            startchunk = True
            print("start")
            # clear the list in chunks in case a previous transmission was not complete!
            chunks = []
            # strip the identifier
            chunk = chunk[4:]

        # this is the last chunk of a full transmission because startchunk is set
        if startchunk and chunk[-4:] == b'json':
            stopchunk = True
            print("end")
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
