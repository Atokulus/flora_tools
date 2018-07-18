from enum import Enum

import numpy as np

import flora_tools.gloria as gloria
import flora_tools.lwb_round as lwb_round
import flora_tools.sim.sim_node as sim_node
from flora_tools.radio_configuration import RadioConfiguration

MODULATIONS = [3, 5, 7, 9]  # SF9, SF7, SF5, FSK 200 Kb/s
POWERS = [10, 22]  # dBm

TIMER_FREQUENCY = 8E6  # 0.125 us
TIME_DEPTH = 6  # 6 Bytes, ~1.116 years
SCHEDULE_GRANULARITY = 1 / TIMER_FREQUENCY * np.exp2(11)  # 256 us
SYNC_PERIOD = 1 / TIMER_FREQUENCY * np.exp2(31)  # 268.435456 s

# GLORIA_HEADER: uint8_t[8]
#   - TYPE: uint8_t
#   - POWER_LEVEL: uint8_t
#   - FIELDS: uint8_t[6]
#       - TYPE in [SYNC, SLOT_SCHEDULE, ROUND_SCHEDULE]:
#           - TIMESTAMP: uint8_t[6]
#       - TYPE in [CONTENTION, DATA, ACK]
#           - SOURCE: uint16_t
#           - DESTINATION: uint16_t
#           - STREAM_ID: uint16_t
gloria_header_length = 8

# CONTENTION_HEADER: uint8_t[14]
#   - GLORIA_HEADER: uint8_t[8]
#   - PAYLOAD_SIZE: uint16_t
#   - PERIOD: uint8_t[3]
#   - PRIORITIES: uint8_t
#       - PRIORITY: uint8_t: 4
#       - SUB_PRIORITY: uint8_t: 4
contention_header_length = gloria_header_length + 6

data_header_length = gloria_header_length
max_data_payload = 255 - data_header_length

# SLOT_SCHEDULE_HEADER: uint8_t[8]
#   - TYPE: uint8_t
#   - COUNT: uint8_t
#   - TIMESTAMP: uint8_t[6]
slot_schedule_header_length = gloria_header_length + 8

# SLOT_SCHEDULE_ITEM: uint8_t[6]
#   - SLOT_SIZE: uint8_t
#   - MASTER: uint16_t
#   - STREAM_ID: uint16_t
slot_schedule_item_length = 6

# ROUND_SCHEDULE_ITEM: uint8_t[4]
#   - TYPE: uint8_t
#   - SLOT_SIZE: uint8_t
#   - MASTER: uint16_t
#   - STREAM_ID: uint16_t
round_schedule_item = 6

round_schedule_item_count = len(MODULATIONS) * 3  # 2 * PERIODIC (SYNC + LP_NOTIFICATION) +  1 * ABSOLUTE Schedule
round_schedule_length = gloria_header_length + round_schedule_item_count * round_schedule_item

DEFAULT_POWER_LEVELS = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
RETRANSMISSIONS_COUNTS = [1, 1, 1, 1, 2, 2, 2, 2, 2, 2]
HOP_COUNTS = [1, 1, 1, 1, 2, 2, 2, 3, 3, 3]


class LWBSlotType(Enum):
    SYNC = 1
    SLOT_SCHEDULE = 2
    ROUND_SCHEDULE = 3
    CONTENTION = 4
    DATA = 5
    ACK = 6
    EMPTY = 7

    def __str__(self):
        return '{0}'.format(self.name)


class LWBSlot:
    def __init__(self, round: 'lwb_round.LWBRound', slot_offset: float, modulation: int, payload: int,
                 type: LWBSlotType, is_ack=True, master: 'sim_node.SimNode' = None, index: int = None,
                 power_level: int = None, stream=None):
        self.round = round
        self.slot_offset = slot_offset
        self.modulation = modulation
        self.gloria_modulation = MODULATIONS[self.modulation]
        self.payload = payload
        self.type = type
        self.is_ack = is_ack
        self.master = master
        self.index = index
        self.stream = stream

        if power_level is None:
            self.power_level = DEFAULT_POWER_LEVELS[self.gloria_modulation]
        else:
            self.power_level = power_level

        self.flood: gloria.GloriaFlood = None

        self.radio_configuration = RadioConfiguration(self.gloria_modulation)

        self.generate()

    def generate(self):
        self.flood = gloria.GloriaFlood(self, self.gloria_modulation, self.payload,
                                        RETRANSMISSIONS_COUNTS[self.gloria_modulation],
                                        HOP_COUNTS[self.gloria_modulation],
                                        is_ack=self.is_ack, is_master=(self.master is not None))
        self.flood.generate()

    @property
    def id(self):
        return self.round.first_id + self.index

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
        elif self.type is LWBSlotType.CONTENTION:
            return 'lightcoral'
        elif self.type is LWBSlotType.SLOT_SCHEDULE:
            return 'darkorchid'
        elif self.type is LWBSlotType.DATA:
            return 'deepskyblue'
        elif self.type is LWBSlotType.ACK:
            return 'mediumaquamarine'
        else:
            return 'r'

    @property
    def total_time(self):
        return self.flood.total_time

    @staticmethod
    def create_data_slot(round, slot_offset, modulation, payload, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, payload, LWBSlotType.DATA, master=master, is_ack=True,
                       index=index)
        return slot

    @staticmethod
    def create_sync_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, gloria_header_length, LWBSlotType.SYNC, master=master,
                       is_ack=False,
                       index=index)
        return slot

    @staticmethod
    def create_round_schedule_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, round_schedule_length, LWBSlotType.ROUND_SCHEDULE, master=master,
                       is_ack=False,
                       index=index)
        return slot

    @staticmethod
    def create_slot_schedule_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        payload = slot_schedule_header_length + lwb_round.SLOT_COUNTS[MODULATIONS[modulation]] * slot_schedule_item_length
        slot = LWBSlot(round, slot_offset, modulation, payload, LWBSlotType.SLOT_SCHEDULE, master=master, is_ack=False,
                       index=index)
        return slot

    @staticmethod
    def create_round_contention_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, contention_header_length, LWBSlotType.CONTENTION, master=master,
                       is_ack=True,
                       index=index)
        return slot

    @staticmethod
    def create_contention_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, contention_header_length, LWBSlotType.CONTENTION, master=master,
                       is_ack=True,
                       index=index)
        return slot

    @staticmethod
    def create_ack_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, gloria_header_length, LWBSlotType.ACK, master=master, is_ack=True,
                       index=index)
        return slot

    @staticmethod
    def create_empty_slot(modulation, payload=gloria_header_length, acked=True):
        empty_round = lwb_round.LWBRound(0, modulation, lwb_round.LWBRoundType.EMPTY)
        slot = LWBSlot(empty_round, 0, modulation, payload, LWBSlotType.EMPTY, is_ack=acked)
        return slot
