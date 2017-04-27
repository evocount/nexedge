#!/usr/bin/python3

import time
import serial

# configure the serial connections (the parameters differs on the device you are connecting to)
ser = serial.Serial("/dev/ttyUSB0")
ser.baudrate = 9600
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_TWO
ser.bytesize = serial.EIGHTBITS


# some predefined standardfunctions

# Callfunctions
def startcall():
    # encode str message to bytes
    command_as_bytes = ("\x02" + "A" + "\x03").encode()

    # write to serial port
    ser.write(command_as_bytes)


def endcall():
    command_as_bytes = ("\x02" + "C" + "\x03").encode()
    ser.write(command_as_bytes)


# message functions
def shortGroupMessage(GroupID, message):
    command_as_bytes = ("\x02" + "g" + "F" + "G" + GroupID + message + "\x03").encode()
    ser.write(command_as_bytes)


def shortMessage2all(message):
    command_as_bytes = ("\x02" + "g" + "F" + "G" + "00000" + message + "\x03").encode()
    ser.write(command_as_bytes)


def shortMessage2Unit(UnitID, message):
    command_as_bytes = ("\x02" + "g" + "F" + "U" + UnitID + message + "\x03").encode()
    ser.write(command_as_bytes)


# ----

def longGroupMessage(GroupID, message):
    command_as_bytes = ("\x02" + "g" + "G" + "G" + GroupID + message + "\x03").encode()
    ser.write(command_as_bytes)


def longMessage2all(message):
    command_as_bytes = ("\x02" + "g" + "G" + "G" + "00000" + message + "\x03").encode()
    ser.write(command_as_bytes)


def longMessage2Unit(UnitID, message):
    command_as_bytes = ("\x02" + "g" + "G" + "U" + UnitID + message + "\x03").encode()
    ser.write(command_as_bytes)


# status functions
def setGroupStatus(GroupID, status):
    command_as_bytes = ("\x02" + "g" + "E" + "G" + GroupID + status + "\x03").encode()
    ser.write(command_as_bytes)


def setUnitStatus(UnitID, status):
    command_as_bytes = ("\x02" + "g" + "E" + "U" + UnitID + status + "\x03").encode()
    ser.write(command_as_bytes)



    # GroupID = "00010"
    # status = "003"
    # UnitID = "00012"
    # message = "hallo Welt!"

    # ser.isOpen()
    # while True:
    # startcall()
    # time.sleep(1)
    # endcall()
    # time.sleep(1)
    # longMessage2Unit(UnitID, message)
    # time.sleep(10)
    # setGroupStatus(GroupID, status)
    # time.sleep(3)
