import typing
from enum import Enum
from typing import Union

import numpy as np

from pandas._libs.tslibs import np_datetime

import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node
import flora_tools.sim.lwb_stream as stream
from flora_tools.radio_configuration import RadioConfiguration

LWB_MAX_SLOT_COUNT = [2, 2, 4, 4, 6, 6, 16, 16, 32, 32]
LWB_MAX_STREAM_REQUEST_SLOT_COUNT = [2, 2, 4, 8]
LWB_INITIAL_STREAM_REQUEST_SLOT_COUNT = [1, 1, 1, 8]
LWB_MIN_STREAM_REQUEST_SLOT_COUNT = [0, 0, 0, 0]


class LWBRoundType(Enum):
    SYNC = 1
    STREAM_REQUEST = 2
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
    def __init__(self, type: LWBSlotItemType, master: 'sim_node.SimNode' = None, target: 'sim_node.SimNode' = None,
                 payload=None, stream: 'Union[stream.DataStream, stream.NotificationStream]' = None,
                 power_level: int = None, ack_power_level: int = None):
        self.type = type
        self.master = master
        self.target = target
        self.payload = payload
        self.stream = stream
        self.power_level = power_level
        self.ack_power_level = ack_power_level


class LWBDataSlotItem:
    def __init__(self, master: 'sim_node.SimNode' = None, target: 'sim_node.SimNode' = None, data_payload=None,
                 stream: 'Union[stream.DataStream, stream.NotificationStream]' = None, power_level: int = None,
                 ack_power_level: int = None):
        self.master = master
        self.target = target
        self.data_payload = data_payload
        self.stream = stream
        self.power_level = power_level
        self.ack_power_level = ack_power_level


class LWBRound:
    def __init__(self, round_marker, modulation, type: LWBRoundType,
                 master: 'sim_node.SimNode' = None, layout: typing.List[LWBSlotItem] = []):
        self.round_marker = round_marker
        self.modulation = modulation
        self.gloria_modulation = lwb_slot.RADIO_MODULATIONS[self.modulation]
        self.radio_configuration = RadioConfiguration(self.gloria_modulation)
        self.type = type
        self.master = master
        self.layout = layout

        self.slots: typing.List[lwb_slot.LWBSlot] = []

        self.generate()

    def __str__(self):
        return "<LWBRound:{:f},{:d},{}>".format(self.round_marker, self.modulation, self.type)

    @property
    def low_power(self):
        if self.type is LWBRoundType.LP_NOTIFICATION:
            return True
        else:
            return False

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
                slot_offset += np.ceil(slot.total_time / lwb_slot.LWB_SCHEDULE_GRANULARITY) * lwb_slot.LWB_SCHEDULE_GRANULARITY
                slot = lwb_slot.LWBSlot.create_ack_slot(self, slot_offset, self.modulation, master=item.target,
                                                        index=index)
            elif item.type is LWBSlotItemType.ROUND_CONTENTION:
                slot = lwb_slot.LWBSlot.create_round_contention_slot(self, slot_offset, self.modulation,
                                                                     master=item.master,
                                                                     index=index)
            elif item.type is LWBSlotItemType.DATA:
                slot = lwb_slot.LWBSlot.create_data_slot(self, slot_offset, self.modulation, payload=item.payload,
                                                         master=item.master, index=index, power_level=item.power_level,
                                                         stream=item.stream)
                self.slots.append(slot)
                index += 1
                slot_offset += np.ceil(slot.total_time / lwb_slot.LWB_SCHEDULE_GRANULARITY) * lwb_slot.LWB_SCHEDULE_GRANULARITY
                slot = lwb_slot.LWBSlot.create_ack_slot(self, slot_offset, self.modulation, master=item.target,
                                                        index=index, power_level=item.ack_power_level)
            else:
                slot = None

            self.slots.append(slot)
            slot_offset += np.ceil(slot.total_time / lwb_slot.LWB_SCHEDULE_GRANULARITY) * lwb_slot.LWB_SCHEDULE_GRANULARITY
            index += 1

    @staticmethod
    def create_sync_round(round_marker: float, modulation: int, master: 'sim_node.SimNode' = None):
        layout = []

        layout.append(LWBSlotItem(LWBSlotItemType.SYNC))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE))

        return LWBRound(round_marker, modulation, type=LWBRoundType.SYNC, layout=layout, master=master)

    @staticmethod
    def create_data_round(round_marker: float, modulation: int, data_slots, master: 'sim_node.SimNode' = None):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE, master=master))
        item: LWBDataSlotItem
        for item in data_slots:
            layout.append(LWBSlotItem(LWBSlotItemType.DATA, master=item.master, target=item.target,
                                      payload=item.data_payload + lwb_slot.LWB_DATA_HEADER_LENGTH,
                                      power_level=item.power_level, ack_power_level=item.ack_power_level,
                                      stream=item.stream))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.DATA, layout=layout, master=master)

    @staticmethod
    def create_stream_request_round(round_marker: float, modulation: int, contention_count: int,
                                    master: 'sim_node.SimNode' = None):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE))
        for i in range(contention_count):
            layout.append(LWBSlotItem(LWBSlotItemType.CONTENTION))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.STREAM_REQUEST, layout=layout, master=master)

    @staticmethod
    def create_notification_round(round_marker: float, modulation: int, data_slots,
                                  master: 'sim_node.SimNode' = None):
        layout = []
        layout.append(LWBSlotItem(LWBSlotItemType.SLOT_SCHEDULE, master=master))
        item: LWBDataSlotItem
        for item in data_slots:
            layout.append(LWBSlotItem(LWBSlotItemType.DATA, master=item.master, target=item.target,
                                      payload=item.data_payload, stream=item.stream))
        layout.append(LWBSlotItem(LWBSlotItemType.ROUND_SCHEDULE, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.NOTIFICATION, layout=layout, master=master)

    @staticmethod
    def create_lp_notification_round(round_marker: float, modulation: int, notification_count: int,
                                     master: 'sim_node.SimNode' = None):
        layout = []
        for i in range(notification_count):
            layout.append(LWBSlotItem(LWBSlotItemType.CONTENTION, master=master))

        return LWBRound(round_marker, modulation, type=LWBRoundType.LP_NOTIFICATION, layout=layout, master=master)
