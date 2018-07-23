import pandas as pd

import flora_tools.lwb_slot as lwb_slot
import flora_tools.sim.sim_node as sim_node

UPGRADE_COUNTER = 2
DOWNGRADE_COUNTER = 1


class LWBLinkManager:
    def __init__(self, node: 'sim_node.SimNode'):
        self.node = node

        self.links = pd.DataFrame(columns=['modulation', 'power_level', 'counter', 'hop_count'])
        self.acknowledged_links = pd.DataFrame(columns=['modulation', 'power_level', 'counter', 'hop_count'])
        self.links.index.name = 'id'

    def upgrade_link(self, target_node: 'sim_node.SimNode', modulation: int, power_level: int, hop_count: int = None):
        if target_node.id in self.links.index:
            current_link = self.links.loc[target_node.id, :]

            if modulation > current_link['modulation'] or (
                    modulation == current_link['modulation'] and power_level < current_link['power_level']):
                if current_link['counter'] <= 0:
                    self.links[target_node.id] = [modulation, power_level, UPGRADE_COUNTER, hop_count]
                else:
                    self.links.loc[target_node.id, 'counter'] -= 1

        else:
            self.links[target_node.id] = [modulation, power_level, UPGRADE_COUNTER, hop_count]

    def downgrade_link(self, target_node: 'sim_node.SimNode'):
        self.links[target_node.id, 'counter'] += 1
        if self.links[target_node.id, 'counter'] > DOWNGRADE_COUNTER:
            self.remove_acknowledged_link(target_node)

            if self.links[target_node.id, 'power_level'] < len(lwb_slot.POWERS) - 1:
                self.links[target_node.id] = [self.links[target_node.id, 'modulation'],
                                              self.links[target_node.id, 'power_level'] + 1, 0]
            else:
                if self.links[target_node.id, 'modulation'] < len(lwb_slot.MODULATIONS) - 1:
                    self.links[target_node.id] = [self.links[target_node.id, 'modulation'] + 1,
                                                  self.links[target_node.id, 'power_level'] + 1, 0]
                else:
                    self.links.drop(id)

    def acknowledge_link(self, target_node: 'sim_node.SimNode'):
        self.acknowledged_links.loc[target_node.id, :] = self.links.loc[target_node.id, :]

    def remove_acknowledged_link(self, target_node: 'sim_node.SimNode'):
        self.acknowledged_links.loc[target_node.id].drop()

    def get_link(self, target_node: 'sim_node.SimNode'):
        link = self.links.loc[target_node.id]
        return link

    def get_acknowledged_link(self, target_node: 'sim_node.SimNode'):
        link = self.links.loc[target_node.id]
        return link
