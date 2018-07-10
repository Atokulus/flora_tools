from flora_tools.experiment import *


class MeasureTimeCAD2RxTimeout(Experiment):
    def __init__(self):
        description = "Measures the time needed from setCAD() (NSS going low for SPI, as it cannot be timed with NSS high) " \
                      "to triggered RX_TIMEOUT_IRQ on receiver side"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=1000):
        self.iterations = iterations

        Experiment.run(self, bench)

        # self.bench.scope.set_scale("COAX", 0.2)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'cad2timeout']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration(limit="LoRa")
            # configuration = RadioConfiguration(6, 0, 0)
            configuration.tx = False

            configuration_tx = copy(configuration)
            configuration_tx.tx = True

            math = RadioMath(configuration)
            min_window = (math.get_preamble_time()) * 3.0 * 2.0
            min_precision = 0.1E-6
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)
            start = int(points * 0.4)

            self.bench.devkit_a.cmd(configuration.cmd)
            self.bench.devkit_b.cmd(configuration_tx.cmd)
            self.bench.devkit_b.cmd("radio preamble")

            self.bench.scope.init_measurement(window, trigger_rise=True,
                                              trigger_channel="NSS",
                                              points=points,
                                              start=start,
                                              text=("{}:{}".format(self.name, configuration)))
            self.bench.scope.delay_acquisition_setup_time(window)

            self.bench.devkit_a.cmd("radio cad rx")

            wave = self.bench.scope.finish_measurement(channels=[1, 2, 3])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                if (len(nss_indices) > 0):
                    setcad_time = nss_indices[4][0]
                else:
                    setcad_time = np.nan

                dio1_indices = utilities.get_edges(wave[1])
                if len(dio1_indices) > 0 and len(dio1_indices) < 5:
                    cad2rxtimeout = (dio1_indices[0][0] - setcad_time) * self.bench.scope.sample_period
                else:
                    cad2rxtimeout = np.nan

                if cad2rxtimeout < 0:
                    cad2rxtimeout = np.nan

                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band,
                        cad2rxtimeout]
            else:
                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band, np.nan]

            df.loc[i] = item
            df.to_csv("{}.csv".format(self.name))
            print(item)

    def analyze(self, df):
        pass
