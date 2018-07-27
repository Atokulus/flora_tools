from enum import Enum

import flora_tools.sim.sim_event_manager as sim_event_manager
import flora_tools.sim.sim_network as sim_network
from flora_tools.sim.sensor_service import SensorService
from flora_tools.sim.sim_lwb import SimLWB
from flora_tools.sim.sim_message_manager import SimMessageManager


class SimNodeRole(Enum):
    BASE = 1
    RELAY = 2
    SENSOR = 3

    def __str__(self):
        return '{0}'.format(self.name)


class SimNode:
    def __init__(self, network: 'sim_network.SimNetwork', em: 'sim_event_manager.SimEventManager',
                 mm: SimMessageManager, id: int = None,
                 role: SimNodeRole = SimNodeRole.SENSOR):
        self.state = 'init'
        self.network = network
        self.mm = mm
        self.em = em
        self.id = id
        self.role = role

        self.lwb = SimLWB(self)

        self.local_time_offset = 0

        if self.role is SimNodeRole.SENSOR:
            service = SensorService(self, "sensor_data{}".format(self.id), 26)
            self.lwb.stream_manager.register_data(service.datastream)

    @property
    def local_timestamp(self):
        return self.local_time_offset + self.network.global_timestamp

    @local_timestamp.setter
    def local_timestamp(self, updated_timestamp):
         self.local_time_offset += updated_timestamp - self.local_timestamp

    def run(self):
        self.lwb.run()

    def __str__(self):
        return str(self.id)

    def transform_local_to_global_timestamp(self, timestamp):
        return timestamp - self.local_time_offset

    def transform_global_to_local_timestamp(self, timestamp):
        return timestamp + self.local_time_offset