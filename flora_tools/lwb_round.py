import typing
from enum import Enum

import flora_tools.lwb_slot as lwb_slot
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.sim.sim_node import SimNode

SLOT_COUNTS = [2, 2, 4, 4, 6, 6, 16, 16, 32, 32]
max_contention_layout = [2, 2, 4, 8]
initial_contention_layout = [1, 1, 1, 8]
min_contention_layout = [0, 0, 0, 0]


class LWBRoundType(Enum):
    SYNC = 1
    STREAM_CONTENTION = 2
    NOTIFICATION = 3
    DATA = 4
    LP_NOTIFICATION = 5
    EMPTY = 6

    def __str__(self):
        return '{0}'.format(self.name)


class LWBSlotItemType(Enum):
    SYNC = 1
    SLOT_SCHEDULE = 2
    ROUND_SCHEDULE = 3
    CONTENTION = 4
    ROUND_CONTENTION = 5
    DATA = 6


class LWBSlotItem:
    def __init__(self, type: LWBSlotItemType, master: 'SimNode' = None, target: 'SimNode' = None, data_payload=None):
        self.type = type
        self.master = master
        self.target = target
        self.data_payload = data_payload


class LWBDataSlotItem:
    def __init__(self, master: 'SimNode' = None, target: 'SimNode' = None, data_payload=None):
        self.master = master
        self.target = target
        self.data_payload = data_payload


class LWBRound:
    def __init__(self, round_marker, modulation, type: LWBRoundType, master: 'SimNode' = None, layout=None,
                 low_power=False, first_id: int = None):
        self.round_marker = round_marker
        self.modulation = modulation
        self.gloria_modulation = lwb_slot.MODULATIONS[self.modulation]
        self.radio_configuration = RadioConfiguration(self.gloria_modulation)
        self.type = type
        self.master = master
        self.layout = layout
        self.low_power = low_power
        self.first_id = first_id

        self.slots: typing.List[lwb_slot.LWBSlot] = []

        self.generate()

    @property
    def color(self):
        return self.radio_configuration.color

    @property
    def total_time(self):
        return self.round_end_marker - self.round_marker

    @property
    def round_end_marker(self):
        return self.slots[-1].slot_end_marker

    def generate(self):
        slot_offset = 0

        index: int = 0
        item: LWBSlotItem
        for item in self.layout:
            if item.type is LWBSlotItemType.SYNC:
                slot = lwb_slot.LWBSlot.create_sync_slot(self, slot_offset, self.modulation, master=item.master,
                                                         index=index)
            elif item.type is LWBSlotItemType.ROUND_SCHEDULE:
                slot = lwb_slot.LWBSlot.create_round_schedule_slot(self, slot_offset, self.modulation,
                                                                   master=item.master,
                                                                   index=index)
            elif item.type is LWBSlotItemType.SLOT_SCHEDULE:
                slot = lwb_slot.LWBSlot.create_slot_schedule_slot(self, slot_offset, self.modulation,
                                                                  master=item.master,
                                                                  index=index)
            elif item.type is LWBSlotItemType.CONTENTION:
                slot = lwb_slot.LWBSlot.create_contention_slot(self, slot_offset, self.modulation, master=item.master,
                                                               index=index)
                self.slots.append(slot)
                index += 1
                slot_offset += slot.total_time
                slot = lwb_slot.LWBSlot.create_ack_slot(self, slot_offset, self.modulation, master=item.target,
                                                        index=index)
            elif item.type is LWBSlotItemType.ROUND_CONTENTION:
                slot = lwb_slot.LWBSlot.create_round_contention_slot(self, slot_offset, self.modulation,
                                                                     master=item.master,
                                                                     index=index)
            elif item.type is LWBSlotItemType.DATA:
                slot = lwb_slot.LWBSlot.create_data_slot(self, slot_offset, self.modulation, payload=item.data_payload,
                                                         master=item.master, index=index)
                self.slots.append(slot)
                index += 1
                slot_offset += slot.total_time
                slot = lwb_slot.LWBSlot.create_ack_slot(self, slot_offset, self.modulation, master=item.target,
                                                        index=index)

            self.slots.append(slot)
            slot_offset += slot.total_time
            index += 1

    @staticmethod
    def create_sync_round(round_marker: float, modulation: int, master: 'SimNode' = None):
        layout = []

        layout.append(LWBSlotItem(LWBSlotItemType.SYNC))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE))

        return LWBRound(round_marker, modulation, type=LWBRoundType.SYNC, layout=layout, master=master)

    @staticmethod
    def create_data_round(round_marker: float, modulation: int, data_slots, master: 'SimNode' = None):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE, master=master))
        item: LWBDataSlotItem
        for item in data_slots:
            layout.append(LWBSlotItem(LWBSlotItemType.DATA, master=item.master, target=item.target,
                                      data_payload=item.data_payload))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.DATA, layout=layout, master=master)

    @staticmethod
    def create_stream_request_round(round_marker: float, modulation: int, contention_count: int,
                                    master: 'SimNode' = None):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE))
        for i in range(contention_count):
            layout.append(LWBSlotItem(LWBSlotItemType.CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.STREAM_CONTENTION, layout=layout, master=master)

    @staticmethod
    def create_notification_round(round_marker: float, modulation: int, data_slots,
                                  master: 'SimNode' = None):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE, master=master))
        item: LWBDataSlotItem
        for item in data_slots:
            layout.append(LWBSlotItem(LWBSlotItemType.DATA, master=item.master, target=item.target,
                                      data_payload=item.data_payload))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.NOTIFICATION, layout=layout, master=master)

    @staticmethod
    def create_lp_notification_round(round_marker: float, modulation: int, notification_count: int,
                                     master: 'SimNode' = None):
        layout = []
        for i in range(notification_count):
            layout.append(LWBSlotItem(LWBSlotItemType.CONTENTION, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.LP_NOTIFICATION, layout=layout, master=master,
                        low_power=True)
