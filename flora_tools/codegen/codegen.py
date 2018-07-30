from jinja2 import Environment, PackageLoader, select_autoescape


class CodeGen:
    def __init__(self, path):
        self.path = path
        self.env = Environment(
            loader=PackageLoader('flora_tools', 'templates'),
        )

        self.generate_all()

    def generate_all(self):
        self.generate_radio_constants()

    def generate_radio_constants(self):

        radio_constants_h = self.env.get_template('radio_constants.h')
        radio_constants_c = self.env.get_template('radio_constants.c')


