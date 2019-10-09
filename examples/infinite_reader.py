import logging
import logging.config
import asyncio
import json

from nexedge import *

if __name__ == '__main__':
    # logging
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': logging.DEBUG,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'root': {
            'handlers': ['default'],
            'level': logging.DEBUG,
        }
    })

    # async loop
    loop = asyncio.get_event_loop()

    serial_conf = {
        "url": '/dev/ttyUSB1',
        "baudrate": 9600,
        #"baudrate": 57600,
    }
    # r = Radio(loop=loop, serial_kwargs=serial_conf, retry_sending=False)
    # loop.create_task(read_queue(r.data_queue))
    # loop.create_task(read_channel(r.channel))
    # loop.create_task(r.receiver())
    # loop.create_task(send_random(r))
    # loop.create_task(trigger_channel_status(r))

    # add listener for "about-me"
    c = RadioCommunicator(loop=loop,
                          serial_kwargs=serial_conf,
                          listeners=["about-me", "about-you"])

    # start the handler
    loop.create_task(c.data_handler())
    loop.create_task(listen_listener_receiver(c, "about-you"))
    loop.create_task(listen_target_receiver(c, b"00002"))
    # dt_nom = 20
    # for s in range(1, 5):
    #     loop.create_task(send_via_com(c, s*dt_nom))

    loop.run_forever()
    loop.close()
