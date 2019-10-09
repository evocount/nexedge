import logging
import base64

# setup logging
logger = logging.getLogger(__name__)


class Encoder:
    """
    Abstract construct for an encoder/decoder.
    For nexedge the data has to be encoded in base64 because of some obscure
    voodoo.

    Like with Packer encode and decode have to be implemented.
    """

    def __init__(self):
        """
        nothing to do here
        """
        logger.debug(f"initialized Encoder {repr(self)}")
        pass

    def encode(self, data: bytes=None) -> bytes:
        raise NotImplementedError

    def decode(self, enc: bytes=None) -> bytes:
        raise NotImplementedError


class B64Encoder(Encoder):
    """
    Implements an encoder with base64.
    """

    def encode(self, data: bytes=None) -> bytes:
        assert type(data) is bytes, "data has to be given as bytes"
        return base64.b64encode(data)

    def decode(self, enc: bytes=None) -> bytes:
        assert type(enc) is bytes, "encoded data has to be given as bytes"
        return base64.b64decode(enc)
