import time
import serial
import threading
import re



# configure the serial connections 
ser = serial.Serial ("/dev/ttyAMA0")
ser.baudrate=9600
ser.parity=serial.PARITY_NONE
ser.stopbits=serial.STOPBITS_TWO
ser.bytesize=serial.EIGHTBITS


#process 
#process messages
def process_message(message):
	sender = message[4:9] 		#extract sender ID
	text = message[15:] 		#extract message
	print "Sender-ID: " + sender
	print "Message: " + text
	#return text
	
#process status
def process_status(message):
	sender = message[4:9]
	status = message[15:]
	print "Sender-ID: " + sender
	print "Status: " + status
	#return status

#process channel state
def process_device(message):
	hexmessage = message.encode("hex")
	led = hexmessage[-3]
	if led == "1": 			#receiving
		print "receive"
		
	elif led == "2": 		#sending
		print "send"
		
	elif led == "4":		 #idle
		print "orange" 
		
	elif led == "0": 		 #free
		print "channel free"
		
	else:
		print "no valid state"


#handle serial input per string
def handle_data(stringliste):

    if re.search(r"gF",stringliste) != None: #SDM
		process_message(stringliste)
		
    if re.search(r"gG",stringliste) != None: #LDM
    	process_message(stringliste)
    	
    if re.search(r"gE",stringliste) != None: #StatusMessage
    	print stringliste
    	
    if re.search(r"JA",stringliste) != None: #Device status
    	process_device(stringliste)
    
    if re.search(r"JA",stringliste) != None: #Device status
    	process_device(stringliste)



#read serial data per string
def read_from_port(ser):
	stringliste= ""
	while True:
		for c in ser.read():
			stringliste += str(c)
			if c == '\x03':
				handle_data(stringliste)
				stringliste = "" 
				break


thread = threading.Thread(target=read_from_port, args=(ser,))
thread.start()
