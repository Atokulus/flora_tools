from enum import Enum
from typing import Callable

import pandas as pd

import flora_tools.sim.sim_network as sim_network
import flora_tools.sim.sim_node as sim_node


class SimEventType(Enum):
    TX_DONE = 1
    RX_TIMEOUT = 2
    RX_DONE = 3
    CAD_DONE = 4
    UPDATE = 5
    TX_DONE_BEFORE_RX_TIMEOUT = 6


class SimEventManager:
    def __init__(self, network: 'sim_network.SimNetwork'):
        self.network = network
        self.eq = pd.DataFrame(columns=['timestamp', 'local_timestamp', 'node', 'type', 'data', 'callback'])

    def loop(self, iterations=1):
        for i in range(iterations):
            self.eq = self.eq.sort_values(by=['timestamp'])
            event = self.eq[self.eq.timestamp >= self.network.current_timestamp].iloc[0, :]
            self.process_event(event)
            self.network.current_timestamp = event['timestamp']
            event['node'].local_timestamp = event['local_timestamp']

    @staticmethod
    def process_event(event):
        event['callback'](event)

    def register_event(self, timestamp: float, node: 'sim_node.SimNode', type: SimEventType,
                       callback: Callable[[None], None], data=None):
        self.eq.loc[len(self.eq)] = [node.transform_local_to_global_timestamp(timestamp), timestamp, node, type, data,
                                     callback]

        return len(self.eq) - 1

    def unregister_event(self, index):
        self.eq.drop(index, inplace=True)
