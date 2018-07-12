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
    _loop = None
    _radio = None
    _target_queues = {}
    _counter = 0

    _packer = JSONPacker()
    _compressor = ZCompressor()
    _encoder = B64Encoder()

    def __init__(self,
                 loop,
                 serial_kwargs: dict):
        logger.info("initialized radio communicator {}".format(repr(self)))

        self._loop = loop

        logger.info("opening connection to radio")
        self._radio = Radio(loop=self._loop,
                            serial_kwargs=serial_kwargs,
                            retry_sending=False)

        # start the receiver
        self._loop.create_task(self._radio.receiver())

    async def transmit_and_wait(self, target_id: bytes, payload: bytes):
        transmission = await self._radio.send_LDM(target_id=target_id,
                                                  payload=payload)

        # wait for result to retry maybe
        #while not transmission.done():
        #    await asyncio.sleep(.05)
        #return transmission.result()
        return transmission

    async def send(self, target_id: bytes = None, data=None):
        """
        Send the object data to the target receiver
        :param target: bytes
        :param data:
        :return: bool
        """
        assert type(target_id) is bytes and data is not None, "target or data not set correctly"
        # increase transmission counter
        self._counter += 1
        logger.info("sending some data to {} with counter {}".format(target_id, self._counter))

        # data processing chain
        packed = self._packer.pack(data=data)
        compressed = self._compressor.compress(data=packed)
        encoded = self._encoder.encode(data=compressed)

        # actually sending something
        t_result = await self.transmit_and_wait(target_id=target_id, payload=encoded)

        if t_result:
            logger.info("transmission {} succeed".format(self._counter))
            return True
        else:
            # retry n times
            n = 2
            while n > 0:
                dt = random.randrange(start=2000, stop=10000)
                dt = dt / 1e3
                logger.info(
                    "transmission {} failed, will retry in {}s".format(self._counter, dt))

                await asyncio.sleep(dt)
                t_result = await self.transmit_and_wait(target_id=target_id,
                                                        payload=encoded)
                if t_result:
                    return True

                n -= 1
            raise SendMaxRetries







