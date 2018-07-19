from flora_tools.sim.sim_network import SimNetwork
import cairo
import os


class Sim:
    def __init__(self, output_path=None, event_count: int = None, time_limit: float = None):
        if event_count is None and time_limit is None:
            event_count = 1000

        with cairo.SVGSurface(os.path.join(output_path, "simulation_plot.svg"), 200, 200) as surface:
            self.network = SimNetwork(event_count=event_count, time_limit=time_limit, surface=surface)

    def run(self):
        self.network.run()
