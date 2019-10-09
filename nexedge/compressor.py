import logging
import zlib

# setup logging
logger = logging.getLogger(__name__)


class Compressor:
    """
    Abstract construct for a data compressor.

    Like with Packer compress and decompress have to be implemented.
    """

    def __init__(self):
        """
        nothing to do here
        """
        logger.debug(f"initialized Encoder {repr(self)}")
        pass

    def compress(self, data: bytes=None) -> bytes:
        raise NotImplementedError

    def decompress(self, enc: bytes=None) -> bytes:
        raise NotImplementedError


class ZCompressor(Compressor):
    """
    Implements an encoder with bas64.
    """

    def compress(self, data: bytes=None):
        assert type(data) is bytes, "data has to be given as bytes"
        return zlib.compress(data, level=9)

    def decompress(self, comp: bytes=None):
        assert type(comp) is bytes, "compressed data has to be given as bytes"
        return zlib.decompress(comp)
