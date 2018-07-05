import pandas as pd

import flora_tools.lwb_math as lwb_math

from flora_tools.sim.sim_node import SimNode


class SimLinkManager:
    def __init__(self, node: SimNode):
        self.node = node

        self.links = pd.DataFrame(columns=['modulation', 'power', 'counter'])
        self.links.index.name = 'id'

    def update_link(self, link):
        current_link = self.links[link['id']]

        if link['modulation'] > current_link['modulation'] or (link['modulation'] == current_link['modulation'] and link['power'] < current_link['power']):
            if current_link['counter'] == 0:
                self.links[link['id']] = [link['modulation'], link['power'], 1]
            else:
                self.links[link['id'], 'counter'] -= 1

    def downgrade_link(self, id):
        self.links[id, 'counter'] += 1
        if self.links[id, 'counter'] > 1:
            if self.links[id, 'power'] < len(lwb_math.powers) - 1:
                self.links[id] = [self.links[id, 'modulation'], self.links[id, 'power'] + 1, 1]
            else:
                if self.links[id, 'modulation'] < len(lwb_math.modulations) - 1:
                    self.links[id] = [self.links[id, 'modulation'] + 1, self.links[id, 'power'] + 1, 1]
                else:
                    self.links.drop(id)