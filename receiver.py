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
	#print "Sender-ID: " + sender
	#print "Message: " + text
	return text
	
#process status
def process_status(message):
	sender = message[4:9]
	status = message[15:]
	#print "Sender-ID: " + sender
	#print "Status: " + status
	return status

#process channel state
def process_device(message):
	hexmessage = message.encode("hex")
	led = hexmessage[-3]
	if led == "1": 			#receiving
		return "receive"
		
	elif led == "2": 		#sending
		return "send"
		
	elif led == "4":		 #idle
		return "orange" 
		
	elif led == "0": 		 #free
		return "channel free"
		
	else:
		return "no valid state"


#handle serial input per string
def handle_data(stringliste):

    if stringliste[1] == "g" and stringliste[2] == "F" : #SDM
        answer = process_message(stringliste)
        return answer
        		
    if stringliste[1] == "g" and stringliste[2] == "G" : #LDM
    	answer = process_message(stringliste)
    	#print "longmessage"
        return answer
            	
    if stringliste[1] == "g" and stringliste[2] == "E" : #StatusMessage
    	answer = stringliste
        return answer
            	
    
    if stringliste[1] == "J" and stringliste[2] == "A":  #Device status
    	answer = process_device(stringliste)
        return answer
    
    if stringliste[1] == "J" and stringliste[2] == "E" : #DisplayContent
    	return None
    
    if stringliste[1] == "0" : #transmission success
    	return "success"
    
    if stringliste[1] == "1" : #transmission error
    	return "error"
    	
    else:
    	return None


#read serial data per string
def read_from_port(ser,q):
	#print "entered thread"
	stringliste= ""
	if ser.read() == '\x02':
		while True:
			#print "startbit found"
			for c in ser.read():
				stringliste += str(c)
				if c == '\x03':
					#print "endbit found"
					answer = handle_data(stringliste)
					stringliste = "" 
					if answer != None:
					    #print answer
					    q.put(answer)
					break



