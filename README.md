# EvoCount nexedge radio communication
This enables the Polling Device Manager to communicate via a radio link using Kenwood Nexedge devices.

## Prerequisites
The following things are needed.
* git
* Python >= 3.4 (as required by pySerial)
* pySerial >= 3.2.1

## Installation
* git clone `git@gitlab.com:evocount/nexedge.git`
* `cp radio_settings.json.sample radio_settings.json` and modify accordingly to your setup.

E.g. port is /dev/ttyAMA0 on the raspberry pi and usually /dev/ttyUSB0 on linux machines.

## Usage
See `test_radio.py` for a short example.
* `from radio import Radio`
* open a serial connection `ser = serial.Serial(...)`
* get an instance of the radio object `radio = Radio(serialcon=ser, max_chunk_size=4096)`
* the second parameter specifies the maximum message size (in bytes) for a *long distance message (LDM)*
* send dictionaries `radio.send(data=data, target=b'00011')` of json data
* receive dictionaries with `data = radio.get()`

## Resources
* pySerial documentation https://pyserial.readthedocs.io/en/latest/pyserial.html
* especially https://pyserial.readthedocs.io/en/latest/pyserial_api.html#module-serial.threaded
* json documentation https://docs.python.org/3/library/json.html

## How does it work?
This will only be a short explanation, the code is quite explanatory.

### Receiving
We constantly get data via the serial connection, every packet starts with `b'\x02'` and ends with `b'\x03'`. By calling `Radio()` a `ReaderThread` (see pySerial docs) is initialized.
The ReaderThread uses the `NexedgePacketizer(FramedPacket)` to handle all data. In short it passes the `b'CONTENT'` in `b'\x02CONTENT\x03'` to the `handle_packet` method.
The first 2 bytes in `b'CONTENT'` decide on the type of this packet, in case of a *long distance message (LDM)* the message is put into `answer_queue`. In case of status messages (i.e. channel is free or occupied) the `channel_status` object is updated.

### Sending
The Thread `send_worker` loops over send-commands in the `send_queue` and sends them if the channel is free. If a error is received, the command is sent again.

### Receiving and sending dictionaries
#### `Radio.send(...)` method
Every json-dictionary has a string representations. The string representations is encoded and split into parts with a `max_chunk_size - 8` (i.e. 4096 - 8 = 4088 bytes). The first chunk is placed behind a identifier string `b'json'`, the same is placed after the last chunk (hence the maximum chunk size - 8, because `len(b'json') = 4`). All chunks are put into the send_queue in order.

#### `Radio.get()` method
The instance of `Radio()` starts a `unite_worker` which task is to look for the start identifier `b'json'` in a message and concat all following messages until the stop identifier `b'json'` is found. The resulting string is now loaded into a json-dictionary and put into the `data_queue`. The `get()` method calls `data_queue.get()` and returns the dict if there is one, else `None` is returned.
