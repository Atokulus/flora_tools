import numpy as np

from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_lwb_slot_manager import SimLWBSlotManager
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.lwb_schedule_manager import LWBScheduleManager
from flora_tools.sim.sim_event_manager import SimEventType


BACKOFF_TIME = 1/8E6 * np.exp2(29)


class SimLWBManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.rounds = []
        self.next_slot = None
        self.ack_operation = None
        self.ack_id = None

        if self.node.role is 'base':
            self.base = self.node
        else:
            self.base = None

        self.lwb_schedule_manager = LWBScheduleManager(self.node)

    def run(self):
        self.next_slot = self.lwb_schedule_manager.get_next_slot()

        if self.next_slot is not None:
            self.node.em.register_event(self.next_slot['offset'], self.node, SimEventType.UPDATE, self.process_slot)
            return True
        else:
            return False

    def process_slot(self):
        if self.next_slot['type'] is 'sync':
            self.process_sync_slot()

    def process_sync_slot(self, slot):
        if self.node.role is 'base':
            message = SimMessage(slot['modulation'], slot['offset'], self.node, slot['payload'],
                                 modulation=slot['modulation'], destination=None, type='sync',
                                 power_level=0)
            SimLWBSlotManager(self.node, slot, self.process_sync_slot_callback, tx_node=self.node,
                              message=message)
        else:
            SimLWBSlotManager(self.node, slot, self.process_sync_slot_callback, tx_node=self.node.current_base,
                              message=None)

    def process_sync_slot_callback(self, message: SimMessage):
        if self.node.role is not 'base':
            self.run()
        else:
            self.lwb_schedule_manager.add_sync_slots()
            self.run()

    def process_slot_schedule_slot(self, slot):
        if self.node.role is 'base':
            slot_schedule = self.lwb_schedule_manager.get_slot_schedule()
            message = SimMessage(slot['modulation'], slot['offset'], self.node, slot['payload'], modulation=slot['modulation'], destination=None, type='slot_schedule', content=slot_schedule, power_level=0)
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, tx_node=self.node, message=message)
        else:
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, tx_node=self.node.current_base, message=None)

    def process_slot_schedule_slot_callback(self, message: SimMessage):
        if not (self.node.role is 'base') and message is not None and message.type is 'slot_schedule':
            self.lwb_schedule_manager.register_slot_schedule(message.content)

        self.run()

    def process_data_slot(self, slot, tx_node: 'sim_node.SimNode'):
        if tx_node is self.node:
            message = self.node.datastream_manager.get_data(slot['payload'], slot['acked'])

            message.timestamp = slot['offset']
            message.modulation = slot['modulation']

            SimLWBSlotManager(self.node, slot, self.process_data_slot_callback, tx_node=self.node,
                              message=message)

        else:
            if slot['acked']:
                self.ack_operation = 'data'

            SimLWBSlotManager(self.node, slot, self.process_data_slot_callback, tx_node=self.node,
                              message=None)

    def process_data_slot_callback(self, message: SimMessage):
        if message is not None and message.type is 'data':
            self.ack_id = message.id
        else:
            self.ack_operation = None

        self.run()

    def process_contention_slot(self, slot):
        if not self.node.role is 'base':
            message = self.node.datastream_manager.get_contention()

            if message is not None:
                message.timestamp = slot['offset']
                message.modulation = slot['modulation']

            SimLWBSlotManager(self.node, slot, self.process_contention_slot_callback, tx_node=self.node,
                              message=message)

        else:
            if slot['acked']:
                self.ack_operation = 'data'

            SimLWBSlotManager(self.node, slot, self.process_contention_slot_callback, tx_node=self.node,
                              message=None)

    def process_contention_slot_callback(self, message: SimMessage):
        if message is not None and message.type is 'contention':
            self.message_to_be_acked = message
            if message.content['type'] is 'datastream':
                if not self.node.datastream_manager.add_datastream(message.content):
                    self.ack_operation = None
        else:
            self.ack_operation = None

        self.run()

    def process_ack_slot(self, slot):
        if self.ack_operation:
            message = SimMessage(slot['modulation'], slot['offset'], self.node, slot['payload'],
                                 modulation=slot['modulation'], destination=self.message_to_be_acked.source, type='ack',
                                 content={'id': self.message_to_be_acked.id}, power_level=0)
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, tx_node=self.node,
                              message=message)

        self.ack_operation = None

    def process_ack_slot_callback(self, message: SimMessage):
        if message.type is 'ack':
            self.node.datastream_manager.ack_data(message.content['id'])

    def process_round_schedule_slot(self, slot):
        if self.node.role is 'base':
            round_schedule = self.lwb_schedule_manager.get_slot_schedule()
            message = SimMessage(slot['modulation'], slot['offset'], self.node, slot['payload'], modulation=slot['modulation'], destination=None, type='round_schedule', content=round_schedule, power_level=0)
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, tx_node=self.node, message=message)
        else:
            SimLWBSlotManager(self.node, slot, self.process_slot_schedule_slot_callback, tx_node=self.node.current_base, message=None)

    def process_round_schedule_slot_callback(self, message: SimMessage):
        if self.node.role is not 'base' and message is not None and message.type is 'round_schedule':
            self.lwb_schedule_manager.register_round_schedule(message.content)
