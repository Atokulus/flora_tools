import numpy as np

import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.lwb_schedule_manager import LWBScheduleManager
from flora_tools.sim.sim_link_manager import SimLinkManager
from flora_tools.sim.stream import StreamManager

BACKOFF_PERIOD = 1 / 8E6 * np.exp2(29)


class SimLWBManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.rounds = []

        self.link_manager = SimLinkManager(self)
        self.stream_manager = StreamManager(self)

        if self.node.role is 'base':
            self.base = self.node
        else:
            self.base = None

        self.lwb_schedule_manager = LWBScheduleManager(self.node)

    def run(self):
        pass
