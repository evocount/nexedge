"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""
from nexedge import Radio, ChannelStatus

import pytest
import asyncio
import logging
logger = logging.getLogger(__name__)


class DummyRadio(Radio):
    """
    A dummy version of the radio class.
    This version does not execute open_connection
    (compare with Radio().__init__()).
    """
    def __init__(self):
        # get a logger
        logger.info("initialized Dummy Radio instance")

        # setting loop
        self._loop = asyncio.get_event_loop()

        # setting initial serial config
        self._serial_kwargs = {
            "url": 'loop://',
            "baudrate": 9600,
            }

        # setting timeouts
        self.confirmation_timeout = 60
        self.channel_timeout = 60

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


@pytest.fixture
def radio():
    """
    Fixture for an existing radio device (loop device).
    :return:
    """
    return DummyRadio()


@pytest.fixture
def no_radio():
    """
    Fixture for a missing radio device (/dev/ttyUSB2).
    :return:
    """
    radio = DummyRadio()
    radio._serial_kwargs = {
        "url": '/dev/ttyFAIL',
        "baudrate": 9600,
    }
    return radio
