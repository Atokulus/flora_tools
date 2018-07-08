from flora_tools.sim.sim_node import SimNode
import numpy as np


class SimMessage:
    def __init__(self, timestamp, source: 'SimNode', payload, modulation, destination=None, type='data', content=None, power_level=0, id=None):
        self.timestamp = timestamp
        self.id = None
        self.source = source
        self.destination = destination
        self.type = type
        self.payload = payload
        self.content = content
        self.modulation = modulation

        if id is not None:
            self.id = id
        else:
            self.id = np.random.randint(256)

        self.power_level = power_level

        self.hop_count = 0
        self.tx_end = None

    def __copy__(self):
        message = SimMessage(timestamp=self.timestamp,
                             source=self.source,
                             payload=self.payload,
                             destination=self.destination,
                             type=self.type,
                             content=self.content,
                             power_level=self.power_level,
                             modulation=self.modulation,
                             id=self.id)

        message.hop_count = self.hop_count
        return message

    def increase_timestamp(self, offset):
        self.timestamp += offset
