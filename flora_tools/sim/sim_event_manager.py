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
    GENERIC = 5
    TX_DONE_BEFORE_RX_TIMEOUT = 6


class SimEventManager:
    def __init__(self, network: 'sim_network.SimNetwork', event_count: int = 1000):
        self.network = network
        self.event_count = event_count
        self.eq = pd.DataFrame(
            columns=['timestamp', 'local_timestamp', 'node', 'type', 'data', 'callback'])
        self.processed_eq = pd.DataFrame(
            columns=['timestamp', 'local_timestamp', 'node', 'type', 'data', 'callback'])

    def loop(self, iterations=1):
        while self.event_count > 0:
            for i in range(iterations):
                self.eq = self.eq.sort_values(by=['timestamp'])
                event = self.eq.iloc[0]
                self.eq = self.eq.iloc[1:len(self.eq)]

                self.process_event(event)

            self.event_count -= iterations

    def process_event(self, event):
        print("{},\t{},\t{},\t{}".format(event['timestamp'], event['node'].id, event['type'], event['callback'].__qualname__))
        print(self.eq)
        self.network.global_timestamp = event['timestamp']
        event['node'].local_timestamp = event['local_timestamp']
        event['callback'](event)
        self.processed_eq.loc[len(self.processed_eq)] = event

    def register_event(self, timestamp: float, node: 'sim_node.SimNode', event_type: SimEventType,
                       callback, data=None):

        self.eq.loc[len(self.eq)] = [
            node.transform_local_to_global_timestamp(timestamp),
            timestamp, node, event_type, data, callback]

    def unregister_event(self, index):
        self.eq.drop(index, inplace=True)
