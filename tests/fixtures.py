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


RADIO_KWARGS = dict(change_baudrate=False,
                    retry_sending=False,
                    confirmation_timeout=60,
                    channel_timeout=60)

SERIAL_KWARGS = dict(url="loop://",
                     baudrate=9600)

SERIAL_KWARGS_FAIL = dict(url="/dev/ttyFAIL",
                          baudrate=9600)

@pytest.fixture
def radio():
    """
    Fixture for an existing radio device (loop device).
    :return:
    """
    return Radio(serial_kwargs=SERIAL_KWARGS, **RADIO_KWARGS)


@pytest.fixture
def no_radio():
    """
    Fixture for a missing radio device (/dev/ttyFAIL).
    :return:
    """
    return Radio(serial_kwargs=SERIAL_KWARGS_FAIL, **RADIO_KWARGS)
