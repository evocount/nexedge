"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""

import logging
import random
import asyncio

# setup logging
logger = logging.getLogger(__name__)

# local imports
from .radio import Radio
from .channel import ChannelStatus
from .packer import JSONPacker
from .encoder import B64Encoder
from .compressor import ZCompressor
from .exceptions import *


class RadioCommunicator:
    """
    Radio communication with a target receiver.
    Provides data transmission queues for every called target
    """

    _packer = JSONPacker()
    _compressor = ZCompressor()
    _encoder = B64Encoder()

    COM_LOCK = None

    def __init__(self,
                 serial_kwargs: dict,
                 listeners=(),
                 timeout: int = 60):
        logger.info(f"initialized radio communicator {self}")

        if RadioCommunicator.COM_LOCK is None:
            RadioCommunicator.COM_LOCK = asyncio.Lock()

        # initialize queues and counter
        self._listener_queues = {}
        self._target_queues = {}
        self._counter = 0

        # initialize data_handler as None
        self._data_handler = None

        # add the listener queues
        for trigger in listeners:
            logger.info(f"adding listener queue for trigger {trigger}")
            self._listener_queues[trigger] = asyncio.Queue()

        logger.info("opening connection to radio")
        self._radio = Radio(serial_kwargs=serial_kwargs,
                            change_baudrate=False,
                            retry_sending=False,
                            confirmation_timeout=timeout,
                            channel_timeout=timeout)

        # open the serial connection
        self._radio.start_connection_handler()

        # start the receiver loop
        self._radio.start_receiver_handler()

        # start the state checker
        self._radio_state_handler =\
            asyncio.get_event_loop().create_task(self.radio_state_handler())

        # flag
        self.is_destroyed = asyncio.Future()

    def destroy(self):
        """
        Cancel all ongoing loops.
        :return:
        """
        for task in [self._data_handler]:
            if task is not None:
                logger.info(f"cancelling task {task}")
                task.cancel()

        # set flag
        self.is_destroyed.set_result(True)

        # if radio is already cancelled, this does nothing
        self._radio.destroy()

    async def radio_state_handler(self):
        """
        Wait untill the radio is destroyed.
        :return:
        """
        await self._radio.is_destroyed
        logger.debug("radio set destroyed flag")
        self.destroy()
        return

    def pickle(self, data):
        """
        Take an object and return the bytes which can be interpreted by Radio()
        :param data: dict
        :return: bytes
        """
        packed = self._packer.pack(data=data)
        compressed = self._compressor.compress(data=packed)
        encoded = self._encoder.encode(data=compressed)

        return encoded

    def unpickle(self, encoded: bytes):
        """
        Reverses the process of self.pickle()
        :param encoded: bytes
        :return: dict
        """
        decoded = self._encoder.decode(enc=encoded)
        uncompressed = self._compressor.decompress(comp=decoded)
        unpacked = self._packer.unpack(message=uncompressed)

        return unpacked

    def allowed_size_with_margin(self, data=None):
        """
        Check the size of the pickled data package.
        :param data:
        :return:
        """
        assert data is not None, "data has to be given"
        # pickle data
        # pack data into dummy dict
        data_dict = {"dummy": data}
        encoded = self.pickle(data_dict)

        # now check size with padding for meta data
        if len(encoded) > (self._radio.MAXSIZE * .8):
            return False
        else:
            return True

    async def send(self, target_id: bytes = None, data=None, meta: dict={}):
        """
        Send the object data to the target receiver
        :param target_id: bytes
        :param data:
        :param meta: dict additional meta information for transmission
        :return: bool
        """
        assert type(target_id) is bytes and data is not None,\
            "target or data not set correctly"

        # check if backend is still running
        if self.is_destroyed.done():
            logger.exception("aborting send because backend was stopped")
            raise DeviceNotFound

        # increase transmission counter
        self._counter += 1
        logger.info(
            f"sending some data to {target_id} with counter {self._counter}"
        )

        # add some meta data to our payload
        data = {
            "counter":  self._counter,
            "meta":     meta,
            "payload":  data,
        }

        # data pickling
        encoded = self.pickle(data=data)

        # now check size
        if len(encoded) > self._radio.MAXSIZE:
            raise PayloadTooLarge(
                f"payload length {len(encoded)}>{self._radio.MAXSIZE}"
            )

        # actually sending something
        # actual sending is done in a lock
        async with RadioCommunicator.COM_LOCK:
            # if True:
            try:
                t_result = await self._radio.send_LDM(target_id=target_id,
                                                      payload=encoded)
            except ConfirmationTimeout:
                t_result = False

        if t_result:
            logger.info(f"transmission {self._counter} succeed")
        else:
            logger.info(f"transmission {self._counter} failed")
        return t_result

        """
        # retry n times
        n = 2
        while n > 0:
            dt = random.randrange(start=2000, stop=10000)
            dt = dt / 1e3
            logger.info(
                f"transmission {self._counter} failed, will retry in {dt}s"
            )

            await asyncio.sleep(dt)
            with (await RadioCommunicator.COM_LOCK):
                t_result = await self._radio.send_LDM(target_id=target_id,
                                                      payload=encoded)
            if t_result:
                return True

            n -= 1
        raise SendMaxRetries
        """

    def get_target_queue(self, target: bytes = None) -> asyncio.Queue:
        """
        Getter method to retrieve a incoming data queue for a certain receiver.
        :param target:
        :return:
        """
        assert type(target) is bytes, "target has to be bytes"

        # does it already exist?
        if target not in self._target_queues.keys():
            # create a new one
            self._target_queues[target] = asyncio.Queue()

        # return said queue
        return self._target_queues[target]

    def get_listener_queue(self, trigger) -> asyncio.Queue:
        """
        Getter method to retrieve a queue which contains
        the pre-defined listeners.
        :param trigger:
        :return:
        """
        # does it already exist?
        if trigger not in self._listener_queues.keys():
            # you should have done that beforehand!
            raise ReceiverException(
                "listener queue was not defined in constructor"
            )

        # return said queue
        return self._listener_queues[trigger]

    def start_data_handler(self):
        """
        Returns data_handler or starts it.
        :return:
        """
        if self._data_handler is None:
            loop = asyncio.get_event_loop()
            self._data_handler = loop.create_task(
                self.data_handler())

        return self._data_handler

    async def data_handler(self):
        """
        This is where the magic happpens.
        This queue interprets the bytes coming from the receiver queue and
        retrieves usable data.
        The data is then sorted to the receiver queues.
        If a trigger keyword for a listener is found, put the data into the
        listener queue
        """
        logger.info("starting data_handler in communicator")
        while True:
            remote_id, encoded = await self._radio.data_queue.get()
            data = self.unpickle(encoded=encoded)

            # get the meta information
            meta = data["meta"]

            # look for trigger in data meta informations
            if "trigger" in meta:
                logger.debug("found meta key trigger")
                trigger = meta["trigger"]
                try:
                    logger.debug(f"adding data to listener queue {trigger}")
                    self._listener_queues[trigger].put_nowait([remote_id,
                                                               data])
                    continue
                except KeyError:
                    logger.warning(
                        f"encountered unknown trigger for listener {trigger}"
                    )
                    continue

            # well there was no trigger, lets continue
            queue = self.get_target_queue(target=remote_id)

            # put it into the data queue
            logger.debug(f"putting data into {remote_id} queue")
            queue.put_nowait([remote_id, data])
