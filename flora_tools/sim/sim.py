from flora_tools.sim.sim_network import SimNetwork


class Sim:
    def __init__(self, event_count=1000):
        self.network = SimNetwork(event_count=event_count)

    def run(self):
        self.network.run()
