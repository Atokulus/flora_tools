from flora_tools.node import Node
from flora_tools.oscilloscope import Oscilloscope
import time

from flora_tools.experiments.test_simult_write_send import  TestSimultWriteSend
from flora_tools.experiments.measure_time_tx2rf import MeasureTimeTx2Rf
from flora_tools.experiments.test_sniff_mode import TestSniffMode
from flora_tools.experiments.measure_time_tx2sync import MeasureTimeTx2Sync
from flora_tools.experiments.measure_time_cad2done import MeasureTimeCAD2Done
from flora_tools.experiments.measure_time_tx2txdone import MeasureTimeTx2TxDone
from flora_tools.experiments.measure_time_cad2rxtimeout import MeasureTimeCAD2RxTimeout
from flora_tools.experiments.measure_time_rx2rf import MeasureTimeRx2Rf
from flora_tools.experiments.measure_time_rx2rxtimeout import MeasureTimeRx2RxTimeout
from flora_tools.experiments.measure_time_tx2rxdone import MeasureTimeTx2RxDone
from flora_tools.experiments.measure_time_tx2rxdone_implicit import MeasureTimeTx2RxDoneImplicit
from flora_tools.experiments.measure_time_tx2txdone_implicit import MeasureTimeTx2TxDoneImplicit
from flora_tools.experiments.measure_time_sniff_mode import MeasureTimeSniffMode
from flora_tools.experiments.measure_time_sleep_mode import MeasureTimeSleepMode
from flora_tools.experiments.measure_time_config import MeasureTimeConfig
from flora_tools.experiments.measure_time_set_payload import MeasureTimeSetPayload
from flora_tools.experiments.measure_time_get_payload import MeasureTimeGetPayload
from flora_tools.experiments.measure_time_set_fs import MeasureTimeSetFS
from flora_tools.experiments.measure_time_irq_process import MeasureTimeIRQProcess
from flora_tools.experiments.measure_time_get_pkt_status import MeasureTimeGetPktStatus
from flora_tools.experiments.measure_time_sync import MeasureTimeSync
from flora_tools.experiments.measure_time_sweep_tx_rx import MeasureTimeSweepTxRx
from flora_tools.experiments.measure_time_sweep_tx_tx import MeasureTimeSweepTxTx
from flora_tools.experiments.measure_time_set_cad import MeasureTimeSetCAD

DEVKIT_A_PORT = "COM17"
DEVKIT_B_PORT = "COM4"
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
            devkit = Node(Node.get_port(DEVKIT_PORTS[i]))
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
        #TestSimultWriteSend().run(bench)
        #TestSniffMode().run(bench)
        #MeasureTimeTx2Rf().run(bench)
        MeasureTimeTx2Sync().run(bench)
        #MeasureTimeCAD2RxTimeout().run(bench)
        #MeasureTimeCAD2Done().run(bench)
        #MeasureTimeRx2Rf().run(bench)
        #MeasureTimeRx2RxTimeout().run(bench)
        #MeasureTimeTx2RxDone().run(bench)
        #MeasureTimeTx2TxDone().run(bench)
        #MeasureTimeTx2RxDoneImplicit().run(bench)
        #MeasureTimeTx2TxDoneImplicit().run(bench)
        #MeasureTimeSniffMode().run(bench)
        #MeasureTimeSleepMode().run(bench)
        #MeasureTimeConfig().run(bench)
        #MeasureTimeSetPayload().run(bench)
        #MeasureTimeGetPayload().run(bench)
        #MeasureTimeSetFS().run(bench)
        #MeasureTimeIRQProcess().run(bench)
        #MeasureTimeGetPktStatus().run(bench)
        #MeasureTimeSync().run(bench)
        #MeasureTimeSweepTxRx().run(bench)
        #MeasureTimeSweepTxTx().run(bench)
        #MeasureTimeSetCAD().run(bench)














