from enum import Enum

from flora_tools.sim.sensor_service import SensorService
import flora_tools.sim.sim_event_manager as sim_event_manager
from flora_tools.sim.sim_lwb import SimLWB
from flora_tools.sim.sim_message_manager import SimMessageManager
from flora_tools.sim.sim_network import SimNetwork


class SimNodeRole(Enum):
    BASE = 1
    RELAY = 2
    SENSOR = 3


class SimNode:
    def __init__(self, network: 'SimNetwork', em: 'sim_event_manager.SimEventManager', mm: SimMessageManager, id: int = None,
                 role: SimNodeRole = SimNodeRole.SENSOR):
        self.state = 'init'
        self.network = network
        self.mm = mm
        self.em = em
        self.id = id
        self.role = role

        self.lwb = SimLWB(self)

        self.local_timestamp = 0

        if self.role is SimNodeRole.SENSOR:
            service = SensorService(self, "sensor_data{}".format(self.id), 10)
            self.lwb.stream_manager.register_data(service.datastream)

    def run(self):
        self.lwb.run()

    def __str__(self):
        return str(self.id)

    def transform_local_to_global_timestamp(self, timestamp):
        timestamp - self.local_timestamp + self.network.current_timestamp
