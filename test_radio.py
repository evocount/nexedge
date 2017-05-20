from main_radio import Radio
import time
import serial
import json

testnachricht = "Hallo Welt hier spricht EvoCount"

test_json_str ='{"id":4,"username":"mertel-blinn","email":"tim.mertel-blinn@evocount.de","first_name":"Tim","last_name":"Mertel-Blinn","is_device":false,"current_or_next_event":{"title":"DASA 2017","id":186,"valid_from":"2017-03-03T16:11:00Z","valid_to":"2017-12-31T22:59:32Z","is_valid_now":true,"current_count":8,"hard_limit":0,"limit":1000,"current_state":"OPN","log_interval":30},"is_superuser":true,"managed_devices":null,"my_location":null,"my_passage":null,"my_last_notifications":[]}'
test_json = json.loads(test_json_str)

print(test_json)

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
    print(radio.get())
    radio.send(test_json, b'00011')
    for i in range(0, 100):
        print(radio.get())
        time.sleep(1)

