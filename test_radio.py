from main_radio import Radio
import time
import serial
import json

testnachricht = "Hallo Welt hier spricht EvoCount"

# load serial configuration from json formatted file
with open("config.json", "r") as fpointer:
    config = json.load(fpointer)

ser = serial.Serial(config["serial"]["port"])  # as str in config.json
ser.baudrate = config["serial"]["baudrate"]  # as int in config.json
ser.parity = eval(config["serial"]["parity"])  # we have to evaluate the code in the file
ser.stopbits = eval(config["serial"]["stopbits"])
ser.bytesize = eval(config["serial"]["bytesize"])

# radio = Radio(serialcon=ser, max_chunk_size=4096)

with Radio(serialcon=ser, max_chunk_size=4096) as radio:
    for i in range(0, 10):
        print(radio.get())
        time.sleep(2)