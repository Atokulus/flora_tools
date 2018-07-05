import serial
import serial.tools.list_ports
import time

from multiprocessing import Pool

from flora_tools.node import Node


class Bootloader:
    def __init__(self, port):
        try:
            try:
                self.node = Node(port, test=False)
                if self.node:
                    self.node.ser.write(b"system bootloader\r\n")
                    self.node.close()
                    time.sleep(0.2)
            except ValueError:
                print("Failed to interface with potential flora CLI at {}".format(port.device))
                pass

            self.port = port

            #ser = serial.Serial(port=port.device, baudrate=115200, parity=serial.PARITY_EVEN,
            #                    stopbits=serial.STOPBITS_ONE, timeout=0.5)

            # ser.setRTS(False) # Boot0 Pin set
            # time.sleep(0.1)
            # ser.setDTR(True) # Reset low active set
            # time.sleep(0.1)
            # ser.setDTR(False) # Reset release
            # time.sleep(0.1)
            #
            # ser.write(b"\x7f")
            # time.sleep(0.2)
            # ack = ser.read()
            # if ack == b"\x79":
            #     print("Enabled UART bootloader on {}".format(port.device))
            #
            # ser.write(b"\x00\xff")
            # time.sleep(0.1)
            # ack = ser.read()
            # if ack == b"\x79":
            #     print("Verified UART bootloader on {}".format(port.device))
            #     ser.close()
            #     self.port = port
            # else:
            #     ser.close()
            #     raise ValueError("Port {} is NOT a flora bootloader.".format(port.device))
        except serial.SerialException as e:
            print(e)
            raise ValueError("Port {} is NOT a flora bootloader.".format(port.device))

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
                bootloaders = [bootloader for bootloader in p.map(Bootloader.get_bootloader, ports) if bootloader is not None]
            if bootloaders:
                print("Flora bootloaders detected: {}".format([bootloader.port.device for bootloader in bootloaders]))
            else:
                print("NO flora bootloaders detected!")
            return bootloaders
        else:
            print("NO flora bootloaders detected!")