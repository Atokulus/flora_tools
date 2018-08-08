import time

from flora_tools.experiments.measure_time_tx2sync import MeasureTimeTx2Sync
from flora_tools.node import Node
from flora_tools.oscilloscope import Oscilloscope

DEVKIT_A_PORT = "COM5"
DEVKIT_B_PORT = "COM12"
DEVKIT_C_PORT = "COM12"
DEVKIT_D_PORT = "COM5"

DEVKIT_PORTS = [
    DEVKIT_A_PORT,
    DEVKIT_B_PORT,
    DEVKIT_C_PORT,
    DEVKIT_D_PORT,
]


class TimingBench:
    def __init__(self, devkit_count=2):
        self.devkit_count = devkit_count
        self.devkits = []

    def __enter__(self, devkit_count=2):
        devkits = []
        for i in range(self.devkit_count):
            devkit = Node(Node.get_serial_port(DEVKIT_PORTS[i]))
            devkit.open()
            devkit.reset()
            devkit.cmd("led blink")
            time.sleep(0.3)
            devkits.append(devkit)

        self.devkits = devkits
        self.devkit_a = devkits[0]
        self.devkit_b = devkits[1]

        self.scope = Oscilloscope()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.scope.inst.close()


if __name__ == "__main__":
    with TimingBench(devkit_count=2) as bench:
        # TestSimultWriteSend().run(bench)
        # TestSniffMode().run(bench)
        # MeasureTimeTx2Rf().run(bench)
        MeasureTimeTx2Sync().run(bench)
        # MeasureTimeCAD2RxTimeout().run(bench)
        # MeasureTimeCAD2Done().run(bench)
        # MeasureTimeRx2Rf().run(bench)
        # MeasureTimeRx2RxTimeout().run(bench)
        # MeasureTimeTx2RxDone().run(bench)
        # MeasureTimeTx2TxDone().run(bench)
        # MeasureTimeTx2RxDoneImplicit().run(bench)
        # MeasureTimeTx2TxDoneImplicit().run(bench)
        # MeasureTimeSniffMode().run(bench)
        # MeasureTimeSleepMode().run(bench)
        # MeasureTimeConfig().run(bench)
        # MeasureTimeSetPayload().run(bench)
        # MeasureTimeGetPayload().run(bench)
        # MeasureTimeSetFS().run(bench)
        # MeasureTimeIRQProcess().run(bench)
        # MeasureTimeGetPktStatus().run(bench)
        # MeasureTimeSync().run(bench)
        # MeasureTimeSweepTxRx().run(bench)
        # MeasureTimeSweepTxTx().run(bench)
        # MeasureTimeSetCAD().run(bench)
