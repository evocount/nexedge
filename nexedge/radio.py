import time
import asyncio
import serial
import serial_asyncio
from six import int2byte
from functools import partial
import logging

# local
from channel import ChannelStatus
from pcip_commands import set_baudrate


async def read_queue(queue):
    while True:
        s, m = await queue.get()
        print("received from {}: {}".format(s, m))


async def read_channel(channel):
    while True:

        print("channel is free: {}".format(channel.free()))
        await asyncio.sleep(2)


# this is basically a copy from the pyserial_async source, but we need to get
# the transport to manipulate serial
@asyncio.coroutine
def open_serial_connection(*,
                           loop=None,
                           limit=asyncio.streams._DEFAULT_LIMIT,
                           **kwargs):
    """
    A wrapper for create_serial_connection() returning a (reader,
    writer) pair.
    The reader returned is a StreamReader instance; the writer is a
    StreamWriter instance.
    The arguments are all the usual arguments to Serial(). Additional
    optional keyword arguments are loop (to set the event loop instance
    to use) and limit (to set the buffer limit passed to the
    StreamReader.
    This function is a coroutine.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader(limit=limit, loop=loop)
    protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
    transport, _ = yield from serial_asyncio.create_serial_connection(
        loop=loop,
        protocol_factory=lambda: protocol,
        **kwargs)
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)
    return transport, reader, writer


class Radio:
    START = b'\x02'
    STOP = b'\x03'

    def __init__(self,
                 loop,
                 serial_kwargs: dict,
                 logger: logging.Logger = None):
        # get a logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.logger.info("initialized Radio instance with logger")

        # setting loop
        self.loop = loop

        # setting initial serial config
        self._serial_kwargs = serial_kwargs

        # queue setup
        # received data queue
        self.data_queue = asyncio.Queue()
        # received status messages
        self.status_queue = asyncio.Queue()
        # transmission result queue
        self.transmission_queue = asyncio.Queue(maxsize=1)

        # channel status object
        self.channel = ChannelStatus(logger=self.logger)

        # open serial connection
        # asyncio.ensure_future(self.open_connection())
        self.loop.create_task(self.open_connection())

    async def open_connection(self):
        # open the serial connection as reader/writer pair
        self.logger.debug("setting up reader/writer pair")
        self.transport, self.reader, self.writer = await open_serial_connection(
                loop=self.loop, **self._serial_kwargs)

        # manipulate Serial object via transport
        self.transport.serial.parity = serial.PARITY_NONE
        self.transport.serial.stopbits = serial.STOPBITS_TWO
        self.transport.serial.bytesize = serial.EIGHTBITS

        # change baud rate
        # self._increase_baudrate()

    def _increase_baudrate(self):
        """
        Increase the serial baudrate to maximum of 57600
        """
        self.logger.info("increasing baud rate to 57600")
        # writing to serial is done in a blocking fashion
        self.writer.write(set_baudrate(baud=57600))
        self.transport.serial.baudrate = 57600

    async def receiver(self):
        self.logger.info("starting receiver loop")
        while True:
            self.logger.debug("waiting for the next message")
            # read until the message is over
            # this is the blocking call
            buffer = await self.reader.readuntil(self.STOP)
            #self.logger.debug("dumping buffer {}".format(buffer))

            # split buffer by stop byte bc it is still there
            # see docs for stream classes in asyncio
            buffer, _tail = buffer.split(self.STOP)

            # split buffer at start byte, head should be empty by design
            _head, message = buffer.split(self.START)
            if _head != b"" or _tail != b"":
                # TODO custom exception
                raise Exception

            # update channel status
            self.channel.update()

            # now handle the message
            try:
                # SDM
                if message[0] == b'g'[0] and message[1] == b'F'[0]:
                    self.logger.debug("got SDM {}".format(message))
                    self.process_message(message)

                # LDM
                elif message[0] == b'g'[0] and message[1] == b'G'[0]:
                    self.logger.debug("got LDM {}".format(message))
                    self.process_message(message)

                # StatusMessage
                elif message[0] == b'g'[0] and message[1] == b'E'[0]:
                    self.logger.debug("got status {}".format(message))
                    self.process_status(message)
                    pass

                # Device status
                elif message[0] == b'J'[0] and message[1] == b'A'[0]:
                    self.logger.debug("got device status {}".format(message))
                    self.process_device(message)

                # DisplayContent
                elif message[0] == b'J'[0] and message[1] == b'E'[0]:
                    self.logger.debug("got display content {}".format(message))
                    pass

                # transmission success
                elif message[0] == b'0'[0]:
                    self.logger.debug("got trans. success")
                    self.transmission_queue.put(True)

                # transmission error
                elif message[0] == b'1'[0]:
                    self.logger.debug("got trans. failure")
                    self.transmission_queue.put(False)

                else:
                    pass
            # something something happened
            except IndexError:
                pass

    def process_message(self, message: bytes):
        """
        Processes long and short messages send directly to the unit (SDM and LDM).
        :param message: bytes
        :return: test: bytes
        """
        sender = message[3:8]  # extract sender ID
        text = message[14:]  # extract message
        self.logger.debug("Sender-ID: {}".format(sender))
        self.logger.debug("Message: {}".format(text))
        self.data_queue.put([sender, text])

    def process_status(self, message: bytes):
        """
        Processes status messages.
        :param message: bytes
        :return: status: str
        """
        sender = message[3:8]
        status = message[14:]
        self.logger.debug("Sender-ID: {}".format(sender))
        self.logger.debug("Status: {}".format(status))
        self.status_queue.put([sender, status])

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
            self.channel.set_green()

        elif led == int(0x81):  # sending/red
            self.channel.set_red()

        elif led == int(0x84):  # idle/orange
            self.channel.set_orange()

        elif led == int(0x80):  # free/led off
            self.channel.set_free()

        else:
            pass


if __name__ == '__main__':
    # logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # async loop
    loop = asyncio.get_event_loop()

    serial_conf = {
        "url": '/dev/ttyUSB0',
        "baudrate": 9600,
        #"baudrate": 57600,
    }
    r = Radio(loop=loop, serial_kwargs=serial_conf, logger=logger)
    loop.create_task(read_queue(r.data_queue))
    loop.create_task(read_channel(r.channel))
    loop.create_task(r.receiver())

    loop.run_forever()
    loop.close()
