import base64
import os

from flora_tools.toolchain.platforms import Platform


class ELFConverter:
    def __init__(self, flora_path, platform: Platform):
        self.flora_path = flora_path
        self.platform = platform

    def convert(self):
        full_path = os.path.join(self.flora_path, Platform.get_firmware_path(self.platform))

        try:
            with open(full_path + ".elf", "rb") as elf_file:
                encoded_string = base64.b64encode(elf_file.read()).decode('ascii')
                encoded_string = self.insert_newlines(encoded_string)
                with open(full_path + ".base64", "w") as base64_file:
                    base64_file.write(encoded_string)
                    print("{} firmware file successfully converted to BASE64 and saved under {}".format(
                        self.platform, full_path + ".base64"))
        except FileNotFoundError:
            print("{} firmware file did not convert to BASE64 as it could not be found.".format(self.platform))

    @staticmethod
    def insert_newlines(string, every=128):
        return '\n'.join(string[i:i + every] for i in range(0, len(string), every))
