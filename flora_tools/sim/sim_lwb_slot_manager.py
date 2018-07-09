from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_gloria_flood import SimGloriaFlood
import flora_tools.sim.sim_node as sim_node


class SimLWBSlotManager:
    def __init__(self, node: 'sim_node.SimNode', slot, callback, tx_node: 'sim_node.SimNode'=None, message=None):
        self.node = node
        self.slot = slot
        self.message = message
        self.callback = callback
        self.tx_node = tx_node

        self.power_increase = True
        self.update_timestamp = True

        if slot['type'] is 'data':
            self.power_increase = False
            self.update_timestamp = False
        elif slot['type'] in ['contention', 'ack']:
            self.update_timestamp = False

        SimGloriaFlood(self.node, self.slot['slot'], self.finished_flood, init_tx_message=self.message,
                       power_increase=self.power_increase, update_timestamp=self.update_timestamp)

    def finished_flood(self, message: 'SimMessage'):
        if self.slot['type'] in ['sync', 'slot_schedule']:
            if message is not None and message.type in ['sync', 'slot_schedule']:
                self.node.link_manager.upgrade_link(message.source, message.modulation, message.power_level)
            else:
                self.node.link_manager.downgrade_link(self.tx_node.id)

        elif message is not None:
                self.node.link_manager.upgrade_link(message.source, message.modulation, message.power_level)

        self.callback(message)