from enum import Enum

import numpy as np

import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.lwb_schedule_manager import LWBScheduleManager
from flora_tools.sim.sim_link_manager import SimLinkManager
from flora_tools.sim.stream import StreamManager


SYNC_PERIOD = 1 / 8E6 * np.exp2(31)  # 268.435456 s


class LWBState(Enum):
    CAD = 1
    SYNCED = 2
    ASSIGNED = 3


class SimLWB:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.rounds = []

        self.link_manager = SimLinkManager(self)
        self.stream_manager = StreamManager(self)
        self.state: LWBState = LWBState.CAD

        if self.node.role is 'base':
            self.base = self.node
        else:
            self.base = None

        self.lwb_schedule_manager = LWBScheduleManager(self.node)

    def run(self):
        pass
