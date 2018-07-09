from enum import Enum

from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.sim.sim_node import SimNode
from flora_tools.lwb_slot import LWBSlotType, LWBSlot, MODULATIONS

from flora_tools.gloria_flood import GloriaFlood

SLOT_COUNTS = [2, 2, 4, 4, 6, 6, 16, 16, 32, 32]
max_contention_layout = [2, 4, 4, 8, 8]
initial_contention_layout = [1, 1, 1, 1, 8]
min_contention_layout = [0, 0, 0, 0, 0]


class LWBRoundType(Enum):
    SYNC = 1
    CONTENTION = 2
    NOTIFICATION = 3
    DATA = 4
    LP_NOTIFICATION = 5


class LWBSlotItemType(Enum):
    SYNC = 1
    SLOT_SCHEDULE = 2
    ROUND_SCHEDULE = 3
    CONTENTION = 4
    ROUND_CONTENTION = 5
    DATA = 6


class LWBSlotItem:
    def __init__(self, type: LWBSlotItemType, master: 'SimNode'=None, target: 'SimNode'=None, data_payload=None):
        self.type = type
        self.master = master
        self.target = target
        self.data_payload = data_payload


class LWBDataSlotItem:
    def __init__(self, master: 'SimNode'=None, target: 'SimNode'=None, data_payload=None):
        self.master = master
        self.target = target
        self.data_payload = data_payload


class LWBRound:
    def __init__(self, round_marker, modulation, type: LWBRoundType, master:'SimNode'=None, layout=None):
        self.round_marker = round_marker
        self.modulation = modulation
        self.gloria_modulation = MODULATIONS[self.modulation]
        self.radio_configuration = RadioConfiguration(self.gloria_modulation)
        self.type = type
        self.master = master
        self.layout = layout

        self.slots = []

        self.generate()

    @property
    def color(self):
        return self.radio_configuration.color

    def generate(self):
        slot_offset = 0

        item : LWBSlotItem
        for item in self.layout:
            if item.type is LWBSlotItem.SYNC:
                slot = LWBSlot.create_sync_slot(self, slot_offset, self.modulation, master=item.master)
            elif item.type is LWBSlotItem.ROUND_SCHEDULE:
                slot = LWBSlot.create_round_schedule_slot(self, slot_offset, self.modulation, master=item.master)
            elif item.type is LWBSlotItem.SLOT_SCHEDULE:
                slot = LWBSlot.create_slot_schedule_slot(self, slot_offset, self.modulation, master=item.master)
            elif item.type is LWBSlotItem.CONTENTION:
                slot = LWBSlot.create_contention_slot(self, slot_offset, self.modulation, master=item.master)
                self.slots.append(slot)
                slot_offset += slot.total_time
                slot = LWBSlot.create_ack_slot(self, slot_offset, self.modulation, master=item.target)
            elif item.type is LWBSlotItem.ROUND_CONTENTION:
                slot = LWBSlot.create_round_contention_slot(self, slot_offset, self.modulation, master=item.master)
                self.slots.append(slot)
                slot_offset += slot.total_time
                slot = LWBSlot.create_ack_slot(self, slot_offset, self.modulation, master=item.target)
            elif item.type is LWBSlotItem.DATA:
                slot = LWBSlot.create_data_slot(self, slot_offset, self.modulation, payload=item.data_payload, master=item.master)
                self.slots.append(slot)
                slot_offset += slot.total_time
                slot = LWBSlot.create_ack_slot(self, slot_offset, self.modulation, master=item.target)

            self.slots.append(slot)
            slot_offset += slot.total_time

    @staticmethod
    def create_sync_round(round_marker: float, modulation: int):
        layout = []

        layout.append(LWBSlotItem(LWBSlotItemType.SYNC))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE))

        return LWBRound(round_marker, modulation, type=LWBRoundType.SYNC, layout=layout)

    @staticmethod
    def create_data_round(round_marker: float, modulation: int, data_slots):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE))
        item: LWBDataSlotItem
        for item in data_slots:
            layout.append(LWBSlotItem(LWBSlotItemType.DATA, master=item.master, target=item.target, data_payload=item.data_payload))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE))

        return LWBRound(round_marker, modulation, type=LWBRoundType.DATA, layout=layout)

    @staticmethod
    def create_contention_round(round_marker: float, modulation: int, contention_count: int):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE))
        for i in range(contention_count):
            layout.append(LWBSlotItem(LWBSlotItemType.CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE))

        return LWBRound(round_marker, modulation, type=LWBRoundType.CONTENTION, layout=layout)

    @staticmethod
    def create_notification_round(round_marker: float, modulation: int, notification_count: int):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE))
        for i in range(notification_count):
            layout.append(LWBSlotItem(LWBSlotItemType.CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE))

        return LWBRound(round_marker, modulation, type=LWBRoundType.NOTIFICATION, layout=layout)

    @staticmethod
    def create_lp_notification_round(round_marker: float, modulation: int, notification_count: int):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE))
        for i in range(notification_count):
            layout.append(LWBSlotItem(LWBSlotItemType.CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE))

        return LWBRound(round_marker, modulation, type=LWBRoundType.LP_NOTIFICATION, layout=layout)



