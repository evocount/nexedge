"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""

import asyncio
import serial_asyncio
from .pcip_commands import *

async def read_queue(queue):
    """
    Dummy routine to echo the received data queue.
    :param queue:
    :return:
    """
    while True:
        s, m = await queue.get()
        print("received from {}: {}".format(s, m))


async def read_channel(channel):
    """
    Dummy routine to echo the channel status.
    :param channel:
    :return:
    """
    while True:

        print("channel is free: {}".format(channel.free()))
        await asyncio.sleep(1)


async def listen_listener_receiver(com, namespace):
    """
    Dummy routine to echo the received data queue.
    :param queue:
    :return:
    """
    while True:
        queue = com.get_listener_queue(namespace)
        remote_id, data = await queue.get()
        print(f"{namespace} from {remote_id} {data['payload']}")


async def listen_target_receiver(com, target):
    """
    Dummy routine to echo the received data queue.
    :param queue:
    :return:
    """
    n = 1
    while True:
        queue = com.get_target_queue(target=target)
        remote_id, data = await queue.get()
        print(f"from {remote_id} {data['payload']}")
        print(f"received {n} packages")
        n += 1


async def send_random(radio, start=5):
    """
    Just send some encoded data to test most basic receiving.
    :param radio:
    :return:
    """
    import random
    dt = random.randrange(start=start, stop=(start+10))
    print("waiting for {} seconds".format(dt))
    await asyncio.sleep(dt)

    data_str = '{"id":4,"username":"mertel-blinn","email":"tim.mertel-blinn@evocount.de","first_name":"Tim","last_name":"Mertel-Blinn","is_device":false,"current_or_next_event":{"title":"DASA 2017","id":186,"valid_from":"2017-03-03T16:11:00Z","valid_to":"2017-12-31T22:59:32Z","is_valid_now":true,"current_count":8,"hard_limit":0,"limit":1000,"current_state":"OPN","log_interval":30},"is_superuser":true,"managed_devices":null,"my_location":null,"my_passage":null,"my_last_notifications":[]}'
    data_bytes = data_str.encode()

    loop = asyncio.get_event_loop()
    transmission = loop.create_task(radio.send_LDM(target_id=b"00006", payload=data_bytes))
    while not transmission.done():
        await asyncio.sleep(.1)
    print(transmission.result())

async def trigger_channel_status(radio):
    """
    Just send some encoded data to test most basic receiving.
    :param radio:
    :return:
    """
    import random
    dt = random.randrange(start=5, stop=10)
    print("waiting for {} seconds".format(dt))
    await asyncio.sleep(dt)

    loop = asyncio.get_event_loop()
    transmission = loop.create_task(radio.write(channel_status_request()))
    while not transmission.done():
        await asyncio.sleep(.1)
    print(transmission.result())


async def send_via_com(com, start=5):
    """
    Just send some encoded data to test most basic receiving.
    :param com:
    :return:
    """
    import json
    import random
    dt = random.randrange(start=start, stop=(start+10))
    print("waiting for {} seconds".format(dt))
    await asyncio.sleep(dt)

    data_str = '{"id":4,"username":"mertel-blinn","email":"tim.mertel-blinn@evocount.de","first_name":"Tim","last_name":"Mertel-Blinn","is_device":false,"current_or_next_event":{"title":"DASA 2017","id":186,"valid_from":"2017-03-03T16:11:00Z","valid_to":"2017-12-31T22:59:32Z","is_valid_now":true,"current_count":8,"hard_limit":0,"limit":1000,"current_state":"OPN","log_interval":30},"is_superuser":true,"managed_devices":null,"my_location":null,"my_passage":null,"my_last_notifications":[]}'
    data = json.loads(data_str)

    transmission = await com.send(target_id=b"00006", data=data)
    print(transmission)


# this is basically a copy from the pyserial_async source, but we need to get
# the transport out to manipulate serial parameters
@asyncio.coroutine
def open_serial_connection(*,
                           loop=None,
                           limit=asyncio.streams._DEFAULT_LIMIT,
                           **kwargs):
    """
    A wrapper for create_serial_connection() returning a (reader,
    writer) pair.
    The reader returned is a StreamReader instance; the writer is a
    StreamWriter instance.
    The arguments are all the usual arguments to Serial(). Additional
    optional keyword arguments are loop (to set the event loop instance
    to use) and limit (to set the buffer limit passed to the
    StreamReader.
    This function is a coroutine.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader(limit=limit, loop=loop)
    protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
    transport, _ = yield from serial_asyncio.create_serial_connection(
        loop=loop,
        protocol_factory=lambda: protocol,
        **kwargs)
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)
    return transport, reader, writer
