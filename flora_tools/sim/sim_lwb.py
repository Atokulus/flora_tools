from enum import Enum

import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.cad_sync import CADSync
from flora_tools.sim.lwb_schedule_manager import LWBScheduleManager
from flora_tools.sim.sim_link_manager import LWBLinkManager
from flora_tools.sim.sim_lwb_round import SimLWBRound
from flora_tools.sim.stream import LWBStreamManager


class LWBState(Enum):
    CAD = 1
    ASSIGNED = 2


class SimLWB:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.rounds = []

        self.link_manager = LWBLinkManager(self.node)
        self.stream_manager = LWBStreamManager(self.node)
        self.schedule_manager = LWBScheduleManager(self.node)
        self.sync: CADSync = None

        if self.node.role is sim_node.SimNodeRole.BASE:
            self.base = self.node
            self.state: LWBState = LWBState.ASSIGNED
        else:
            self.base = None
            self.state: LWBState = LWBState.CAD

    def run(self):
        if self.state is LWBState.CAD:
            self.sync = CADSync(self.node)
            self.sync.run(self.sync_callback)
        elif self.state is LWBState.ASSIGNED:
            round = self.schedule_manager.get_next_round()
            if round is not None:
                SimLWBRound(self.node, self, round, self.round_callback)
            else:
                self.state = LWBState.CAD
                self.run()

    def round_callback(self, success):
        self.run()

    def sync_callback(self):
        self.state = LWBState.ASSIGNED
        self.run()
