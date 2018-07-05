import os

from intelhex import hex2bin

from flora_tools.toolchain.bootloader import Bootloader
from flora_tools.toolchain.platforms import *

class Programmer:
    def __init__(self, flora_path, bootloader: Bootloader):
        self.flora_path = flora_path
        self.bootloader = bootloader

    def program(self):
        if not os.path.isfile(os.path.join(self.flora_path, DEVKIT_FIRMWARE_PATH + '.binary')):
            hex2bin(os.path.join(self.flora_path, DEVKIT_FIRMWARE_PATH + '.hex'),
                os.path.join(self.flora_path, DEVKIT_FIRMWARE_PATH + '.binary'))

        if not os.path.isfile(os.path.join(self.flora_path, COMBOARD_FIRMWARE_PATH + '.binary')):
            hex2bin(os.path.join(self.flora_path, COMBOARD_FIRMWARE_PATH + '.hex'),
                    os.path.join(self.flora_path, COMBOARD_FIRMWARE_PATH + '.binary'))

        self.loader = stm32loader.stm32loader.Stm32Loader()
        self.loader.configuration['data_file'] = DEVKIT_FIRMWARE_PATH
        self.loader.configuration['port'] = self.bootloader.port.device
        # self.loader.configuration['family'] = "F4"
        self.loader.configuration['erase'] = True
        self.loader.configuration['write'] = True
        self.loader.configuration['verify'] = True
        self.loader.configuration['go_address'] = 0x08000000
        self.loader.configuration['baud'] = 115200

        # self.loader.connect()
        # Connecting manually, as a reset like in self.loader.connect() would not work on DevKit or ComBoard

        self.loader.bootloader = stm32loader.stm32loader.Stm32Bootloader()
        self.loader.bootloader.open(
            self.loader.configuration['port'],
            self.loader.configuration['baud'],
            self.loader.configuration['parity'],
        )

        try:
            self.loader.bootloader.reset_from_system_memory()
        except Exception:
            print("Can't init. Ensure that BOOT0 is enabled and reset device")
            self.loader.bootloader.reset_from_flash()
            return

        try:
            device_id = self.loader.bootloader.get_id()
            self.loader.read_device_details()

            if device_id == 0x415:
                print("{} is DevKit.".format(self.bootloader.port.device))
                self.loader.configuration['data_file'] = os.path.join(self.flora_path, DEVKIT_FIRMWARE_PATH + '.binary')
            elif device_id == 0x435:
                print("{} is ComBoard.".format(self.bootloader.port.device))
                self.loader.configuration['data_file'] = os.path.join(self.flora_path, COMBOARD_FIRMWARE_PATH + '.binary')

            self.loader.perform_commands()

            if device_id == 0x435:
                self.loader.reset()
                # self.loader.bootloader.serial.setRTS(False)  # Boot0 Pin reset
                # time.sleep(0.1)
                # self.loader.bootloader.serial.setDTR(True)  # Reset low active set
                # time.sleep(0.1)
                # self.loader.bootloader.serial.setDTR(False)  # Reset release
        finally:
            pass

    @staticmethod
    def program_on_bootloader(arguments):
        programmer = Programmer(arguments['flora_path'], arguments['bootloader'])
        programmer.program()

