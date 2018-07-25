from itertools import combinations

import cairo
import networkx as nx
import numpy as np

import flora_tools.sim.sim_event_manager as sim_event_manager
import flora_tools.sim.sim_node as sim_node
from flora_tools.radio_configuration import RadioConfiguration
from flora_tools.radio_math import RadioMath
from flora_tools.sim.sim_analyzer import SimAnalyzer
from flora_tools.sim.sim_message_channel import SimMessageChannel
from flora_tools.sim.sim_message_manager import SimMessageManager


class SimNetwork:
    def __init__(self, surface: cairo.SVGSurface = None, node_count=5, event_count: int = None,
                 time_limit: float = None, path_loss=[90, 140], seed: int = 0):
        self.global_timestamp = 0

        self.visualizer = SimAnalyzer(surface)

        self.mm = SimMessageManager(self)
        self.mc = SimMessageChannel(self)
        self.em = sim_event_manager.SimEventManager(self, event_count=event_count, time_limit=time_limit)

        self.nodes = [sim_node.SimNode(self, mm=self.mm, em=self.em, id=i, role=(
            sim_node.SimNodeRole.SENSOR if i is not 0 else sim_node.SimNodeRole.BASE))
                      for i in range(node_count)]
        self.G = nx.Graph()
        self.G.add_nodes_from(range(node_count))

        edges = list(combinations(range(node_count), 2))

        np.random.seed(seed)
        path_losses = np.random.uniform(path_loss[0], path_loss[1], len(list(edges)))
        channels = [tuple([edge[0], edge[1], {'path_loss': path_losses[index]}]) for index, edge in enumerate(edges)]

        self.G.add_edges_from(channels)

    def run(self):
        for node in self.nodes:
            node.run()

        self.em.loop()

    def draw(self, modulation=None, power=22):
        if modulation is not None:
            H = self.G.copy()
            config = RadioConfiguration(modulation)
            math = RadioMath(config)
            edges_to_remove = []
            for (u, v, pl) in H.edges.data('path_loss'):
                if pl > math.link_budget(power=power):
                    edges_to_remove.append((u, v))

            H.remove_edges_from(edges_to_remove)

            config = RadioConfiguration(modulation)

            pos = nx.spring_layout(H)
            edge_labels = dict([((u, v), "{:.2f}".format(d['path_loss'])) for u, v, d in H.edges(data=True)])
            nx.draw(H, with_labels=True, node_size=500, node_color=config.color, font_color='white', pos=pos)
            nx.draw_networkx_edge_labels(H, pos=pos, edge_labels=edge_labels)
        else:
            pos = nx.spring_layout(H)
            edge_labels = dict([((u, v), "{:.2f}".format(d['path_loss'])) for u, v, d in self.G.edges(data=True)])
            nx.draw(self.G, with_labels=True, node_size=500, node_color='black', font_color='white', pos=pos)
            nx.draw_networkx_edge_labels(self.G, pos=pos, edge_labels=edge_labels)
