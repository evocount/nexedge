"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""

import logging
import json

# setup logging
logger = logging.getLogger(__name__)


class Packer:
    """
    Packer is basically a serializer.
    Packer.pack accepts an object and returns bytes.
    Packer.unpack accepts bytes and returns an object.
    """

    def __init__(self):
        """
        nothing to do here
        """
        logger.debug(f"initialized Packer {repr(self)}")
        pass

    def pack(self, data=None) -> bytes:
        raise NotImplementedError

    def unpack(self, message: bytes = None):
        raise NotImplementedError


class JSONPacker(Packer):
    """
    Implements a packer for JSON like objects.
    """

    def pack(self, data: dict=None) -> bytes:
        assert type(data) is dict, "data has to be giving as a dictionary"
        ser = json.dumps(data, separators=(',', ':'))
        return ser.encode()

    def unpack(self, message: bytes = None):
        assert type(message) is bytes, "message has to be given as bytes"
        return json.loads(message)
