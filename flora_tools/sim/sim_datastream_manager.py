from flora_tools.sim.sim_node import SimNode
from flora_tools.sim.service import Service

MAX_TTL = 3


class DataStream:
    def __init__(self, service: Service, priority, datarate, period, max_slot_size=255):
        self.service = service
        self.priority = priority
        self.datarate = datarate
        self.period = period
        self.max_slot_size = max_slot_size

        self.ttl = MAX_TTL

    def data_available(self):
        return self.service.data_available()

    def get_data(self):
        return self.service.get_data()

    def notification_available(self):
        return s


class DataStreamManager:
    def __init__(self, node: 'SimNode'):
        self.node = node
        self.datastreams = []

    def register(self, datastream: DataStream):
        self.datastreams.append(datastream)

    def unregister(self, datastream: DataStream):
        self.datastreams.remove(datastream)

    def update_datastreams


