
# base method to wrap the command into start and end bytes
def wrap(command: bytes):
    """
    Wrap the given command into the padding bytes \x02 and \x03
    :param command: bytes
    :return: padded command: bytes
    """
    start = b"\x02"
    stop = b"\x03"
    return start + command + stop


# service methods
def set_baudrate(baud: int=57600):
    """
    Set the baud rate to one of the possible values.
    Raises AssertionError if no valid value is used.
    :param baud: int
    :return: command: bytes
    """
    settings = {
        1200:   b"2",
        2400:   b"3",
        4800:   b"4",
        9600:   b"5",
        19200:  b"6",
        38400:  b"7",
        57600:  b"8",
    }

    assert baud in settings.keys(), "selected baudrate is not valid"
    return wrap(b"O" + settings[baud])


def set_repeat(repeat: bool=False):
    """
    Control if failed messages should be repeated.
    :param repeat: bool
    :return: command: bytes
    """
    settings = {
        True:   b"1",
        False:  b"0",
    }
    return wrap(b"k" + b"R" + settings[repeat])


def channel_status_request():
    """
    Ask the receiver politely to report its channel status.
    :return: command: bytes
    """
    return wrap(b"J" + b"C" + b"A")


# Callfunctions
def startcall() -> bytes:
    """
    Starting a voice call
    :return:
    """
    return wrap(b"A")


def endcall() -> bytes:
    """
    Ending a voice call
    :return:
    """
    return wrap(b"C")


# message functions
def shortGroupMessage(groupID: bytes, message: bytes) -> bytes:
    """
    Short group message (will be displayed on the unit)
    :param groupID:
    :param message:
    :return:
    """
    return wrap(b"g" + b"F" + b"G" + groupID + message)


def shortMessage2all(message: bytes):
    """
    Short message to all units (will be displayed on the unit)
    :param message:
    :return:
    """
    return wrap(b"g" + b"F" + b"G" + b"00000" + message)


def shortMessage2Unit(unitID: bytes, message: bytes) -> bytes:
    """
    Short message to one unit (will be displayed on the unit)
    :param unitID:
    :param message:
    :return:
    """
    return wrap(b"g" + b"F" + b"U" + unitID + message)


def longGroupMessage(groupID: bytes, message: bytes) -> bytes:
    """
    Long message (4096 bytes) to group
    :param groupID:
    :param message:
    :return:
    """
    return wrap(b"g" + b"G" + b"G" + groupID + message)


def longMessage2all(message: bytes) -> bytes:
    """
    Long message (4096 bytes) to all units
    :param message:
    :return:
    """
    return wrap(b"g" + b"G" + b"G" + b"00000" + message)


def longMessage2Unit(unitID: bytes, message: bytes) -> bytes:
    """
    Long message (4096 bytes) to one unit
    :param unitID:
    :param message:
    :return:
    """
    return wrap(b"g" + b"G" + b"U" + unitID + message)


# status functions
def setGroupStatus(groupID: bytes, status: bytes) -> bytes:
    """
    Sets the status for a group
    :param groupID:
    :param status:
    :return:
    """
    return wrap(b"g" + b"E" + b"G" + groupID + status)


def setUnitStatus(unitID: bytes, status: bytes) -> bytes:
    """
    Sets the status for a unit
    :param unitID:
    :param status:
    :return:
    """
    return wrap(b"g" + b"E" + b"U" + unitID + status)


# get status information
# does not work
def getChannelStatus() -> bytes:
    """
    Get the
    :return:
    """
    return wrap(b"j" + b"c" + b"s")
