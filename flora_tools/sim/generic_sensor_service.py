from flora_tools.sim.service import Service
from flora_tools.sim.sim_message import SimMessage
from flora_tools.sim.sim_node import SimNode


class GenericSensorService(Service):
    def __init__(self, node: 'SimNode', name, datarate, period, slot_size=255):
        self.node = node
        self.name = name
        self.datarate = datarate
        self.period = period

        self.slot_size = slot_size
        self.accumulated_data = 0.0
        self.last_timestamp = node.network.current_timestamp

    def get_data(self, modulation) -> SimMessage:
        message = self.data_available()
        if message is not None:
            self.accumulated_data -= message.payload

        return message

    def data_available(self) -> SimMessage:
        elapsed = self.node.network.current_timestamp - self.last_timestamp
        self.accumulated_data += elapsed * self.datarate
        self.last_timestamp = self.node.network.current_timestamp

        if self.accumulated_data >= self.slot_size:
            message = SimMessage(None,
                                 self.node,
                                 self.slot_size,
                                 None,
                                 destination=self.node.lwb_manager.base,
                                 type='data',
                                 content={'node': self.node,
                                          'timestamp': self.node.local_timestamp,
                                          'payload': self.slot_size})
            return message
        else:
            return None



