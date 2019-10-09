# EvoCount nexedge radio communication
This module provides high level data transmission via radio link using Kenwood Nexedge devices.

## Prerequisites
The following things are needed.
* git
* Python >= 3.6
* hardware serial device or RS232 dongle, the executing user has to have writing permission

## Installation
* git clone `git@github.com:evocount/nexedge.git`
* `cd nexedge && pipenv install`

## Transmitting and receiving data
The following sections will describe the what each component of this packages does.

### Short primer on radio communication
A radio transmission always consists of the transmitter or sender and the receiving unit.
The transmission itself _travels_ through a common radio channel.
If a sender/receiver pair is transmitting data, the channel is blocked.
Since usual case consists of more than 2 transceivers, only one pair can be actively sending at one point of time.

The nexedge devices by Kenwood provide two functions to transmit a payload via air.
Short-data-message (SDM) and long-data-messages (LDM) are handled by the devices.
SDMs are displayed on the screen, LDMs are not.

Interfacing the transceivers is possible via a serial interface at the back of the unit.
The RS232 is carried via a D-SUB25 connector.
In most cases a D-SUB9 to 25 serial modem cable is necessary since the device features a female connector.
By default the serial configuration is the following:
```python
import serial

baudrate = 9600
parity = PARITY_NONE
stopbits = serial.STOPBITS_TWO
bytesize = serial.EIGHTBITS
```

The data which is available via serial is encapsulated in packages with a start and s stop byte:
```python
\x02 SEQ DATA \x03
```
`SEQ` is an identifier for the type of package (display message, status message, LDM, SDM).

Controlling of the device is possible in the same way by constructing a command:
```python
\x02 gGU 00002 helloWorld \x03
```
In this case `b'gGU'` is the command for a LDM and `b'00002'` is the target transceiver.
Every command is followed by a ACK signal:
```python
\x02 1 \x03
```
or in the failing case:
```python
\x02 0 \x03
```
As transmissions can take up to 40s the ACK can be delayed by quite some time.

### Initializing `nexedge.RadioCommunicator`
When using you should only ever use this class.
The communicator provides provides a high-level interface to send and receive data via radio.

Example usage:
```python
loop = asyncio.get_event_loop()

com = RadioCommunicator(serial_kwargs=
                        {"url": settings.RADIO_SERIAL_URL,
                        "baudrate": settings.RADIO_SERIAL_BAUDRATE},
                        listeners=["about-me"],
                        timeout=settings.RADIO_TIMEOUT)

# start the handler for incoming data
loop.create_task(com.data_handler())
```

### Sending a payload with `nexedge.RadioCommunicator.send()`
Imagine you (transceiver b"00001") want to send the payload
```python
p = {
    "name":     "dog",
    "tail":     True,
    "sound":    "wuff"
}
```
to the target transceiver `b"00002"`.

Example with `com` from the above section:
```python
result = await com.send(target_id=b"00002",
                       data=p,
                       meta={})
```
First of all it is to note that `send` is a awaitable coroutine!

The return value of this command is either `True` or `False` as indicated by the ACK.
If no ACK at all is received during `timeout` => `ConfirmationTimeout` is raised.

Under the hood the data is placed into a dictionary:
```python
# add some meta data to our payload
data = {
    "counter":  self._counter,
    "meta":     meta,
    "payload":  data,
}
```
The counter just tags the transmission and metadata can be added as a dictionary.

### Receiving the payload with `nexedge.RadioCommunicator.get_target_queue()`
The `data_handler()` coroutine continuously places received data into the a so-called target queue.
This queue consists of tuples `(target_id, data)` of data which is received from the transceiver with a specific target id.
Note that every transceiver has a unique queue!

To receive the data from `b"00001"` (above section), you have to acquire the queue:
```python
queue = com.get_target_queue(target=`b"00001"`)
remote_id, data = await queue.get()
print(data["payload"])

"""
 {
    "name":     "dog",
    "tail":     True,
    "sound":    "wuff"
 }
"""
```
`remote_id` will carry `b"00002"`.

### Transmitting and receiving _broadcast_ data with triggers
The term broadcast has to be used with caution since the transmission still targets only one transceiver.
But in this case the target transceiver does not know beforehand from whom it will get data.
A classical use case in the `pdm` scenario is the transmission of the slave configuration, aka. its `about-me` data.

First we will observe the receiving side.
To retrieve such data, we have to listen for a `trigger`.
During initialization of the communicator a list of listeners can be given `listeners=["about-me"]`.
This sets up a separate `listener_queue` for this trigger.
To receive data the only thing we have to do is to get from this queue:
```python
queue = com.get_listener_queue("about-me")
remote_id, data = await queue.get()
```

As indicated beforehand the metadata of a transmission can be used to get transmit addition information.
The trigger is just a special metadata keyword:
```python
com.send(receiver=b"00002",
         data=self.model.configuration,
         meta={"trigger": "about-me"})
```

## Caveats
* the radio channel is a shared medium, even if the transmission is directed to a single transceiver, it still blocks the channel.
As a result the user has to make sure only one radio is talking at a time.
* a considerable amount of time is spent to wait until the radio channel is considered free again. If the channel is not updated for 10s, it is considered free and the transmission starts.
* `nexedge` does not do any retries of sending.
* transmissions can take up to 40s when sending 4000 bytes. To counter this, every data is serialized with json, compressed with zlib and encoded in base64. With this method up to 220 log events can be transmitted in one package.
