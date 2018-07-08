from flora_tools.sim.sim_node import SimNode
from flora_tools.sim.service import Service
from flora_tools.sim.sim_message import SimMessage

MAX_TTL = 3


class DataStream:
    def __init__(self, service: Service, priority, datarate, period, max_slot_size=255):
        self.service = service
        self.priority = priority
        self.datarate = datarate
        self.period = period
        self.max_slot_size = max_slot_size

        self.ttl = MAX_TTL

        def get_data(self) -> SimMessage:
            return self.service.

        def data_available(self) -> SimMessage:
            return


class NotificationStream:
    def __init__(self, service: Service, priority, period):
        self.service = service
        self.priority = priority
        self.period = period

        self.ttl = MAX_TTL

        @abc.abstractmethod
        def get_notification(self) -> SimMessage:
            return self.service.get_notification()


class LocalServiceManager:
    def __init__(self, node: 'SimNode'):
        self.node = node
        self.datastreams = []

    def register_datastream(self, datastream: DataStream):
        self.datastreams.append(datastream)

    def register_notification(self, ):


