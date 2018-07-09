from enum import Enum

import flora_tools.sim.sim_node as sim_node

from flora_tools.gloria_flood import GloriaFlood
from flora_tools.radio_configuration import RadioConfiguration
import flora_tools.lwb_round as lwb_round

MODULATIONS = [3, 5, 7, 9]
BANDS = [48, 50]
POWERS = [22, 10]

gloria_header_length = 4
sync_header_length = gloria_header_length + 4
contention_length = gloria_header_length + 3

rounds_schedule_buffer_items = len(MODULATIONS) * 2
round_schedule_length = gloria_header_length + rounds_schedule_buffer_items * 4

slot_schedule_item_length = 3

RETRANSMISSIONS_COUNTS = [1, 1, 1, 1, 2, 2, 2, 2, 2, 2]
HOP_COUNTS = [1, 1, 1, 1, 2, 2, 2, 3, 3, 3]


class LWBSlotType(Enum):
    SYNC = 1
    SLOT_SCHEDULE = 2
    ROUND_SCHEDULE = 3
    CONTENTION = 4
    ROUND_CONTENTION = 5
    DATA = 6
    ACK = 7


class LWBSlot:
    def __init__(self, round: 'lwb_round.LWBRound', slot_offset: float, modulation: int, payload: int, type: LWBSlotType, acked=True, master:'sim_node.SimNode'=None):
        self.round = round
        self.slot_offset = slot_offset
        self.modulation = modulation
        self.gloria_modulation = MODULATIONS[self.modulation]
        self.payload = payload
        self.type = type
        self.acked = acked
        self.master = master

        self.flood: 'GloriaFlood' = None

        self.radio_configuration = RadioConfiguration(self.gloria_modulation)

        self.generate()

    def generate(self):
        self.flood = GloriaFlood(self, self.gloria_modulation, self.payload,
                                 RETRANSMISSIONS_COUNTS[self.gloria_modulation], HOP_COUNTS[self.gloria_modulation],
                                 acked=self.acked, is_master=(self.master is not None))
        self.flood.generate()

    @property
    def slot_marker(self):
        return self.round.round_marker + self.slot_offset

    @property
    def slot_end_marker(self):
        return self.round.round_marker + self.slot_offset + self.total_time

    @property
    def color(self):
        if self.type is LWBSlotType.SYNC:
            return 'fuchsia'
        elif self.type is LWBSlotType.ROUND_SCHEDULE:
            return 'rebeccapurple'
        elif self.type is LWBSlotType.ROUND_CONTENTION:
            return 'lightcoral'
        elif self.type is LWBSlotType.CONTENTION:
            return 'lightcoral'
        elif self.type is LWBSlotType.SLOT_SCHEDULE:
            return 'darkorchid'
        elif self.type is LWBSlotType.DATA:
            return 'deepskyblue'
        elif self.type is LWBSlotType.ACK:
            return 'mediumaquamarine'

    @property
    def total_time(self):
        return self.flood.total_time

    @staticmethod
    def create_data_slot(round, slot_offset, modulation, payload, master: 'sim_node.SimNode'):
        slot = LWBSlot(round, slot_offset, modulation, payload, LWBSlotType.DATA, acked=True)
        return slot

    @staticmethod
    def create_sync_slot(round, slot_offset, modulation, master: 'sim_node.SimNode'):
        slot = LWBSlot(round, slot_offset, modulation, sync_header_length, LWBSlotType.SYNC, acked=False)
        return slot

    @staticmethod
    def create_round_schedule_slot(round, slot_offset, modulation, master: 'sim_node.SimNode'):
        slot = LWBSlot(round, slot_offset, modulation, round_schedule_length, LWBSlotType.ROUND_SCHEDULE, acked=False)
        return slot

    @staticmethod
    def create_slot_schedule_slot(round, slot_offset, modulation, master: 'sim_node.SimNode'):
        payload = sync_header_length + lwb_round.SLOT_COUNTS[MODULATIONS[modulation]] * slot_schedule_item_length
        slot = LWBSlot(round, slot_offset, modulation, payload, LWBSlotType.SLOT_SCHEDULE, acked=False)
        return slot

    @staticmethod
    def create_round_contention_slot(round, slot_offset, modulation, master: 'sim_node.SimNode'):
        slot = LWBSlot(round, slot_offset, modulation, contention_length, LWBSlotType.ROUND_CONTENTION, acked=True)
        return slot

    @staticmethod
    def create_contention_slot(round, slot_offset, modulation, master: 'sim_node.SimNode'):
        slot = LWBSlot(round, slot_offset, modulation, contention_length, LWBSlotType.CONTENTION, acked=True)
        return slot

    @staticmethod
    def create_ack_slot(round, slot_offset, modulation, master: 'sim_node.SimNode'):
        slot = LWBSlot(round, slot_offset, modulation, gloria_header_length, LWBSlotType.ACK, acked=True)
        return slot
