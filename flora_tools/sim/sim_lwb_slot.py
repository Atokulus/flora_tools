import logging

import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_gloria import SimGloriaFlood
from flora_tools.sim.sim_message import SimMessage, SimMessageType
from flora_tools.sim.sim_tracer import LWBSlotActivity


class SimLWBSlot:
    def __init__(self, node: 'sim_node.SimNode', slot: 'lwb_slot.LWBSlot', callback, master: 'sim_node.SimNode' = None,
                 message=None):
        self.logger = logging.getLogger(self.__class__.__qualname__)

        self.node = node
        self.slot = slot
        self.message = message
        self.callback = callback
        self.master = master

        self.power_increase = True
        self.update_timestamp = True

        if slot.type is lwb_slot.LWBSlotType.DATA:
            self.power_increase = False
            self.update_timestamp = False
        elif slot.type in [lwb_slot.LWBSlotType.CONTENTION]:
            self.update_timestamp = False

        self.node.network.tracer.log_activity(
            LWBSlotActivity(slot.slot_marker, slot.slot_end_marker, self.node,
                            slot.type, slot.modulation)
        )

        self.log_slot()

        SimGloriaFlood(self.node, self.slot.flood, self.finished_flood, init_tx_message=self.message,
                       power_increase=self.power_increase, update_timestamp=self.update_timestamp)

    def log_slot(self):
        self.logger.info(
            "Marker:{:10f}\tNode:{:3d}\tMod:{:2d}\tType:{:16s}".format(self.slot.slot_marker,
                                                                       self.node.id,
                                                                       self.slot.modulation,
                                                                       self.slot.type))

    def finished_flood(self, message: 'SimMessage'):
        if self.node.role is sim_node.SimNodeRole.BASE:
            if message is not None and message.source is not self.node:
                self.node.lwb.link_manager.upgrade_link(message.source, message.modulation, message.freeze_power_level)
        else:
            if self.slot.type in [lwb_slot.LWBSlotType.SYNC,
                                  lwb_slot.LWBSlotType.SLOT_SCHEDULE,
                                  lwb_slot.LWBSlotType.ROUND_SCHEDULE]:
                if message is not None and message.type in [SimMessageType.SYNC,
                                                            SimMessageType.SLOT_SCHEDULE,
                                                            SimMessageType.ROUND_SCHEDULE]:
                    self.node.lwb.link_manager.upgrade_link(message.source, message.modulation,
                                                            message.freeze_power_level)
                elif self.master is not None:
                    self.node.lwb.link_manager.downgrade_link(self.master)
            elif self.slot.type in [lwb_slot.LWBSlotType.ACK]:
                if message is not None:
                    self.node.lwb.link_manager.upgrade_link(message.source, message.modulation,
                                                            message.freeze_power_level)

        self.callback(message)
