from flora_tools.sim.service import Service
from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_node import SimNode

MAX_TTL = 3


class DataStream:
    def __init__(self, service: Service, priority, subpriority, datarate, period, max_slot_size=255):
        self.service = service
        self.priority = priority
        self.subpriority = subpriority
        self.datarate = datarate
        self.period = period
        self.max_slot_size = max_slot_size
        self.stream_manager: StreamManager = None

        self.ttl = MAX_TTL
        self.to_be_registered = True

    def data(self) -> SimMessage:
        return self.service.get_data()

    def available(self) -> SimMessage:
        return self.service.data_available()

    def success(self):
        self.ttl = MAX_TTL

    def fail(self):
        self.ttl -= 1
        if self.ttl is 0:
            self.stream_manager.remove_data(self)
            self.service.failed_datastream_callback(self)

    def retry(self):
        self.ttl = MAX_TTL
        self.to_be_registered = True


class NotificationStream:
    def __init__(self, service: Service, priority: int, subpriority: int, period):
        self.service = service
        self.priority = priority
        self.subpriority = subpriority
        self.period = period

        self.ttl = MAX_TTL
        self.to_be_registered = True

    def get(self) -> SimMessage:
        return self.service.get_notification()

    def available(self) -> SimMessage:
        return self.service.notification_available()

    def success(self):
        self.ttl = MAX_TTL

    def fail(self):
        self.ttl -= 1


class StreamManager:
    def __init__(self, node: 'SimNode'):
        self.node = node
        self.datastreams = []
        self.notification_streams = []

    def register_data(self, datastream: DataStream):
        self.datastreams.append(datastream)
        datastream.stream_manager = self

    def remove_data(self, datastream: DataStream):
        self.datastreams.remove(datastream)

    def register_notification(self, notification_stream: DataStream):
        self.notification_streams.append(notification_stream)
        notification_stream.stream_manager = self

    def remove_notification(self, notification_stream: DataStream):
        self.notification_streams.remove(notification_stream)

    def select_data(self, payload_size: int):
        best_match: DataStream = None

        stream: DataStream
        for stream in self.datastreams:
            if not stream.to_be_registered and stream.available() and stream.available().payload <= payload_size:
                if best_match is None:
                    best_match = stream
                else:
                    if best_match.priority >= stream.priority \
                            and best_match.subpriority >= stream.subpriority \
                            and best_match.available().payload < stream.available().payload:
                        best_match = stream

        return best_match

    def select_notification(self):
        best_match: NotificationStream = None

        stream: NotificationStream
        for stream in self.notification_streams:
            if not stream.to_be_registered and stream.available():
                if best_match is None:
                    best_match = stream
                else:
                    if best_match.priority >= stream.priority \
                            and best_match.subpriority > stream.subpriority:
                        best_match = stream

        return best_match
