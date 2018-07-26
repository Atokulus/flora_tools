import socket
import time
from multiprocessing import Pool

import serial
import serial.tools.list_ports

FLOCKLAB = "flocklab.ethz.ch"
FLOCKLAB_SERIAL_PORT_BASE = 50100


class Node:
    def __init__(self, port=None, test=True, flocklab=False, id: int = None):
        self.flocklab = flocklab

        if self.flocklab:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(0.2)
            self.id = id

            self.open()

            if test:
                self.s.send(b"\x1b[3~\r\n")
                time.sleep(0.1)

            try:
                if b"flora" in self.s.recv(1024):
                    self.port = port
                    self.close()
                    print("Initialized flora node on FlockLab with target id {}".format(self.id))

                else:
                    self.close()
                    raise ValueError("FlockLab target ID {} is NOT a flora node with CLI".format(self.id))
            except socket.timeout:
                self.close()
                raise ValueError("FlockLab target ID {} is NOT responding".format(self.id))

        else:
            try:
                self.ser = serial.Serial(port=port.device, baudrate=115200, parity=serial.PARITY_NONE,
                                         stopbits=serial.STOPBITS_ONE, timeout=0.1)

                if test:
                    self.ser.write(b"\x1b[3~\r\n")
                    time.sleep(0.1)

                    if b"flora" in self.ser.read_all():
                        self.port = port
                        self.close()
                        print("Initialized flora node on serial port {}".format(port.device))

                    else:
                        self.close()
                        raise ValueError("Serial port {} is NOT a flora node with CLI".format(port.device))

            except serial.SerialException as e:
                print(e)
                raise ValueError("Serial port {} is NOT responding".format(port.device))

    def open(self):
        if self.flocklab:
            self.s.connect((FLOCKLAB, FLOCKLAB_SERIAL_PORT_BASE + self.id))
        else:
            self.ser.open()

    def close(self):
        if self.flocklab:
            self.s.close()
        else:
            self.ser.close()

    def reset(self):
        self.cmd("system reset")

    def cmd(self, command):
        if self.flocklab:
            self.s.send(bytes(command + "\r\n", encoding='ascii'))
        else:
            self.ser.write(bytes(command + "\r\n", encoding='ascii'))

    def flush(self):
        if self.flocklab:
            pass
        else:
            self.ser.flushInput()

    def query(self, command):
        self.flush()
        self.cmd(command)
        if self.flocklab:
            try:
                return self.s.recv(1000)
            except socket.timeout:
                return b''
        else:
            return self.ser.readlines()

    def delay_cmd_time(self, payload=0):
        time.sleep(0.1 + payload / 256.0 * 0.1)

    def interactive_mode(self, set=True):
        if set:
            self.cmd("interactive true")
        else:
            self.cmd("interactive false")

    @staticmethod
    def get_serial_port(name):
        ports = list(serial.tools.list_ports.grep(name))
        if len(ports):
            return ports[0]
        else:
            return None

    @staticmethod
    def get_serial_node(port):
        try:
            node = Node(port)
            return node
        except ValueError:
            return None

    @staticmethod
    def get_serial_all():
        ports = [port for port in serial.tools.list_ports.comports() if port[2] != 'n/a']

        if len(ports):
            with Pool(len(ports)) as p:
                nodes = [node for node in p.map(Node.get_serial_node, ports) if node is not None]
            if nodes:
                print("Flora nodes detected: {}".format([node.port.device for node in nodes]))
            else:
                print("NO flora ports detected!")
            return nodes
        else:
            print("NO flora ports detected!")
