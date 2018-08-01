from copy import copy
from typing import List, Union, Tuple, Optional

import numpy as np

import flora_tools.lwb_round as lwb_round
import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.lwb_service as service
import flora_tools.sim.sim_node as sim_node
from flora_tools.sim.sim_message import SimMessage, SimMessageType

LWB_STREAM_MAX_TTL = 3
LWB_STREAM_MAX_REQUEST_TRIALS = 10
LWB_STREAM_DEACTIVATION_BACKDROP = 100
LWB_STREAM_MAX_BACKDROP_RANGE = 16
LWB_STREAM_INITIAL_BACKDROP_RANGE = 4


class DataStream:
    def __init__(self, id: str, node: 'sim_node.SimNode', master: 'sim_node.SimNode', priority, subpriority, period,
                 service: 'service.Service' = None, destination: 'sim_node.SimNode' = None,
                 max_payload=None, needs_ack=True):
        self.id = id
        self.node = node
        self.master = master
        self.destination = destination
        self.service = service

        self.priority = priority
        self.subpriority = subpriority
        self.period = period

        self.max_payload = max_payload
        self.needs_ack = needs_ack

        self.stream_manager: LWBStreamManager = None
        self._last_consumption = self.node.local_timestamp - self.period
        self.ttl = LWB_STREAM_MAX_TTL
        self.is_ack = False

        if max_payload is None:
            max_payload = lwb_slot.LWB_MAX_DATA_PAYLOAD

        self.slot_count = int(np.ceil(self.max_payload / lwb_slot.LWB_MAX_DATA_PAYLOAD))
        self.last_slot_size = self.max_payload % max_payload
        self.current_slot = 0

        self.trial_modulation = None
        self.trial_counter = 0
        self.backdrop = 0
        self.backdrop_range = LWB_STREAM_INITIAL_BACKDROP_RANGE

        # TODO Contracts

        self.advertised_ack_power_level = None  # Modulation not needed, as it is implicated by the stream request handshake

    @property
    def last_consumption(self):
        return self._last_consumption

    @last_consumption.setter
    def last_consumption(self, value):
        self._last_consumption = value

    def schedule_slot(self, timestamp):
        if self.current_slot < self.slot_count - 1:
            self.current_slot += 1
        else:
            self.current_slot = 0
            self.last_consumption = timestamp

    def check_request(self, round: 'lwb_round.LWBRound', modulation: int) -> bool:
        if not self.backdrop:
            self.backdrop = np.random.choice(range(self.backdrop_range))
            self.backdrop_range *= 2
            if self.backdrop_range > LWB_STREAM_MAX_BACKDROP_RANGE:
                self.backdrop_range = LWB_STREAM_MAX_BACKDROP_RANGE

            if self.trial_modulation is not None:
                self.trial_counter += 1

                if self.trial_counter >= LWB_STREAM_MAX_REQUEST_TRIALS:
                    if self.trial_modulation > 0:
                        self.trial_modulation -= 1
                        self.trial_counter = 0
                    else:
                        self.trial_modulation = None
                        self.trial_counter = 0
                        self.backdrop = LWB_STREAM_DEACTIVATION_BACKDROP

                if modulation == self.trial_modulation:
                    return True
                else:
                    return False
            else:
                if self.node.lwb.link_manager.get_link(round.master)['modulation'] > modulation:
                    return False
                else:
                    self.trial_counter += 1
                    self.trial_modulation = modulation
                    return True
        else:
            self.backdrop -= 1
            return False

    def reset_request_check(self, round: 'lwb_round.LWBRound'):
        if self.trial_modulation == round.modulation:
            self.trial_counter = 0
            self.backdrop = 0
            self.backdrop_range = LWB_STREAM_INITIAL_BACKDROP_RANGE

    @property
    def next_period(self):
        return self.last_consumption + self.period

    def __copy__(self):
        return DataStream(self.id, self.node, self.master, self.priority, self.subpriority, self.period, service=None,
                          destination=self.destination, max_payload=self.max_payload, needs_ack=self.needs_ack)

    def get(self):
        return self.service.get_data()

    def available(self, timestamp=None):
        if timestamp is None:
            timestamp = self.service.node.local_timestamp

        if self.current_slot < self.slot_count:
            if self.service is not None:
                return self.service.data_available()
            elif timestamp - self.last_consumption > self.period:
                return (self.slot_count - self.current_slot) * self.max_payload
            else:
                return 0
        else:
            return 0

    def success(self):
        self.ttl = LWB_STREAM_MAX_TTL
        self.backdrop = 0
        self.backdrop_range = LWB_STREAM_INITIAL_BACKDROP_RANGE
        self.trial_counter = 0

        if self.current_slot < self.slot_count - 1:
            self.current_slot += 1
        else:

            self.current_slot = 0
            if self.service is not None:
                self.last_consumption = self.node.local_timestamp  # Not required on BASE
                self.service.ack_data_callback()

    def fail(self):
        self.ttl -= 1
        if self.ttl is 0:
            if self.stream_manager is not None:
                self.stream_manager.remove_data(self)
                if self.service is not None:
                    self.service.failed_datastream_callback(self)

    def retry(self):
        self.ttl = LWB_STREAM_MAX_TTL
        self.is_ack = False
        self.stream_manager.register_data(self)


class NotificationStream:
    def __init__(self, id: str, node: 'sim_node.SimNode', master: 'sim_node.SimNode', priority: int, subpriority: int,
                 period, service: 'service.Service' = None, destination: 'sim_node.SimNode' = None, low_power=False,
                 needs_ack=True):
        self.id = id
        self.node = node
        self.master = master
        self.destination = destination
        self.service = service

        self.priority = priority
        self.subpriority = subpriority
        self.period = period

        self.low_power = low_power
        self.needs_ack = needs_ack

        self.stream_manager: LWBStreamManager = None
        self.last_consumption = self.node.local_timestamp - self.period
        self.ttl = LWB_STREAM_MAX_TTL
        self.is_ack = True

        self.trial_modulation = None
        self.trial_counter = 0
        self.backdrop = None
        self.backdrop_range = LWB_STREAM_INITIAL_BACKDROP_RANGE

        self.advertised_ack_power_level = None  # Modulation not needed, as it is implicated by the stream request handshake

    def check_request(self, round: 'lwb_round.LWBRound', modulation: int) -> bool:
        if not self.backdrop:
            self.backdrop = np.random.choice(range(self.backdrop_range))
            self.backdrop_range *= 2
            if self.backdrop_range > LWB_STREAM_MAX_BACKDROP_RANGE:
                self.backdrop_range = LWB_STREAM_MAX_BACKDROP_RANGE

            if self.trial_modulation is not None:
                self.trial_counter += 1

                if self.trial_counter >= LWB_STREAM_MAX_REQUEST_TRIALS:
                    if self.trial_modulation > 0:
                        self.trial_modulation -= 1
                        self.trial_counter = 0
                    else:
                        self.trial_modulation = None
                        self.trial_counter = 0
                        self.backdrop = LWB_STREAM_DEACTIVATION_BACKDROP

                if modulation == self.trial_modulation:
                    return True
                else:
                    return False
            else:
                if self.node.lwb.link_manager.get_link(round.master)['modulation'] > modulation:
                    return False
                else:
                    self.trial_counter += 1
                    self.trial_modulation = modulation
                    return True
        else:
            self.backdrop -= 1
            return False

    def reset_request_check(self, round: 'lwb_round.LWBRound'):
        if self.trial_modulation == round.modulation:
            self.trial_counter = 0
            self.backdrop = 0
            self.backdrop_range = LWB_STREAM_INITIAL_BACKDROP_RANGE

    def __copy__(self):
        return NotificationStream(self.id, self.node, self.master, self.priority, self.subpriority, self.period,
                                  service=None, destination=self.destination, low_power=self.low_power,
                                  needs_ack=self.needs_ack)

    @property
    def next_period(self):
        return self.last_consumption + self.period

    def schedule_slot(self, timestamp):
        self.last_consumption = timestamp

    def get(self):
        return self.service.get_notification()

    def available(self, timestamp=None):
        if timestamp is None:
            timestamp = self.service.node.local_timestamp

        if timestamp - self.last_consumption > self.period:
            if self.service is not None:
                return self.service.notification_available()
            else:
                return True
        else:
            return None

    def success(self):
        self.ttl = LWB_STREAM_MAX_TTL
        self.last_consumption = self.stream_manager.node.local_timestamp
        if self.service is not None:
            self.service.ack_notification_callback()

    def fail(self):
        self.ttl -= 1
        if self.ttl is 0:
            self.stream_manager.remove_notification(self)
            if self.service is not None:
                self.service.failed_notification_callback(self)

    def retry(self):
        self.ttl = LWB_STREAM_MAX_TTL
        self.is_ack = False
        self.stream_manager.register_notification(self)


class LWBStreamManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node
        self.datastreams: List[DataStream] = []
        self.notification_streams: List[NotificationStream] = []

    def register(self, stream: Union[DataStream, NotificationStream]):
        if stream.service is None:
            stream.is_ack = True

        if type(stream) is DataStream:
            self.register_data(stream)
        else:
            self.register_notification(stream)

    def register_data(self, datastream: DataStream):
        datastream.node = self.node
        datastream.stream_manager = self

        for item in self.datastreams:
            if item.id == datastream.id:
                self.datastreams.remove(item)

        self.datastreams.append(datastream)

    def remove_data(self, datastream: DataStream):
        self.datastreams.remove(datastream)

    def register_notification(self, notification_stream: NotificationStream):
        notification_stream.node = self.node
        notification_stream.stream_manager = self
        for item in self.notification_streams:
            if item.id == notification_stream.id:
                self.datastreams.remove(item)

        self.datastreams.append(notification_stream)

    def remove_notification(self, notification_stream: NotificationStream):
        self.notification_streams.remove(notification_stream)

    def select_data(self, slot_size: int = None, selection: List[DataStream] = None, timestamp=None):
        if selection is None:
            selection = self.datastreams.copy()

        best_match: DataStream = None

        if slot_size:
            stream: DataStream
            for stream in selection:
                if (stream.is_ack and stream.available(timestamp=timestamp)
                        and stream.max_payload <= slot_size):
                    if best_match is None:
                        best_match = stream
                    else:
                        if (best_match.priority >= stream.priority
                                and best_match.subpriority >= stream.subpriority
                                and best_match.available(timestamp) < stream.available(timestamp)
                                and best_match.last_consumption > stream.last_consumption):
                            best_match = stream
        else:
            'stream: DataStream'
            for stream in selection:
                if stream.is_ack and stream.available(timestamp):
                    if best_match is None:
                        best_match = stream
                    else:
                        if (best_match.priority >= stream.priority
                                and best_match.subpriority >= stream.subpriority
                                and best_match.available(timestamp) < stream.available(timestamp)
                                and best_match.last_consumption > stream.last_consumption):
                            best_match = stream
        return best_match

    def select_notification(self, selection: List[NotificationStream] = None, low_power=False, timestamp=None):
        if selection is None:
            selection = self.notification_streams

        best_match: NotificationStream = None
        stream: NotificationStream
        for stream in selection:
            if stream.is_ack and stream.available(timestamp=timestamp) and (stream.low_power if low_power else True):
                if best_match is None:
                    best_match = stream
                else:
                    if best_match.priority >= stream.priority \
                            and best_match.subpriority > stream.subpriority:
                        best_match = stream

        return best_match

    def schedule_data(self, timestamp, slot_count: int, modulation: int):
        selection = self.datastreams.copy()
        streams: List[DataStream] = []
        count = 0

        while count < slot_count:
            stream = self.select_data(timestamp=timestamp, selection=selection)
            if (stream is not None
                    and self.node.lwb.link_manager.get_link(stream.master)['modulation'] == modulation
                    and stream.priority <= modulation):

                for i in range(stream.slot_count):
                    streams.append(stream)
                    count += 1
                    if count >= slot_count:
                        break
                selection.remove(stream)
            else:
                break

        return streams

    def schedule_notification(self, timestamp, slot_count: int, modulation: int):
        selection = self.notification_streams.copy()
        streams: List[NotificationStream] = []
        count = 0

        while count < slot_count:
            stream = self.select_notification(selection=selection)
            if (stream is not None
                    and self.node.lwb.link_manager.get_link(stream.master)['modulation'] == modulation
                    and stream.priority <= modulation):
                if stream.priority <= modulation:
                    streams.append(stream)
                    count += 1

                selection.remove(stream)
            else:
                break

        return streams

    def get_round_request(self):
        if (not all([stream.is_ack for stream in self.notification_streams])
                or not all([stream.is_ack for stream in self.datastreams])):
            return SimMessage(self.node.local_timestamp, self.node, lwb_slot.LWB_CONTENTION_HEADER_LENGTH, 0,
                              self.node.lwb.base,
                              SimMessageType.ROUND_REQUEST)
        else:
            return None

    def get_data(self, slot_size: int) -> Tuple[DataStream, SimMessage]:
        stream = self.select_data(slot_size=slot_size - lwb_slot.LWB_DATA_HEADER_LENGTH)

        if stream is not None:
            content = {'data': stream.get(), 'stream': copy(stream)}

            message = SimMessage(self.node.local_timestamp, self.node, stream.max_payload + lwb_slot.LWB_DATA_HEADER_LENGTH,
                                 0,
                                 self.node.lwb.base,
                                 SimMessageType.DATA, content=content)

            return stream, message
        else:
            return None, None

    def get_notification(self, low_power=False) -> Tuple[Optional[NotificationStream], Optional[SimMessage]]:
        stream = self.select_notification(low_power=low_power)
        content = {'notification': stream.get(), 'stream': stream}

        message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.LWB_CONTENTION_HEADER_LENGTH, 0,
                             self.node.lwb.base,
                             SimMessageType.NOTIFICATION, content=content)

        return stream, message

    def get_stream_request(self, round: 'lwb_round.LWBRound', modulation: int, power_level: int) -> Tuple[
        Optional[Union[DataStream, NotificationStream]], Optional[SimMessage]]:
        for stream in self.notification_streams:
            if not stream.is_ack and stream.check_request(modulation, power_level):
                stream = copy(stream)
                stream.advertised_ack_power_level = self.node.lwb.link_manager.get_link(round.master)['power_level']
                message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.LWB_CONTENTION_HEADER_LENGTH, 0,
                                     self.node.lwb.base,
                                     SimMessageType.STREAM_REQUEST,
                                     content={'type': 'notification', 'stream': stream})
                return stream, message

        for stream in self.datastreams:
            if not stream.is_ack and stream.check_request(round, modulation):
                stream = copy(stream)
                stream.advertised_ack_power_level = self.node.lwb.link_manager.get_link(round.master)['power_level']
                message = SimMessage(self.node.local_timestamp, self.node, lwb_slot.LWB_CONTENTION_HEADER_LENGTH, 0,
                                     self.node.lwb.base,
                                     SimMessageType.STREAM_REQUEST,
                                     content={'type': 'data', 'stream': stream})
                return stream, message
        return None, None

    def rx_ack_stream_request(self, message: SimMessage):
        if message.content['type'] is 'data':
            for stream in self.datastreams:
                if stream.id is message.content['stream'].id:
                    stream.is_ack = True
                    break
        elif message.content['type'] is 'notification':
            for stream in self.notification_streams:
                if stream.id is message.content['stream'].id:
                    stream.to_be_registered = False
                    break

    def tx_ack_stream_request(self, stream: Union[DataStream, NotificationStream]):
        return SimMessage(self.node.local_timestamp, self.node, lwb_slot.GLORIA_HEADER_LENGTH, 0,
                          stream.master,
                          SimMessageType.ACK,
                          content={'type': ('data' if type(stream) is DataStream else 'notification'),
                                   'stream': copy(stream)})

    def tx_ack(self, stream: Union[DataStream, NotificationStream]):
        for local_stream in self.datastreams:
            if stream.id == local_stream.id:
                local_stream.success()
        for local_stream in self.notification_streams:
            if stream.id == local_stream.id:
                local_stream.success()

        return SimMessage(self.node.local_timestamp, self.node, lwb_slot.GLORIA_HEADER_LENGTH, 0,
                          stream.master,
                          SimMessageType.ACK, content={'stream': copy(stream)})

    def rx_ack(self, message: SimMessage):
        for stream in self.datastreams:
            if stream.id is message.content['stream'].id:
                stream.success()
                return

        for stream in self.notification_streams:
            if stream.id is message.content['stream'].id:
                stream.success()
                return

    def get_next_round_schedule_timestamp(self, modulation):
        next_period: int = None
        stream_type = None

        for stream in self.datastreams:
            if self.node.lwb.link_manager.get_link(stream.master)['modulation'] is modulation:
                if next_period is None:
                    next_period = stream.next_period
                    stream_type = type(stream)
                elif stream.next_period < next_period:
                    next_period = stream.next_period
                    stream_type = type(stream)

        for stream in self.notification_streams:
            if (not stream.low_power and
                    self.node.lwb.link_manager.get_link(stream.master)['modulation'] is modulation):
                if next_period is None:
                    next_period = stream.next_period
                    stream_type = type(stream)
                elif stream.next_period < next_period:
                    next_period = stream.next_period
                    stream_type = type(stream)

        if next_period is not None:
            return np.ceil(next_period / lwb_slot.LWB_SCHEDULE_GRANULARITY) * lwb_slot.LWB_SCHEDULE_GRANULARITY, stream_type
        else:
            return None, None

    def get_next_lp_notifiaction_round_schedule_timestamp(self, modulation):
        next_period: int = None

        for stream in self.notification_streams:
            if (stream.low_power and
                    self.node.lwb.link_manager.get_acknowledged_link(stream.master)['modulation'] is modulation):
                if next_period is None:
                    next_period = stream.next_period
                elif stream.next_period < next_period:
                    next_period = stream.next_period

        return np.ceil(next_period / lwb_slot.LWB_SCHEDULE_GRANULARITY) * lwb_slot.LWB_SCHEDULE_GRANULARITY

    def retry_all_streams(self):
        for stream in self.datastreams:
            stream.retry()

        for stream in self.notification_streams:
            stream.retry()

    def reset_request_check(self, round: 'lwb_round.LWBRound'):
        for stream in self.datastreams:
            stream.reset_request_check(round)
        for stream in self.notification_streams:
            stream.reset_request_check(round)
