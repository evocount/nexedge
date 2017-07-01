"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

# this file defines all Exceptions used


# receiver Exceptions
class ReceiveTimeout(Exception):
    """
    The unifier thread received to messages in the answer_queue.
    """
    pass


class VerificationError(Exception):
    """
    The received checksum does not match the generated checksum of the received data.
    """
    pass


# sender exceptions
class ChannelTimeout(Exception):
    """
    The channel timed out during send, this means, that the channel was not free for a set duration that exceeded
    the limit.
    """
    pass


class ConfirmationTimeout(Exception):
    """
    The confirmation message for a command was not received in a given frame of time.
    """
    pass


class SendMaxRetries(Exception):
    """
    The number of failed send attempts exceeded the maximum number.
    """
    pass
