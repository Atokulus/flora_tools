import time
from multiprocessing import Pool

import serial
import serial.tools.list_ports

from flora_tools.node import Node


class Bootloader:
    def __init__(self, port):
        try:
            self.node = Node(port, test=False)
            if self.node:
                self.node.ser.write(b"system bootloader\r\n")
                self.node.close()
                time.sleep(0.2)

            self.port = port

        except serial.SerialException as e:
            print(e)
            raise ValueError("Port {} is NOT a valid COM Port.".format(port.device))

    @staticmethod
    def get_bootloader(port):
        try:
            bootloader = Bootloader(port)
            return bootloader
        except ValueError:
            return None

    @staticmethod
    def get_all():
        ports = [port for port in serial.tools.list_ports.comports() if port[2] != 'n/a']
        serial.tools.list_ports.comports()[0]

        if len(ports):
            with Pool(len(ports)) as p:
                bootloaders = [bootloader for bootloader in p.map(Bootloader.get_bootloader, ports) if
                               bootloader is not None]
            if bootloaders:
                print("Flora bootloaders detected: {}".format([bootloader.port.device for bootloader in bootloaders]))
            else:
                print("NO flora bootloaders detected!")
            return bootloaders
        else:
            print("NO flora bootloaders detected!")
