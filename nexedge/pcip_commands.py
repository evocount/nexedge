"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2017
"""

# Callfunctions
def startcall() -> bytes:
    """
    Starting a voice call
    :return: 
    """
    command_as_bytes = (b"\x02" + b"A" + b"\x03")

    return command_as_bytes


def endcall() -> bytes:
    """
    Ending a voice call
    :return: 
    """
    command_as_bytes = (b"\x02" + b"C" + b"\x03")

    return command_as_bytes


# message functions
def shortGroupMessage(groupID: bytes, message: bytes) -> bytes:
    """
    Short group message (will be displayed on the unit)
    :param groupID: 
    :param message: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"F" + b"G" + groupID + message + b"\x03")

    return command_as_bytes


def shortMessage2all(message: bytes):
    """
    Short message to all units (will be displayed on the unit)
    :param message: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"F" + b"G" + b"00000" + message + b"\x03")

    return command_as_bytes


def shortMessage2Unit(unitID: bytes, message: bytes) -> bytes:
    """
    Short message to one unit (will be displayed on the unit)
    :param unitID: 
    :param message: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"F" + b"U" + unitID + message + b"\x03")

    return command_as_bytes


def longGroupMessage(groupID: bytes, message: bytes) -> bytes:
    """
    Long message (4096 bytes) to group
    :param groupID: 
    :param message: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"G" + b"G" + groupID + message + b"\x03")
    return command_as_bytes


def longMessage2all(message: bytes) -> bytes:
    """
    Long message (4096 bytes) to all units
    :param message: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"G" + b"G" + b"00000" + message + b"\x03")
    return command_as_bytes


def longMessage2Unit(unitID: bytes, message: bytes) -> bytes:
    """
    Long message (4096 bytes) to one unit
    :param unitID: 
    :param message: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"G" + b"U" + unitID + message + b"\x03")
    return command_as_bytes


# status functions
def setGroupStatus(groupID: bytes, status: bytes) -> bytes:
    """
    Sets the status for a group
    :param groupID: 
    :param status: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"E" + b"G" + groupID + status + b"\x03")
    return command_as_bytes


def setUnitStatus(unitID: bytes, status: bytes) -> bytes:
    """
    Sets the status for a unit
    :param unitID: 
    :param status: 
    :return: 
    """
    command_as_bytes = (b"\x02" + b"g" + b"E" + b"U" + unitID + status + b"\x03")
    return command_as_bytes
