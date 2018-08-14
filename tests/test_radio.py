"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""
from tests.fixtures import radio, no_radio

import pytest
import logging
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_open_connection_no_device(no_radio, caplog):
    import serial
    with caplog.at_level(logging.ERROR):
        with pytest.raises(serial.SerialException):
            await no_radio.open_connection(change_baudrate=False,
                                           retry=False)
        assert "could not open serial port" in caplog.text


@pytest.mark.asyncio
async def test_open_connection(radio):
    await radio.open_connection(change_baudrate=False,
                                retry=False)
