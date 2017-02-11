import time
import serial
import threading
import re
from Queue import Queue
import receiver
import sender
import sys


testnachricht ="Hallo Welt hier spricht EvoCount"
channel_free = True

# configure the serial connections 
ser = serial.Serial ("/dev/ttyAMA0")
ser.baudrate=9600
ser.parity=serial.PARITY_NONE
ser.stopbits=serial.STOPBITS_TWO
ser.bytesize=serial.EIGHTBITS

#Setting up queueing and threading
q = Queue(maxsize=0)
thread = threading.Thread(target=receiver.read_from_port, args=(ser,q,))
thread.setDaemon(True)
thread.start()


#send function
def send(ser,q, device_function, masterID):
	send_success = False
	timeout = 10 # [seconds]
	global testnachricht #access global message for transmission
	while send_success == False:  # try til success or timeout/error
			sender.longMessage2Unit(masterID,testnachricht)
			timeout_start = time.time()
            
			while time.time() < timeout_start + timeout: #set timeout of 10 seconds
				serialqueue = q.get()
				if serialqueue  == "success":
					send_success = True
					testnachricht = ""  #clear message
					return
				elif serialqueue == "error": #if device error
					print "Error"
					return
				else:
					pass
			return #timeout


#read from serial
def read(ser,q):
	try: #try if there's some data for us
		data = q.get(False)  
	except:
		data = None
	#function for setting channel status
	if data != "channel free":
		channel_free = False
	else:
		channnel_free = True
	#------ here should follow some code
	if data != None:
		print data


#main process
def main(ser,q,testnachricht):
	device_function = "Slave" #Master or Slave device should be set in future externally
	masterID = "00012" #should also beeing set via remote
	while True:
		if testnachricht != "": # transmit if there's a message
			if channel_free == True:
				print "start"
				send(ser, q, device_function, masterID)
				break
			else:
				pass
		else:
			pass
		read(ser,q) # if not, be on standby and read from serial
    
while True:
	main(ser,q,testnachricht)


