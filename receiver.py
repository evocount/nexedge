"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

import serial.threaded
import zlib
import json
from queue import Queue


class ChannelStatus(object):
    """
    This class contains the status of the radio channel as indicated by the led.
    """
    channel_free = True
    radio_status = "unknown"

    def is_free(self):
        """
        True if channel is free (led off)
        :return: 
        """
        return self.channel_free

    def set_red(self):
        self.channel_free = False
        self.radio_status = "sending"

    def set_green(self):
        self.channel_free = False
        self.radio_status = "receiving"

    def set_orange(self):
        self.channel_free = False
        self.radio_status = "idle"

    def set_free(self):
        self.channel_free = True
        self.radio_status = "off"


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
    data = b''
    for c in chunks:
        data = data + c

    return data


def unite(answer_queue: Queue, compression: bool, receive_timeout: int = 60) -> dict:
    startchunk = False
    stopchunk = False
    chunks = []

    # get all chunks from the queue
    while not stopchunk:
        # the timeout is set per chunk
        #  if the timeout is reached the queue.Empty exception is raised
        chunk = answer_queue.get(timeout=receive_timeout)

        # this is the first chunk
        if chunk[:4] == b'json':
            startchunk = True
            # clear the list in chunks in case a previous transmission was not complete!
            chunks = []
            # strip the identifier
            chunk = chunk[4:]

        # this is the last chunk of a full transmission because startchunk is set
        if startchunk and chunk[-4:] == b'json':
            stopchunk = True
            # strip the identifier
            chunk = chunk[:-4]

        if startchunk:
            chunks.append(chunk)

    data_compressed = unite_chunks(chunks)

    # decompression
    if compression:
        data_bytes = zlib.decompress(data_compressed)
    else:
        data_bytes = data_compressed

    data_str = data_bytes.decode()
    data = json.loads(data_str)

    return data
