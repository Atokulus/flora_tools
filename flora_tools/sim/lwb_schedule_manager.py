from typing import List

import numpy as np

import flora_tools.lwb_round as lwb_round
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node

class LWBDataSlotItem:
    def __init__(self, master: 'sim_node.SimNode', length, stream = None):
        self.master = master
        self.length = length
        self.stream = stream

class LWBSlotSchedule:
    def __init__(self, round: 'lwb_round.LWBRound'):
        self.round = round
        self.type = round.type

        self.slot_count = int((len(round.slots) - 2) / 2)
        self.schedule_items: List[lwb_round.LWBDataSlotItem] = []

        if self.type is lwb_round.LWBRoundType.NOTIFICATION:
            for i in range(self.slot_count):
                slot = self.round.slots[i * 2 + 1]
                self.schedule_items.append(lwb_round.LWBDataSlotItem(slot.master, None, lwb_slot.gloria_header_length))

        elif self.type is lwb_round.LWBRoundType.STREAM_CONTENTION:
            for i in range(self.slot_count):
                slot = self.round.slots[i * 2 + 1]
                self.schedule_items.append(lwb_round.LWBDataSlotItem(slot.master, None, slot.payload))

        elif self.type is lwb_round.LWBRoundType.DATA:
            for i in range(self.slot_count):
                slot = self.round.slots[i * 2 + 1]
                self.schedule_items.append(lwb_round.LWBDataSlotItem(slot.master, slot.stream, slot.payload))

class LWBScheduleManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.next_rounds: List[lwb_round.LWBRound] = [None] * len(lwb_slot.MODULATIONS)

        self.last_sync: float = 0

        self.data_slot_count = lwb_round.SLOT_COUNTS
        self.notification_slot_count = lwb_round.SLOT_COUNTS

        self.stream_contention_layout = lwb_round.initial_contention_layout

        if self.node.role is sim_node.SimNodeRole.BASE:
            self.generate_initial_schedule()

    def increment_contention(self, modulation):
        if self.stream_contention_layout[modulation] < lwb_round.max_contention_layout:
            self.stream_contention_layout[modulation] += 1

    def decrement_contention(self, modulation):
        if self.stream_contention_layout[modulation] > lwb_round.min_contention_layout:
            self.stream_contention_layout[modulation] -= 1

    def generate_initial_schedule(self):
        sync_round: lwb_round.LWBRound = lwb_round.LWBRound.create_sync_round(self.get_next_epoch(),
                                                                              lwb_slot.MODULATIONS[0],
                                                                              self.node)
        self.last_sync: float = 0
        self.next_rounds[0] = sync_round

    def get_next_round(self):
        sorted_next_rounds: List[lwb_round.LWBRound] = sorted(
            [interfering_round for interfering_round in self.next_rounds if
             type(interfering_round) is lwb_round.LWBRound], key=lambda x: x.round_marker)[0]

        if len(sorted_next_rounds):
            round = sorted_next_rounds[0]
            self.next_rounds[round.modulation] = None
            return round
        else:
            return None

    def get_schedule(self, current_round: 'lwb_round.LWBRound'):
        self.schedule_next_rounds(current_round)

        return self.next_rounds

    def register_round_schedule(self, schedule):
        self.next_rounds = schedule

    def register_slot_schedule(self, round: 'lwb_round.LWBRound', schedule: LWBSlotSchedule):
        if schedule.type is lwb_round.LWBRoundType.NOTIFICATION:
            pass
        elif schedule.type is lwb_round.LWBRoundType.STREAM_CONTENTION:
            pass
        elif schedule.type is lwb_round.LWBRoundType.DATA:
            pass

    def schedule_next_rounds(self, current_round: 'lwb_round.LWBRound'):
        last_round = current_round

        for i in reversed(range(current_round.modulation, len(lwb_slot.MODULATIONS))):
            last_epoch = self.get_next_epoch(last_round)

            if self.next_rounds[i] is not None:
                if (self.next_rounds[i] > last_epoch
                        and self.stream_contention_layout[i] > 0):
                    round = lwb_round.LWBRound.create_stream_request_round(last_epoch)
                else:
                    round = self.next_rounds[i]
            else:
                notification_schedule = self.node.lwb.stream_manager.schedule_notification(
                    lwb_round.SLOT_COUNTS[i], i, timestamp=self.get_next_epoch(last_round))

                if len(notification_schedule):
                    round = lwb_round.LWBRound.create_notification_round(last_epoch, i, notification_schedule)
                else:
                    data_schedule = self.node.lwb.stream_manager.schedule_data(
                        lwb_round.SLOT_COUNTS[i], i, timestamp=self.get_next_epoch(last_round))
                    if len(data_schedule):
                        round = lwb_round.LWBRound.create_data_round(data_schedule)
                    else:
                        next_time = self.node.lwb.stream_manager.get_next_round_schedule_timestamp()
                        if next_time is not None:
                            round = lwb_round.LWBRound.create_sync_round(next_time, i, self.node)
                        else:
                            round = None
                            continue

            if i is 0:
                if round is None:
                    if last_epoch - self.last_sync > lwb_slot.SYNC_PERIOD:
                        round = lwb_round.LWBRound.create_sync_round(last_epoch, i, self.node)
                else:
                    self.last_sync = last_epoch

            interfering_rounds: List[lwb_round.LWBRound] = sorted(
                [interfering_round for interfering_round in self.next_rounds[0:current_round.modulation] if
                 interfering_round is not None], key=lambda x: x.round_marker)

            for interfering_round in interfering_rounds:
                if round.round_end_marker < interfering_round.round_marker:
                    round.round_marker = last_epoch
                    self.next_rounds[i] = round
                    break
                else:
                    last_epoch = interfering_round.round_end_marker
                    round.round_marker = last_epoch

    def get_next_epoch(self, round: 'lwb_round.LWBRound' = None):
        if round is None:
            return 0
        else:
            return np.ceil(round.round_end_marker / lwb_slot.SCHEDULE_GRANULARITY) * lwb_slot.SCHEDULE_GRANULARITY
