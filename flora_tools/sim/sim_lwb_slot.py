import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_gloria_flood import SimGloriaFlood
from flora_tools.sim.sim_message import SimMessage, SimMessageType


class SimLWBSlot:
    def __init__(self, node: 'sim_node.SimNode', slot: 'lwb_slot.LWBSlot', callback, master: 'sim_node.SimNode' = None,
                 message=None):
        self.node = node
        self.slot = slot
        self.message = message
        self.callback = callback
        self.tx_node = master

        self.power_increase = True
        self.update_timestamp = True

        if slot.type is lwb_slot.LWBSlotType.DATA:
            self.power_increase = False
            self.update_timestamp = False
        elif slot.type in [lwb_slot.LWBSlotType.CONTENTION, lwb_slot.LWBSlotType.ACK]:
            self.update_timestamp = False

        SimGloriaFlood(self.node, self.slot, self.finished_flood, init_tx_message=self.message,
                       power_increase=self.power_increase, update_timestamp=self.update_timestamp)

    def finished_flood(self, message: 'SimMessage'):
        if self.slot.type in [lwb_slot.LWBSlotType.SYNC, lwb_slot.LWBSlotType.SLOT_SCHEDULE]:
            if message is not None and message.type in [SimMessageType.SYNC, SimMessageType.SLOT_SCHEDULE]:
                self.node.lwb.link_manager.upgrade_link(message.source, message.modulation, message.power_level)
            else:
                self.node.lwb.link_manager.downgrade_link(self.tx_node.id)
        elif self.slot.type is lwb_slot.LWBSlotType.ACK:
            self.node.lwb.link_manager.acknowledge_link(message.source)
        elif message is not None:
            self.node.link_manager.upgrade_link(message.source, message.modulation, message.power_level)

        self.callback(message)
