from enum import Enum

import numpy as np

import flora_tools.gloria as gloria
import flora_tools.lwb_round as lwb_round
import flora_tools.sim.sim_node as sim_node
from flora_tools.radio_configuration import RadioConfiguration

GLORIA_DEFAULT_POWER_LEVELS = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
GLORIA_RETRANSMISSIONS_COUNTS = [1, 1, 1, 1, 2, 2, 2, 2, 2, 2]
GLORIA_HOP_COUNTS = [1, 1, 1, 1, 2, 2, 2, 3, 3, 3]

RADIO_MODULATIONS = [3, 5, 7, 9]  # SF9, SF7, SF5, FSK 200 Kb/s
RADIO_POWERS = [10, 22]  # dBm

TIMER_FREQUENCY = 8E6  # 0.125 us
TIME_DEPTH = 6  # 6 Bytes, ~1.116 years

LWB_SCHEDULE_GRANULARITY = 1 / TIMER_FREQUENCY * np.exp2(11)  # 256 us
LWB_SYNC_PERIOD = 1 / TIMER_FREQUENCY * np.exp2(31)  # 268.435456 s

# GLORIA_HEADER: uint8_t[8]
#   - TYPE: uint8_t
#   - HOP_COUNT: uint8_t:4
#   - POWER_LEVEL: uint8_t:4
#   - FIELDS: uint8_t[6]
#       - TYPE in [SYNC, SLOT_SCHEDULE, ROUND_SCHEDULE]:
#           - TIMESTAMP: uint8_t[6]
#       - TYPE in [CONTENTION, DATA, ACK]
#           - SOURCE: uint16_t
#           - DESTINATION: uint16_t
#           - STREAM_ID: uint16_t
GLORIA_HEADER_LENGTH = 8

# CONTENTION_HEADER: uint8_t[14]
#   - GLORIA_HEADER: uint8_t[8]
#   - PAYLOAD_SIZE: uint16_t
#   - PERIOD: uint8_t[3]
#   - PRIORITIES: uint8_t
#       - PRIORITY: uint8_t: 4
#       - SUB_PRIORITY: uint8_t: 4
LWB_CONTENTION_HEADER_LENGTH = GLORIA_HEADER_LENGTH + 6

LWB_DATA_HEADER_LENGTH = GLORIA_HEADER_LENGTH
LWB_MAX_DATA_PAYLOAD = 255 - LWB_DATA_HEADER_LENGTH

# SLOT_SCHEDULE_HEADER: uint8_t[8]
#   - TYPE: uint8_t
#   - COUNT: uint8_t
#   - TIMESTAMP: uint8_t[6]
LWB_SLOT_SCHEDULE_HEADER_LENGTH = GLORIA_HEADER_LENGTH + 8

# SLOT_SCHEDULE_ITEM: uint8_t[6]
#   - SLOT_SIZE: uint8_t
#   - MASTER: uint16_t
#   - STREAM_ID: uint16_t
LWB_SLOT_SCHEDULE_ITEM_LENGTH = 6

# ROUND_SCHEDULE_ITEM: uint8_t[4]
#   - TYPE: uint8_t
#   - SLOT_SIZE: uint8_t
#   - MASTER: uint16_t
#   - STREAM_ID: uint16_t
LWB_ROUND_SCHEDULE_ITEM = 6

LWB_ROUND_SCHEDULE_ITEM_COUNT = len(RADIO_MODULATIONS) * 1
LWB_ROUND_SCHEDULE_LENGTH = GLORIA_HEADER_LENGTH + LWB_ROUND_SCHEDULE_ITEM_COUNT * LWB_ROUND_SCHEDULE_ITEM


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
        self.gloria_modulation = RADIO_MODULATIONS[self.modulation]
        self.payload = payload
        self.type = type
        self.is_ack = is_ack
        self.master = master
        self.index = index
        self.stream = stream

        if power_level is None:
            self.power_level = GLORIA_DEFAULT_POWER_LEVELS[self.gloria_modulation]
        else:
            self.power_level = power_level

        self.flood: gloria.GloriaFlood = None

        self.radio_configuration = RadioConfiguration(self.gloria_modulation)

        self.generate()

    def generate(self):
        self.flood = gloria.GloriaFlood(self, self.gloria_modulation, self.payload,
                                        GLORIA_RETRANSMISSIONS_COUNTS[self.gloria_modulation],
                                        GLORIA_HOP_COUNTS[self.gloria_modulation],
                                        is_ack=self.is_ack, is_master=(self.master is not None),
                                        power=RADIO_POWERS[self.power_level])
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
    def create_data_slot(round, slot_offset, modulation, payload, master: 'sim_node.SimNode', index=None,
                         power_level=None, stream=None):
        slot = LWBSlot(round, slot_offset, modulation, payload, LWBSlotType.DATA, master=master, is_ack=True,
                       index=index, power_level=power_level, stream=stream)
        return slot

    @staticmethod
    def create_sync_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, GLORIA_HEADER_LENGTH, LWBSlotType.SYNC, master=master,
                       is_ack=False,
                       index=index)
        return slot

    @staticmethod
    def create_round_schedule_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, LWB_ROUND_SCHEDULE_LENGTH, LWBSlotType.ROUND_SCHEDULE, master=master,
                       is_ack=False,
                       index=index)
        return slot

    @staticmethod
    def create_slot_schedule_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        payload = LWB_SLOT_SCHEDULE_HEADER_LENGTH + lwb_round.LWB_MAX_SLOT_COUNT[
            RADIO_MODULATIONS[modulation]] * LWB_SLOT_SCHEDULE_ITEM_LENGTH
        slot = LWBSlot(round, slot_offset, modulation, payload, LWBSlotType.SLOT_SCHEDULE, master=master, is_ack=False,
                       index=index)
        return slot

    @staticmethod
    def create_round_contention_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, LWB_CONTENTION_HEADER_LENGTH, LWBSlotType.CONTENTION, master=master,
                       is_ack=True,
                       index=index)
        return slot

    @staticmethod
    def create_contention_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None):
        slot = LWBSlot(round, slot_offset, modulation, LWB_CONTENTION_HEADER_LENGTH, LWBSlotType.CONTENTION, master=master,
                       is_ack=True,
                       index=index)
        return slot

    @staticmethod
    def create_ack_slot(round, slot_offset, modulation, master: 'sim_node.SimNode', index=None, power_level=None):
        slot = LWBSlot(round, slot_offset, modulation, GLORIA_HEADER_LENGTH, LWBSlotType.ACK, master=master,
                       is_ack=True,
                       index=index, power_level=power_level)
        return slot

    @staticmethod
    def create_empty_slot(modulation, payload=GLORIA_HEADER_LENGTH, acked=True):
        empty_round = lwb_round.LWBRound(0, modulation, lwb_round.LWBRoundType.EMPTY)
        slot = LWBSlot(empty_round, 0, modulation, payload, LWBSlotType.EMPTY, is_ack=acked)
        return slot
