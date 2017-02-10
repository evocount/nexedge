import time
import serial


# configure the serial connections (the parameters differs on the device you are connecting to)
ser = serial.Serial ("/dev/ttyAMA0")
ser.baudrate=9600
ser.parity=serial.PARITY_NONE
ser.stopbits=serial.STOPBITS_TWO
ser.bytesize=serial.EIGHTBITS

# some predefined standardfunctions

#Callfunctions
def startcall():
	ser.write("\x02" + "A" + "\x03")
	
def endcall():
	ser.write("\x02" + "C" + "\x03")


#message functions
def shortGroupMessage(GroupID,message):
	ser.write("\x02" + "g" + "F" + "G" + GroupID + message + "\x03")
	
def shortMessage2all(message):
	ser.write("\x02" + "g" + "F" + "G" + "00000" + message + "\x03")
	
def shortMessage2Unit(UnitID,message):
	ser.write("\x02" + "g" + "F" + "U" + UnitID + message + "\x03")

# ----
	
def longGroupMessage(GroupID,message):
	ser.write("\x02" + "g" + "G" + "G" + GroupID + message + "\x03")
	
def longMessage2all(message):
	ser.write("\x02" + "g" + "G" + "G" + "00000" + message + "\x03")

def longMessage2Unit(UnitID,message):
	ser.write("\x02" + "g" + "G" + "U" + UnitID + message + "\x03")
 

#status functions
def setGroupStatus(GroupID,status):
	ser.write("\x02" + "g" + "E" + "G" + GroupID + status + "\x03")
	
def setUnitStatus(UnitID,status):
	ser.write("\x02" + "g" + "E" + "U" + UnitID + status + "\x03")



GroupID = "00010"
status = "003"
UnitID = "00012"
message = "hallo Welt!"

ser.isOpen()
while True:
	startcall()
	time.sleep(1)
	endcall()
	time.sleep(1)
	shortMessage2Unit(UnitID, message)
	time.sleep(3)
	setGroupStatus(GroupID, status)
	time.sleep(3)	