import os
import time

from intelhex import hex2bin
import serial

from flora_tools.toolchain.bootloader import Bootloader
from flora_tools.toolchain.platforms import *
from flora_tools.stm32loader.stm32loader import Stm32Bootloader, Stm32Loader

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

        self.loader = Stm32Loader()
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

        self.loader.bootloader = Stm32Bootloader()
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
        finally:
            pass

    @staticmethod
    def program_on_bootloader(arguments):
        programmer = Programmer(arguments['flora_path'], arguments['bootloader'])
        programmer.program()

    @staticmethod
    def program_device(firmware_path, port):
        filename, file_extension = os.path.splitext(firmware_path)
        if file_extension is '.hex':
            hex2bin(firmware_path,
                    filename + '.binary')
            firmware_path = filename + '.binary'


        ser = serial.Serial(port=port, baudrate=115200, parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE, timeout=0.1)
        ser.write(b"system bootloader\r\n")
        time.sleep(0.1)

        loader = Stm32Loader()
        loader.configuration['data_file'] = firmware_path
        loader.configuration['port'] = port
        loader.configuration['erase'] = True
        loader.configuration['write'] = True
        loader.configuration['verify'] = True
        loader.configuration['go_address'] = 0x08000000
        loader.configuration['baud'] = 115200

        loader.connect()
        loader.perform_commands()
        loader.reset()


