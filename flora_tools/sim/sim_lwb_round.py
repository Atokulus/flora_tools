from collections import Callable
from enum import Enum

import flora_tools.lwb_round as lwb_round
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_lwb_manager as sim_lwb_manager
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_lwb_slot_manager import SimLWBSlotManager
from flora_tools.sim.sim_message import SimMessage, SimMessageType


class AckOperation(Enum):
    DATA = 1
    CONTENTION = 2


class SimLWBRound:
    def __init__(self, node: 'sim_node.SimNode', lwb_manager: 'sim_lwb_manager.SimLWBManager',
                 round: 'lwb_round.LWBRound', callback: Callable[[bool], None]):
        self.node = node
        self.lwb_manager = lwb_manager
        self.round = round
        self.callback = callback

        self.current_slot_index = 0
        self.ack_operation: AckOperation = None
        self.ack_id: int = None

        self.process_slot()

    def process_next_slot(self):
        self.current_slot_index += 1
        self.process_slot()

    def process_slot(self):
        slot = self.round.slots[self.current_slot_index]

        if self.slot_valid():
            if slot.type is not lwb_slot.LWBSlotType.ACK:
                self.ack_operation = None
                self.ack_id: int = None

            if slot.type is lwb_slot.LWBSlotType.SYNC:
                self.process_sync_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.SLOT_SCHEDULE:
                self.process_slot_schedule_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.ROUND_SCHEDULE:
                self.process_round_schedule_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.CONTENTION:
                self.process_contention_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.ROUND_CONTENTION:
                self.process_round_contention_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.DATA:
                self.process_data_slot(slot)
            elif slot.type is lwb_slot.LWBSlotType.ACK:
                self.process_ack_slot(slot)
            else:
                self.callback(False)
        else:
            self.callback(False)

    def process_sync_slot(self, slot: 'lwb_slot.LWBSlot'):
        if self.node.role is 'sim_node.SimNodeRole':
            message = SimMessage(slot.slot_marker, self.node, slot.payload,
                                 modulation=slot.modulation, destination=None, type=SimMessageType.SYNC,
                                 power_level=slot.power_level)
            SimLWBSlotManager(self.node, slot, self.process_sync_slot_callback, master=self.node,
                              message=message)
        else:
            SimLWBSlotManager(self.node, slot, self.process_sync_slot_callback, master=self.node.current_base,
                              message=None)

    def process_sync_slot_callback(self, message: SimMessage):
        self.process_next_slot()

    def process_slot_schedule_slot(self, slot: 'lwb_slot.LWBSlot'):
        if self.node.role is sim_node.SimNodeRole.BASE:
            slot_schedule = self.lwb_schedule_manager.slot_schedule
            message = SimMessage(slot.slot_marker, self.node, slot.payload,
                                 modulation=slot.modulation, destination=None, type=SimMessageType.SLOT_SCHEDULE,
                                 content=slot_schedule, power_level=slot.power_level)
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, master=self.node,
                              message=message)
        else:
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, master=self.node.current_base,
                              message=None)

    def process_slot_schedule_slot_callback(self, message: SimMessage):
        if self.node.role is not sim_node.SimNodeRole.BASE and \
                message is not None and message.type is SimMessageType.SLOT_SCHEDULE:
            self.lwb_schedule_manager.register_slot_schedule(message.content)

        self.process_next_slot()

    def process_data_slot(self, slot: 'lwb_slot.LWBSlot'):
        if slot.master is self.node:
            message = self.node.datastream_manager.get_data(slot.payload, slot.acked)

            message.timestamp = slot.slot_marker
            message.modulation = slot.modulation
            message.id = slot.id

            SimLWBSlotManager(self.node, slot, self.process_data_slot_callback, master=slot.master,
                              message=message)

        else:
            if slot.acked:
                self.ack_operation = AckOperation.DATA

            SimLWBSlotManager(self.node, slot, self.process_data_slot_callback, master=slot.master,
                              message=None)

    def process_data_slot_callback(self, message: SimMessage):
        if message is not None and message.type is SimMessageType.DATA:
            self.ack_id = message.id
        else:
            self.ack_operation = None

        self.process_next_slot()

    def process_contention_slot(self, slot):
        if not self.node.role is not sim_node.SimNodeRole.BASE and (slot.master is None or slot.master is self.node):

            ### TODO

            if self.round.type is LWBRoundType.CONTENTION
                message = self.lwb_manager.stream_manager.get_

            if message is not None:
                message.timestamp = slot.slot_marker
                message.modulation = slot.modulation

            SimLWBSlotManager(self.node, slot, self.process_contention_slot_callback, master=self.node,
                              message=message)
        else:
            if slot.acked:
                self.ack_operation = AckOperation.CONTENTION

            SimLWBSlotManager(self.node, slot, self.process_contention_slot_callback, master=slot.master,
                              message=None)

    def process_contention_slot_callback(self, message: SimMessage):
        if message is not None and message.type in [SimMessageType.NOTIFICATION, SimMessageType.ROUND_REQUEST,
                                                    SimMessageType.STREAM_REQUEST]:
            self.ack_id = message.id
            if message.type is SimMessageType.STREAM_REQUEST:
                if not self.node.lwb_manager.stream_manager.register_request(message.content):
                    self.ack_operation = AckOperation.CONTENTION
        else:
            self.ack_operation = None

        self.process_next_slot()

    def process_round_contention_slot(self, slot):

    def process_ack_slot(self, slot):
        if self.ack_operation:
            message = SimMessage(slot['modulation'], slot['offset'], self.node, slot['payload'],
                                 modulation=slot['modulation'], destination=self.message_to_be_acked.source, type='ack',
                                 content={'id': self.message_to_be_acked.id}, power_level=slot.power_level)
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, master=self.node,
                              message=message)

        self.ack_operation = None

    def process_ack_slot_callback(self, message: SimMessage):
        if message.type is 'ack':
            self.node.datastream_manager.ack_data(message.content['id'])

    def process_round_schedule_slot(self, slot):
        if self.node.role is 'base':
            round_schedule = self.lwb_schedule_manager.get_slot_schedule()
            message = SimMessage(slot['modulation'], slot['offset'], self.node, slot['payload'],
                                 modulation=slot['modulation'], destination=None, type='round_schedule',
                                 content=round_schedule, power_level=slot.power_level)
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, master=self.node,
                              message=message)
        else:
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, master=self.node.current_base,
                              message=None)

    def process_round_schedule_slot_callback(self, message: SimMessage):
        if self.node.role is not 'base' and message is not None and message.type is 'round_schedule':
            self.lwb_schedule_manager.register_round_schedule(message.content)

    def slot_valid(self):
        return self.round.slots[self.current_slot_index] is not None
