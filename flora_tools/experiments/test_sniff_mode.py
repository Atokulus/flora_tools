from flora_tools.experiment import *


class TestSniffMode(Experiment):
    def __init__(self):

        description = "Tests whether sniff mode directly goes into sleep or first into receive"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=1):
        self.iterations = iterations
        Experiment.run(self, bench)

        points = 20000000
        window = 1.0
        sample_period = window / (points - 1)

        configuration = RadioConfiguration(5,48,10)
        self.bench.devkit_a.cmd(configuration.cmd)
        self.bench.devkit_b.cmd(configuration.cmd)

        self.bench.scope.set_scale("COAX", 0.2)

        for i in range(0, self.iterations):
            self.bench.devkit_a.cmd("radio receive 2 2 -s")
            self.bench.devkit_a.delay_cmd_time()

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_a.cmd("radio execute")
            time.sleep(2)
