from enum import Enum

import numpy as np

import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath


class SimMessageType(Enum):
    SYNC = 1
    ROUND_SCHEDULE = 2
    SLOT_SCHEDULE = 3
    ROUND_REQUEST = 4
    STREAM_REQUEST = 5
    NOTIFICATION = 6
    DATA = 7
    ACK = 8


class SimMessage:
    def __init__(self, timestamp, source: 'sim_node.SimNode', payload, modulation, destination=None,
                 type=SimMessageType.DATA,
                 content=None, power_level=0, id=None, band=None, tx_start=None):
        self.timestamp = timestamp
        if id is not None:
            self.id = id
        else:
            self.id = np.random.randint(1024)
        self.source = source
        self.destination = destination
        self.type = type
        self.payload = payload
        self.content = content
        self.modulation = modulation
        self.band = band
        self.tx_start = tx_start

        if id is not None:
            self.id = id
        else:
            self.id = np.random.randint(256)

        self.power_level = power_level

        self.hop_count = 0
        self.radio_configuration = RadioConfiguration(lwb_slot.RADIO_MODULATIONS[modulation], lwb_slot.RADIO_POWERS[self.power_level], tx=True,
                                                      preamble=(2 if self.modulation > 7 else 3))
        self.radio_math = RadioMath(self.radio_configuration)

        self.freeze_hop_count = self.hop_count
        self.freeze_power_level = self.power_level

    def __copy__(self):
        message = SimMessage(timestamp=self.timestamp,
                             source=self.source,
                             payload=self.payload,
                             destination=self.destination,
                             type=self.type,
                             content=self.content,
                             power_level=self.power_level,
                             modulation=self.modulation,
                             band=self.band,
                             id=self.id)

        message.hop_count = self.hop_count
        message.tx_start = self.tx_start
        self.freeze_hop_count = self.hop_count
        self.freeze_power_level = self.power_level
        return message

    def copy(self):
        return self.__copy__()

    def __str__(self):
        return "<SimMessage {:f},{:d},{:d},{},{},{},{}>".format(
            self.timestamp,
            self.modulation,
            self.power_level,
            self.type,
            self.source,
            self.destination,
            self.payload
        )

    def increase_timestamp(self, offset):
        self.timestamp += offset

    def freeze(self):
        self.freeze_hop_count = self.hop_count
        self.freeze_power_level = self.power_level
        self.freeze_timestamp = self.timestamp

    @property
    def tx_end(self):
        return self.tx_start + self.radio_math.get_message_toa(payload_size=self.payload)

    @property
    def hash(self):
        return "{timestamp},{source},{destination},{type},{power_level},{hop_count},{id}".format(
            timestamp=self.timestamp,
            source=self.source,
            destination=self.destination,
            type=self.type,
            content=self.content,
            power_level=self.power_level,
            hop_count=self.hop_count,
            id=self.id)
