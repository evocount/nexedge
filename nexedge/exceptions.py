"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

# this file defines all Exceptions used

# receiver Exceptions
class ReceiverException(Exception):
    pass


class ReceiveTimeout(ReceiverException):
    """
    The unifier thread received to messages in the answer_queue.
    """
    pass


class VerificationError(ReceiverException):
    """
    The received checksum does not match the generated checksum of the received data.
    """
    pass


# sender exceptions
class SenderException(Exception):
    pass

class PayloadTooLarge(SenderException):
    """
    The payload size exceeded the maximum send size.
    """
    pass

class ChannelTimeout(SenderException):
    """
    The channel timed out during send, this means, that the channel was not free for a set duration that exceeded
    the limit.
    """
    pass


class ConfirmationTimeout(SenderException):
    """
    The confirmation message for a command was not received in a given frame of time.
    """
    pass


class SendMaxRetries(SenderException):
    """
    The number of failed send attempts exceeded the maximum number.
    """
    pass
