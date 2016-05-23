# -*- coding: utf-8 -*-
"""The Raspberry http thread

Server files using the http protocol

"""

__license__ = """
    This file is part of Janitoo.

    Janitoo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Janitoo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Janitoo. If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

import logging
logger = logging.getLogger(__name__)
import os, sys
import threading

from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.component import JNTComponent

import Adafruit_DHT

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_WEB_CONTROLLER = 0x1030
COMMAND_WEB_RESOURCE = 0x1031
COMMAND_DOC_RESOURCE = 0x1032

assert(COMMAND_DESC[COMMAND_WEB_CONTROLLER] == 'COMMAND_WEB_CONTROLLER')
assert(COMMAND_DESC[COMMAND_WEB_RESOURCE] == 'COMMAND_WEB_RESOURCE')
assert(COMMAND_DESC[COMMAND_DOC_RESOURCE] == 'COMMAND_DOC_RESOURCE')
##############################################################

def make_dht(**kwargs):
    return DHTComponent(**kwargs)

SENSORS = { 11: Adafruit_DHT.DHT11,
            22: Adafruit_DHT.DHT22,
            2302: Adafruit_DHT.AM2302 }

class DHTComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'rpibasic.dht')
        name = kwargs.pop('name', "Input")
        product_name = kwargs.pop('product_name', "DHT")
        product_type = kwargs.pop('product_type', "Temperature/humidity sensor")
        product_manufacturer = kwargs.pop('product_manufacturer', "Janitoo")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                product_name=product_name, product_type=product_type, product_manufacturer=product_manufacturer, **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

        uuid="pin"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The pin number on the board',
            label='Pin',
            default=kwargs.pop('pin', 1),
        )
        uuid="sensor"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The sensor type : 11,22,2302',
            label='Type',
            default=kwargs.pop('sensor', 11),
        )
        uuid="temperature"
        self.values[uuid] = self.value_factory['sensor_temperature'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The temperature',
            label='Temp',
            get_data_cb=self.temperature,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value

        uuid="humidity"
        self.values[uuid] = self.value_factory['sensor_humidity'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The humidity',
            label='Hum',
            get_data_cb=self.humidity,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value
        self._dht_lock =  threading.Lock()

    def dht_read(self, sensor=11, pin=1):
        ret = None,None
        self._dht_lock.acquire()
        try:
            ret = Adafruit_DHT.read_retry(sensor, pin)
            return ret
        except Exception:
            logger.exception('[%s] - Exception when reading sensor : %s, %s', self.__class__.__name__, sensor, pin)
        finally:
            self._dht_lock.release()
        return None,None

    def temperature(self, node_uuid, index):
        """ Retrieve temperature """
        humidity, temperature = self.dht_read( \
            SENSORS[self.values['sensor'].get_data_index(index=index)],
            self.values['pin'].get_data_index(index=index)
        )
        self.values['temperature'].set_data_index(index=index, data=temperature)
        return temperature

    def humidity(self, node_uuid, index):
        """ Retrieve humidity """
        self.values['humidity'].set_data_index(index=index, data=None)
        humidity, temperature = self.dht_read( \
            SENSORS[self.values['sensor'].get_data_index(index=index)],
            self.values['pin'].get_data_index(index=index)
        )
        self.values['humidity'].set_data_index(index=index, data=humidity)
        return humidity

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        if 'temperature' not in self.values:
            return False
        return self.values['temperature'].data is not None
