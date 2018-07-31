import os

from jinja2 import Environment, PackageLoader

from radio_configuration import RadioConfiguration, RADIO_CONFIGURATIONS, RadioModem, BAND_FREQUENCIES, BAND_GROUPS, \
    BAND_FREQUENCIES_US915, BAND_GROUPS_US915


class CodeGen:
    def __init__(self, path):
        self.path = path

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        self.env = Environment(
            loader=PackageLoader('flora_tools', 'codegen/templates'),
            block_start_string='<%',
            block_end_string='%>',
            variable_start_string='%%',
            variable_end_string='%%',
            comment_start_string='<#',
            comment_end_string='#>',
        )

        self.generate_all()

    def generate_all(self):
        self.generate_radio_constants()

    def generate_radio_constants(self):
        target_radio_constants_c = './lib/radio/radio_constants.c'
        self.create_folder(target_radio_constants_c)

        radio_constants_c = self.env.get_template('radio_constants.c')

        configurations = [({
                               'modem': config['modem'].c_name,
                               'bandwidth': config['bandwidth'],
                               'datarate': config['datarate'],
                               'coderate': config['coderate'],
                               'preamble_len': config['preamble_len'],
                           } if config['modem'] is RadioModem.LORA else
                           {
                               'modem': config['modem'].c_name,
                               'bandwidth': config['bandwidth'],
                               'datarate': config['datarate'],
                               'preamble_len': config['preamble_len'],
                               'fdev': config['fdev'],
                           }
                           ) for config in RADIO_CONFIGURATIONS]

        print(radio_constants_c.render(configurations=configurations, bands=BAND_FREQUENCIES, band_groups=BAND_GROUPS,
                                 bands_us915=BAND_FREQUENCIES_US915, band_groups_us915=BAND_GROUPS_US915))

    def create_folder(self, file):
        if not os.path.exists(os.path.join(self.path, os.path.dirname(file))):
            os.makedirs(os.path.join(self.path, os.path.dirname(file)))
