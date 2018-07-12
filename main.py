"""
Copyright (C) EvoCount UG - All Rights Reserved
Unauthorized copying of this file, via any medium is strictly prohibited
Proprietary and confidential

Suthep Pomjaksilp <sp@laz0r.de> 2018
"""

import logging
import asyncio
import json

from nexedge import Radio, read_channel, read_queue, send_random

if __name__ == '__main__':
    # logging
    logging.basicConfig(level=logging.DEBUG)

    # async loop
    loop = asyncio.get_event_loop()

    serial_conf = {
        "url": '/dev/ttyUSB0',
        "baudrate": 9600,
        #"baudrate": 57600,
    }
    r = Radio(loop=loop, serial_kwargs=serial_conf, retry_sending=False)
    loop.create_task(read_queue(r.data_queue))
    loop.create_task(read_channel(r.channel))
    loop.create_task(r.receiver())
    loop.create_task(send_random(r))

    loop.run_forever()
    loop.close()
