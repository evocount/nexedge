"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017-2018
"""

import asyncio
from asyncio.futures import TimeoutError
import serial
import logging

# local
from .channel import ChannelStatus
from .pcip_commands import set_baudrate, set_repeat,\
    channel_status_request, getChannelStatus, longMessage2Unit,\
    startcall, endcall
from .utils import open_serial_connection
from .exceptions import *

# setup logging
logger = logging.getLogger(__name__)


class Radio:
    START = b'\x02'
    STOP = b'\x03'

    MAXSIZE = 4000

    def __init__(self,
                 serial_kwargs: dict,
                 change_baudrate: bool = False,
                 retry_sending: bool = True,
                 confirmation_timeout: float = 60,
                 channel_timeout: float = 60,
                 ):
        # get a logger
        logger.info("initialized Radio instance")

        # setting loop
        self._loop = asyncio.get_event_loop()

        # setting initial serial config
        self._serial_kwargs = serial_kwargs
        self._retry_sending = retry_sending
        self._change_baudrate = change_baudrate

        # setting timeouts
        self.confirmation_timeout = confirmation_timeout
        self.channel_timeout = channel_timeout

        # queue setup
        # received data queue
        self.data_queue = asyncio.Queue()
        # received status messages
        self.status_queue = asyncio.Queue()

        # channel status object
        self.channel = ChannelStatus()

        # initialize command return
        self._command_return = None

        # only one writing is allowed at one
        self.RADIO_LOCK = asyncio.Lock()

        # initialize receiver loop and connection handler as None
        self._receiver = None
        self._con_handler = None

        # initialize reader/writer pair as None
        self._reader = None
        self._writer = None
        self._transport = None

        # indicator for cancelling
        self.is_destroyed = asyncio.Future()

    def destroy(self):
        """
        Cancel all ongoing loops.
        :return:
        """
        for task in [self._con_handler, self._receiver]:
            if task is not None:
                logger.info(f"cancelling task {task}")
                task.cancel()
        self.is_destroyed.set_result(True)

        return None

    def start_connection_handler(self):
        """
        Returns open_connection or starts it.
        :return:
        """
        if self._con_handler is None:
            loop = asyncio.get_event_loop()
            self._con_handler = loop.create_task(
                self.open_connection())

        return self._con_handler

    async def open_connection(self):
        # open the serial connection as reader/writer pair
        logger.debug("setting up reader/writer pair")
        try:
            loop = asyncio.get_event_loop()
            transport, reader, writer = await open_serial_connection(
                    loop=loop, **self._serial_kwargs)
        except serial.SerialException as e:
            logger.exception(
                f"opening serial port {self._serial_kwargs['url']}"
                f" failed witdh {repr(e)}")
            self.destroy()
            raise DeviceNotFound(
                f"could not open {self._serial_kwargs['url']}")

        # manipulate Serial object via transport
        transport.serial.parity = serial.PARITY_NONE
        transport.serial.stopbits = serial.STOPBITS_TWO
        transport.serial.bytesize = serial.EIGHTBITS

        # now write everything to instance variables
        self._reader = reader
        self._writer = writer
        self._transport = transport

        # change baud rate
        if self._change_baudrate:
            logger.info("try increasing baud rate to 57600")
            success = await self._increase_baudrate()
            if success:
                logger.info("baudrate set to 57600")
                self._transport.serial.baudrate = 57600
            else:
                logger.info("incresing baudrate failed, staying at 9600")

        # disable air retries
        # should not be changed atm since I do not know why it is failing
        # if not self._retry:
        #     logger.info("disabling repeated sending")
        #     success = await self._disable_retry()
        #     if success:
        #         logger.info("retry disabled")
        #     else:
        #         logger.info("retry still unchanged")

    async def _increase_baudrate(self):
        """
        Increase the serial baudrate to maximum of 57600
        """
        return await self.write(set_baudrate(baud=57600))

    async def _disable_retry(self):
        """
        Disable repeated sending
        """
        return await self.write(set_repeat(True))

    @property
    def maxsize(self):
        """
        Return max package size.
        :return: int
        """
        return self.MAXSIZE

    def start_receiver_handler(self):
        """
        Return the receiver coroutine or start if not already started.
        :return:
        """
        if self._receiver is None:
            loop = asyncio.get_event_loop()
            self._receiver = loop.create_task(self.receiver())

        return self._receiver

    async def receiver(self):
        logger.info("starting receiver loop")
        while True:
            if self._reader is None:
                logger.warning(f"connection is not ready, sleeping for 5s")
                await asyncio.sleep(5)
                continue

            logger.debug("waiting for the next message")
            # read until the message is over
            # this is the blocking call
            try:
                buffer = await self._reader.readuntil(self.STOP)
                # logger.debug(f"dumping buffer {buffer}")
            except serial.serialutil.SerialException:
                logger.exception(f"could not access serial port during reading")
                self.destroy()
                raise DeviceNotFound

            # split buffer by stop byte bc it is still there
            # see docs for stream classes in asyncio
            buffer, *_tail = buffer.split(self.STOP)

            # split buffer at start byte, head should be empty by design
            *_head, message = buffer.split(self.START)

            # now handle the message
            try:
                # SDM
                if message[0] == b'g'[0] and message[1] == b'F'[0]:
                    logger.debug(f"got SDM {message}")
                    self.channel.update()
                    self.process_message(message)

                # LDM
                elif message[0] == b'g'[0] and message[1] == b'G'[0]:
                    logger.debug(f"got LDM {message}")
                    self.channel.update()
                    self.process_message(message)

                # StatusMessage
                elif message[0] == b'g'[0] and message[1] == b'E'[0]:
                    logger.debug(f"got status {message}")
                    self.channel.update()
                    self.process_status(message)
                    pass

                # Device status
                elif message[0] == b'J'[0] and message[1] == b'A'[0]:
                    logger.debug(f"got device status {message}")
                    self.channel.update()
                    self.process_device(message)

                # DisplayContent
                elif message[0] == b'J'[0] and message[1] == b'E'[0]:
                    logger.debug(f"got display content {message}")
                    pass

                # transmission success
                elif message[0] == b'0'[0]:
                    logger.debug("got trans. success")
                    if self._command_return is not None:
                        self._command_return.set_result(True)
                    else:
                        logger.debug("but no one cared")

                # transmission error
                elif message[0] == b'1'[0]:
                    logger.debug("got trans. failure")
                    if self._command_return is not None:
                        self._command_return.set_result(False)
                    else:
                        logger.debug("but no one cared")

                else:
                    pass
            # something something happened
            except IndexError:
                pass

    def process_message(self, message: bytes):
        """
        Processes long and short messages send directly
        to the unit (SDM and LDM).
        :param message: bytes
        :return: test: bytes
        """
        sender = message[3:8]  # extract sender ID
        text = message[14:]  # extract message
        logger.debug(f"Sender-ID: {sender}")
        logger.debug(f"Message: {text}")
        self.data_queue.put_nowait([sender, text])

    def process_status(self, message: bytes):
        """
        Processes status messages.
        :param message: bytes
        :return: status: str
        """
        sender = message[3:8]
        status = message[14:]
        logger.debug(f"Sender-ID: {sender}")
        logger.debug(f"Status: {status}")
        self.status_queue.put([sender, status])

    def process_device(self, message: bytes):
        """
        We want to now if the channel is free, this is indicated by the state
        of the front led of the device.
        messages is in bytes format and the information is encoded in the
        last byte.
        See https://gitlab.com/evocount/nexedge/wikis/transceiver_status
        for further info.
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

    async def write(self, command: bytes, await_response: bool = True):
        """
        low level write something to serial device
        :param command:
        :return:
        """
        self._command_return = asyncio.Future() if await_response else None
        try:
            self._writer.write(command)
        except serial.serialutil.SerialException as e:
            logger.exception(f"could not access serial port during writing"
                             f"{repr(e)}")
            self.destroy()
            raise DeviceNotFound

        logger.debug("actual writing to serial finished")

        # default is to wait for a response
        if await_response:
            # result is either True or False
            try:
                result = await asyncio.wait_for(self._command_return,
                                                self.confirmation_timeout)
                logger.debug(f"write result {result}")
            except TimeoutError:
                logger.error("confirmation of write timed out")
                raise ConfirmationTimeout
            finally:
                self._command_return = None
            return result
        # if only the channel status should be checked we cannot wait
        # for confirmations, just go on
        else:
            return None

    async def send(self, command):
        """
        wait for channel to get free and write to device
        :param command:
        :return:
        """
        # radio shows strange behaviour if next message is sent befor display
        # is updated, give it 5 seconds
        await asyncio.sleep(5)

        if self._command_return is not None:
            logger.debug("waiting for current command to end")
            await self._command_return

        logger.debug("acquiring writing lock")
        # temporary removing lock
        async with self.RADIO_LOCK:
            # if True:
            logger.debug("lock acquired")
            logger.debug("checking if channel is free")
            if not self.channel.free():
                # behaviour not predictable
                # await self.write(command=channel_status_request(b"00002"),
                #                  await_response=False)

                # also not always working
                # trying something dirty, just starting a call
                logger.debug("starting call")
                await self.write(command=startcall(), await_response=True)
                await asyncio.sleep(1)
                logger.debug("ending call")
                await self.write(command=endcall(), await_response=True)

                logger.debug("waiting for channel to become free")
                try:
                    # a force to set the channel free after a certain
                    # inactivity is implemented
                    await asyncio.wait_for(self.channel.wait_for_free(),
                                           self.channel_timeout)
                except TimeoutError:
                    raise ChannelTimeout

            logger.debug("channel is free")
            return await self.write(command)

    async def send_LDM(self, target_id: bytes = None, payload: bytes = None):
        assert (target_id is not None) and (payload is not None),\
            "target and payload have to be set!"

        logger.info(
            f"sending LDM with payload length {len(payload)} to {target_id}"
        )
        if len(payload) > self.MAXSIZE:
            raise PayloadTooLarge

        cmd = longMessage2Unit(unitID=target_id, message=payload)
        return await self.send(cmd)
