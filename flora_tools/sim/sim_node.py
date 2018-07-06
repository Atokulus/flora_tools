import numpy as np
import pandas as pd

from flora_tools.sim.sim_network import SimNetwork
from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_link_manager import SimLinkManager
from flora_tools.sim.sim_message_manager import SimMessageManager
from flora_tools.sim.sim_event_manager import  SimEventManager


class SimNode:
    def __init__(self, network: 'SimNetwork', em: SimEventManager, mm: SimMessageManager, id: int=None, role='sensor', datarate=10):
        self.state = 'init'
        self.network = network
        self.mm = mm
        self.em = em
        self.id = id
        self.role = role
        self.datarate = datarate

        self.link_manager = SimLinkManager(self)
        self.last_timestamp = None
        self.pipelined_message = None
        self.accumulated_data = 0.0

        self.current_base = None
        self.local_timestamp = 0

        if self.role is 'base':
            self.start_base()
        elif self.role is 'sensor':
            self.start_sensor()
        elif self.role is 'relay':
            self.start_relay()


    def __str__(self):
        return str(self.id)

    def start_base(self):
        pass

    def start_sensor(self):
        pass

    def start_relay(self):
        pass

    def generate_data(self, timestamp) -> SimMessage:
        if self.last_timestamp is not None:
            elapsed = timestamp - self.last_timestamp
            self.accumulated_data += elapsed * self.datarate
        else:
            self.accumulated_data += self.datarate
        self.last_timestamp = timestamp
        data = np.min(np.floor(self.accumulated_data), 255)
        self.accumulated_data -= data
        return SimMessage(data, self.id, 0, 'data')

    def transform_local_to_global_timestamp(self, timestamp):
        timestamp - self.local_timestamp + self.network.current_timestamp








