import time
from multiprocessing import Pool

import serial
import serial.tools.list_ports


class Node:
    def __init__(self, port, test=True):
        try:
            self.ser = serial.Serial(port=port.device, baudrate=115200, parity=serial.PARITY_NONE,
                                     stopbits=serial.STOPBITS_ONE, timeout=0.1)

            if test:
                self.ser.write(b"\x1b[3~\r\n")
                time.sleep(0.1)

                if (b"flora" in self.ser.read_all()):
                    self.port = port
                    self.close()
                    print("Initialized flora node on port {}".format(port.device))

                else:
                    self.close()
                    raise ValueError("Port {} is NOT a flora node with CLI".format(port.device))

        except serial.SerialException as e:
            print(e)
            raise ValueError("Port {} is NOT a flora node".format(port.device))

    def open(self):
        self.ser.open()

    def close(self):
        self.ser.close()

    def reset(self):
        self.cmd("system reset")

    def cmd(self, command):
        self.ser.write(bytes(command + "\r\n", encoding='ascii'))

    def flush(self):
        self.ser.flushInput()

    def query(self, command):
        self.flush()
        self.cmd(command)
        return self.ser.readlines()

    def query(self, command):
        self.flush()
        self.cmd(command)
        return self.ser.readlines()

    def delay_cmd_time(self, payload=0):
        time.sleep(0.1 + payload / 256.0 * 0.1)

    @staticmethod
    def get_port(name):
        ports = list(serial.tools.list_ports.grep(name))
        if len(ports):
            return ports[0]
        else:
            return None

    @staticmethod
    def get_node(port):
        try:
            node = Node(port)
            return node
        except ValueError:
            return None

    @staticmethod
    def get_all():
        ports = [port for port in serial.tools.list_ports.comports() if port[2] != 'n/a']

        if len(ports):
            with Pool(len(ports)) as p:
                nodes = [node for node in p.map(Node.get_node, ports) if node is not None]
            if nodes:
                print("Flora nodes detected: {}".format([node.port.device for node in nodes]))
            else:
                print("NO flora ports detected!")
            return nodes
        else:
            print("NO flora ports detected!")
