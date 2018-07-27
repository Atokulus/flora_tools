from flora_tools.sim.sim_network import SimNetwork


class Sim:
    def __init__(self, output_path=None, event_count: int = None, time_limit: float = None, seed: int = 0):
        if event_count is None and time_limit is None:
            event_count = 1000

        self.network = SimNetwork(output_path, event_count=event_count, time_limit=time_limit, seed=seed)

    def run(self):
        self.network.run()
        self.network.tracer.store()
