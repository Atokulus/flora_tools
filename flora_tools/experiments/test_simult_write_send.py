from flora_tools.experiment import *


class TestSimultWriteSend(Experiment):
    def __init__(self):
        description = "Tests whether it is possible to write to buffer while sending/transmitting another message on the same radio." \
                      "The buffer is then sent as a separate message."

        Experiment.__init__(self, description)

    def run(self, bench, iterations=1):
        self.iterations = iterations
        Experiment.run(self, bench)

        points = 10000000
        window = 0.5
        sample_period = window / (points - 1)

        configuration = RadioConfiguration(5, 48, 10)
        configuration_rx = copy(configuration)
        configuration_rx.tx = False
        self.bench.devkit_a.cmd(configuration.cmd)
        self.bench.devkit_b.cmd(configuration_rx.cmd)
        self.bench.devkit_b.cmd("radio receive")
        self.bench.devkit_b.close()

        self.bench.scope.set_scale("COAX", 0.2)

        for i in range(0, self.iterations):
            text1 = "'Blub Blub'"
            self.bench.devkit_a.cmd("radio send " + text1 + " -s")
            self.bench.devkit_a.delay_cmd_time(len(text1))

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time()

            self.bench.devkit_a.cmd("radio execute")

            text2 = "'Lorem ipsum dolor sit amet, consetetur sadipscing elitr. Hi you! What*s up? How is it going?'"

            self.bench.devkit_a.cmd("radio payload " + text2 + " t")
            time.sleep(0.5)
            self.bench.devkit_a.cmd("radio send")

            time.sleep(2)
