from typing import List

import numpy as np

import flora_tools.lwb_round as lwb_round
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node


class LWBScheduleItem:
    def __init__(self, period: float):
        self.period = period


class LWBSlotSchedule:
    def __init__(self, rounde: 'lwb_round.LWBRound'):
        self.round = rounde
        self.type = rounde.type

        if self.type is lwb_round.LWBRoundType.NOTIFICATION:
            self.slot_count = (len(rounde.slots) - 2) / 2

            self.data_slots: List[lwb_round.LWBDataSlotItem] = []

            for i in range(self.slot_count):
                slot = self.round.slots[i * 2 + 1]
                self.data_slots.append(lwb_round.LWBDataSlotItem(slot.master, None, lwb_slot.gloria_header_length))

        # TODO: Full Encoding. Add registration procedures for client nodes


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
             interfering_round is not None], key=lambda x: x.round_marker)[0]

        if len(sorted_next_rounds):
            round = sorted_next_rounds[0]
            self.next_rounds[round.modulation] = None
            return round
        else:
            return None

    def schedule_next_rounds(self, current_round: lwb_round.LWBRound):
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

    def get_next_epoch(self, round: lwb_round.LWBRound):
        if round is None:
            return 0
        else:
            return np.ceil(round.round_end_marker / lwb_slot.SCHEDULE_GRANULARITY) * lwb_slot.SCHEDULE_GRANULARITY
