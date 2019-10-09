# radio device exceptions

class RadioException(Exception):
    pass


class DeviceNotFound(RadioException):
    """
    The radio device under the given address was not found or otherwise unable
    to connect.
    """
    pass


# receiver Exceptions
class ReceiverException(RadioException):
    pass


class ListenerNotDefined(ReceiverException):
    """
    The listener queue was not defined.
    """


# sender exceptions
class SenderException(RadioException):
    pass


class PayloadTooLarge(SenderException):
    """
    The payload size exceeded the maximum send size.
    """
    pass


class ChannelTimeout(SenderException):
    """
    The channel timed out during send, this means, that the channel was
    not free for a set duration that exceeded
    the limit.
    """
    pass


class ConfirmationTimeout(SenderException):
    """
    The confirmation message for a command was not received in a given
    frame of time.
    """
    pass


class SendMaxRetries(SenderException):
    """
    The number of failed send attempts exceeded the maximum number.
    """
    pass
