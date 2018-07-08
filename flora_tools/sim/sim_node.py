import numpy as np
import pandas as pd

from flora_tools.sim.sim_network import SimNetwork
from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_link_manager import SimLinkManager
from flora_tools.sim.sim_message_manager import SimMessageManager
from flora_tools.sim.sim_event_manager import SimEventManager
from flora_tools.sim.sim_lwb_manager import SimLWBManager


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
        self.lwb_manager = SimLWBManager(self)
        self.local_timestamp = 0

        self.lwb_manager.run()

    def __str__(self):
        return str(self.id)

    def start_base(self):
        pass

    def start_sensor(self):
        pass

    def start_relay(self):
        pass

    def transform_local_to_global_timestamp(self, timestamp):
        timestamp - self.local_timestamp + self.network.current_timestamp








