from typing import List

import numpy as np

import flora_tools.lwb_round as lwb_round
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_message as sim_message
import flora_tools.sim.sim_node as sim_node
import flora_tools.sim.lwb_stream as strm


class LWBSlotSchedule:
    def __init__(self, round: 'lwb_round.LWBRound'):
        self.round = round
        self.type = round.type

        self.round_marker = round.round_marker
        self.slot_count = int((len(round.slots) - 2) / 2)
        self.schedule_items: List[lwb_round.LWBDataSlotItem] = []

        if self.type is lwb_round.LWBRoundType.NOTIFICATION:
            for i in range(self.slot_count):
                slot = self.round.slots[i * 2 + 1]
                slot.stream.schedule_slot(self.round_marker)
                self.schedule_items.append(lwb_round.LWBDataSlotItem(slot.master, None, lwb_slot.GLORIA_HEADER_LENGTH))

        elif self.type is lwb_round.LWBRoundType.STREAM_REQUEST:
            for i in range(self.slot_count):
                slot = self.round.slots[i * 2 + 1]
                self.schedule_items.append(lwb_round.LWBDataSlotItem(slot.master, None, slot.payload))

        elif self.type is lwb_round.LWBRoundType.DATA:
            for i in range(self.slot_count):
                slot = self.round.slots[i * 2 + 1]
                slot.stream.schedule_slot(self.round_marker)
                self.schedule_items.append(
                    lwb_round.LWBDataSlotItem(slot.master, slot.stream, slot.payload - lwb_slot.LWB_DATA_HEADER_LENGTH,
                                              power_level=slot.power_level))

        self.payload = lwb_slot.LWB_SLOT_SCHEDULE_HEADER_LENGTH + len(
            self.schedule_items) * lwb_slot.LWB_SLOT_SCHEDULE_ITEM_LENGTH


class LWBScheduleManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.next_rounds: List[lwb_round.LWBRound] = [None] * len(lwb_slot.RADIO_MODULATIONS)

        self.last_sync: float = 0

        self.data_slot_count = lwb_round.LWB_MAX_SLOT_COUNT
        self.notification_slot_count = lwb_round.LWB_MAX_SLOT_COUNT

        self.stream_request_layout = lwb_round.LWB_INITIAL_STREAM_REQUEST_SLOT_COUNT.copy()

        if self.node.role is sim_node.SimNodeRole.BASE:
            self.generate_initial_schedule()

    def increment_contention(self, modulation):
        if self.stream_request_layout[modulation] < lwb_round.LWB_MAX_STREAM_REQUEST_SLOT_COUNT[modulation]:
            self.stream_request_layout[modulation] += 1

    def decrement_contention(self, modulation):
        if self.stream_request_layout[modulation] > lwb_round.LWB_MIN_STREAM_REQUEST_SLOT_COUNT[modulation]:
            self.stream_request_layout[modulation] -= 1

    def generate_initial_schedule(self):
        sync_round: lwb_round.LWBRound = lwb_round.LWBRound.create_sync_round(self.get_next_epoch(),
                                                                              0,
                                                                              self.node)
        self.last_sync: float = 0
        self.next_rounds[0] = sync_round

    def get_next_round(self):
        sorted_next_rounds: List[lwb_round.LWBRound] = sorted(
            [round for round in self.next_rounds if
             round is not None],
            key=lambda x: x.round_marker)

        if len(sorted_next_rounds):
            round = sorted_next_rounds[0]
            self.next_rounds[round.modulation] = None
            return round
        else:
            return None

    def get_slot_schedule(self, current_round: 'lwb_round.LWBRound'):
        return LWBSlotSchedule(current_round)

    def get_round_schedule(self, current_round: 'lwb_round.LWBRound'):
        self.schedule_next_rounds(current_round)
        return self.next_rounds.copy()

    def register_round_schedule(self, message: 'sim_message.SimMessage'):
        schedule: List[lwb_round.LWBRound] = message.content.copy()
        for round in schedule:
            if round is not None:
                layout = round.layout[0:1]
                empty_round = lwb_round.LWBRound(round.round_marker, round.modulation, round.type, round.master, layout)
                self.next_rounds[round.modulation] = empty_round

        self.node.lwb.base = message.source

    def register_slot_schedule(self, message: 'sim_message.SimMessage'):
        schedule: LWBSlotSchedule = message.content

        if schedule.type is lwb_round.LWBRoundType.NOTIFICATION:
            round = lwb_round.LWBRound.create_notification_round(schedule.round_marker, message.modulation,
                                                                 schedule.schedule_items, message.source)
        elif schedule.type is lwb_round.LWBRoundType.STREAM_REQUEST:
            round = lwb_round.LWBRound.create_stream_request_round(schedule.round_marker, message.modulation,
                                                                   len(schedule.schedule_items),
                                                                   message.source)
        elif schedule.type is lwb_round.LWBRoundType.DATA:
            round = lwb_round.LWBRound.create_data_round(schedule.round_marker, message.modulation,
                                                         schedule.schedule_items, message.source)
        else:
            round = None
        return round

    def register_sync(self, message: 'sim_message.SimMessage'):
        round_marker = self.calculate_sync_round_marker(message)
        return lwb_round.LWBRound.create_sync_round(round_marker, message.modulation, message.source)

    def schedule_next_rounds(self, current_round: 'lwb_round.LWBRound'):
        last_round = current_round

        for i in reversed(range(current_round.modulation, len(lwb_slot.RADIO_MODULATIONS))):
            condense = True

            last_epoch = self.get_next_epoch(last_round)

            if self.next_rounds[i] is not None:
                if (self.next_rounds[i].round_marker > last_epoch
                        and self.stream_request_layout[i] > 0):
                    round = lwb_round.LWBRound.create_stream_request_round(last_epoch, i, self.stream_request_layout[i])
                else:
                    round = self.next_rounds[i]
            else:
                notification_schedule = self.node.lwb.stream_manager.schedule_notification(
                    self.get_next_epoch(last_round), lwb_round.LWB_MAX_SLOT_COUNT[i], i)

                if len(notification_schedule):
                    round = lwb_round.LWBRound.create_notification_round(last_epoch, i, notification_schedule)
                else:
                    if len(self.node.lwb.stream_manager.datastreams):
                        data_schedule = self.node.lwb.stream_manager.schedule_data(
                            self.get_next_epoch(last_round), lwb_round.LWB_MAX_SLOT_COUNT[i], i)
                    else:
                        data_schedule = []

                    if len(data_schedule):
                        data_slots: List[lwb_round.LWBDataSlotItem] = []
                        for stream in data_schedule:
                            data_slots.append(
                                lwb_round.LWBDataSlotItem(
                                    stream.master, None,
                                    stream.max_payload, stream,
                                    power_level=self.node.lwb.link_manager.get_link(stream.master)['power_level'],
                                    ack_power_level=stream.advertised_ack_power_level))

                        round = lwb_round.LWBRound.create_data_round(last_epoch, i, data_slots, self.node)
                    elif self.stream_request_layout[i] > 0:
                        round = lwb_round.LWBRound.create_stream_request_round(last_epoch, i,
                                                                               self.stream_request_layout[i], self.node)
                    else:
                        condense = False
                        next_time, stream_type = self.node.lwb.stream_manager.get_next_round_schedule_timestamp(i)
                        if next_time is not None:
                            if stream_type is strm.NotificationStream:
                                notification_schedule = self.node.lwb.stream_manager.schedule_notification(
                                    self.get_next_epoch(next_time), lwb_round.LWB_MAX_SLOT_COUNT[i], i)

                                if len(notification_schedule):
                                    round = lwb_round.LWBRound.create_notification_round(next_time, i,
                                                                                         notification_schedule)
                            else:
                                if len(self.node.lwb.stream_manager.datastreams):
                                    data_schedule = self.node.lwb.stream_manager.schedule_data(next_time,
                                                                                               lwb_round.LWB_MAX_SLOT_COUNT[
                                                                                                   i],
                                                                                               i)
                                else:
                                    data_schedule = []

                                if len(data_schedule):
                                    data_slots: List[lwb_round.LWBDataSlotItem] = []
                                    for stream in data_schedule:
                                        data_slots.append(
                                            lwb_round.LWBDataSlotItem(
                                                stream.master, None,
                                                stream.max_payload, stream,
                                                power_level=self.node.lwb.link_manager.get_link(stream.master)[
                                                    'power_level'],
                                                ack_power_level=stream.advertised_ack_power_level))

                                    round = lwb_round.LWBRound.create_data_round(next_time, i, data_slots, self.node)
                        else:
                            if i is 0:
                                next_sync = last_epoch + np.ceil(
                                    (last_epoch - self.last_sync) / lwb_slot.LWB_SYNC_PERIOD) * lwb_slot.LWB_SYNC_PERIOD
                                round = lwb_round.LWBRound.create_sync_round(next_sync, i, self.node)
                                self.last_sync = next_sync
                            else:
                                continue

            interfering_rounds: List[lwb_round.LWBRound] = sorted(
                [interfering_round for interfering_round in self.next_rounds[0:current_round.modulation] if
                 interfering_round is not None], key=lambda x: x.round_marker)

            if condense:
                if len(interfering_rounds):
                    for interfering_round in interfering_rounds:
                        if round.round_end_marker < interfering_round.round_marker:
                            round.round_marker = last_epoch
                            break
                        else:
                            last_epoch = interfering_round.round_end_marker
                            round.round_marker = last_epoch
                    self.next_rounds[i] = round
                else:
                    self.next_rounds[i] = round
            else:
                if len(interfering_rounds):
                    for interfering_round in interfering_rounds:
                        if round.round_end_marker < interfering_round.round_marker:
                            break
                        else:
                            last_epoch = interfering_round.round_end_marker
                            round.round_marker = np.max([last_epoch, round.round_marker])

                    self.next_rounds[i] = round
                else:
                    self.next_rounds[i] = round

            if round is not None:
                last_round = round

    def get_next_epoch(self, round: 'lwb_round.LWBRound' = None):
        if round is None:
            return 0
        else:
            return np.ceil(
                round.round_end_marker / lwb_slot.LWB_SCHEDULE_GRANULARITY) * lwb_slot.LWB_SCHEDULE_GRANULARITY

    def invoke_round_request(self):
        self.stream_request_layout = lwb_round.LWB_INITIAL_STREAM_REQUEST_SLOT_COUNT.copy()

    def calculate_sync_round_marker(self, message: 'sim_message.SimMessage'):
        if message.type is sim_message.SimMessageType.SYNC:
            tmp_sync = lwb_round.LWBRound.create_sync_round(0, message.modulation)
            slot_time = tmp_sync.slots[0].flood.slots[0].slot_time
            setup_time = tmp_sync.slots[0].flood.slots[0].tx_marker
            round_marker = (
                    message.freeze_timestamp
                    - slot_time * (
                            message.freeze_hop_count - 1
                            + 2 * (
                                    message.freeze_power_level
                                    - lwb_slot.GLORIA_DEFAULT_POWER_LEVELS[
                                        lwb_slot.RADIO_MODULATIONS[message.modulation]]
                            )
                    )
                    - setup_time
            )

            return round_marker
        else:
            return None
