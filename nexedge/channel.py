"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""

import time
import asyncio
import logging

# logging setup
logger = logging.getLogger(__name__)


class ChannelStatus:
    """
    This class contains the status of the radio channel as
    indicated by the led.
    """
    _channel_free = True
    _radio_status = "unknown"
    _time_unfree = time.time()
    # when did we receive a package for the last time
    _time_last_updated = 0

    def __init__(self, free_threshold: int = 4, force_threshold: int = 10):
        """
        Initialize Object.
        Free Threshold sets the time in seconds in which the channel has to be
        clear before it is considered really free.
        In case we do not receive anything from the channel for 10 s, the force
        threshold forces sets the channel free.
        This works in our scheme since by design only one unit is sending and
        there is no concurrency.
        :param free_threshold: int
        """
        self.free_threshold = free_threshold
        self.force_threshold = force_threshold

    def update(self):
        """
        Update the time on this object.
        """
        logger.debug("updating channel access time")
        self._time_last_updated = time.time()

    def free(self):
        """
        True if channel is free (led off) and was free for the last
        self.free_threshold seconds (default = 4s).
        :return: bool
        """
        # first case, we get enough updates on the channel
        # this means the channel is free and is was free for the last 4 seconds
        status = self._channel_free and \
                 (time.time() - self.free_threshold > self._time_unfree)

        # sometimes the channel just does not get any status updates, in this
        # case just assume free and force the message
        force = time.time() - self.force_threshold > self._time_last_updated
        return status or force

    async def wait_for_free(self):
        """
        Returns when the channel is finally free.
        :return:
        """
        while True:
            if self.free():
                logger.debug("wait_for_free terminates gracefully")
                return
            await asyncio.sleep(.1)

    def set_free(self):
        logger.debug("setting channel free")
        self._channel_free = True
        self._radio_status = "off"

    def set_unfree(self, status):
        """
        Sets self.channel_free to False and the radio status to a
        human readable string, the time when the channel goes
        unfree is stored.
        :param status: str
        :return:
        """
        logger.debug("setting channel unfree")
        self._channel_free = False
        self._time_unfree = time.time()
        self._radio_status = status

    def set_red(self):
        self.set_unfree("sending")

    def set_green(self):
        self.set_unfree("receiving")

    def set_orange(self):
        self.set_unfree("idle")