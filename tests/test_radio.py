"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""
from tests.fixtures import radio, no_radio
import nexedge.exceptions

import pytest
import mock
from pytest_mock import mocker
import logging
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_open_connection_raise_on_no_device(no_radio, caplog):
    with pytest.raises(nexedge.exceptions.DeviceNotFound):
        await no_radio.start_connection_handler()


@pytest.mark.asyncio
async def test_open_connection_log_on_no_device(no_radio, caplog):
    with caplog.at_level(logging.ERROR):
        try:
            await no_radio.start_connection_handler()
        except:
            pass
        assert "opening serial port" in caplog.text


@pytest.mark.asyncio
async def test_open_connection_destroy_on_no_device(no_radio, mocker):
    mocker.patch.object(no_radio, "destroy")
    try:
        await no_radio.start_connection_handler()
    except:
        pass
    no_radio.destroy.assert_called_with()


@pytest.mark.asyncio
async def test_open_connection(radio):
    await radio.start_connection_handler()
