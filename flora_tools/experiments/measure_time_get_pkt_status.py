from flora_tools.experiment import *


class MeasureTimeGetPktStatus(Experiment):
    def __init__(self):

        description = "Measures the time needed to read the radio's packet status."

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'measured']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        points = 100000
        window = 0.0001
        sample_period = window / (points - 1)

        self.bench.scope.set_scale("COAX", 0.2)

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration(tx='randomize') # Does not work for FSK (random glitches on BUSY line)
            self.bench.devkit_a.cmd("radio standby")
            self.bench.devkit_a.cmd(configuration.cmd)

            self.bench.scope.init_measurement(window, trigger_rise=False, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            boost = np.random.choice([True, False])

            self.bench.devkit_a.cmd("radio status")

            wave = self.bench.scope.finish_measurement(channels=[1])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])

                if 0 < len(nss_indices) < 100:
                    nss_start = nss_indices[0][0]
                    delay = (nss_indices[-1][0] - nss_start) * self.bench.scope.sample_period
                else:
                    delay = np.nan

                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, delay]
            else:
                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df : pd.DataFrame):
        df.dropna()
        
        delay = df.measured

        columns = ['delay', 'delay_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay.mean(), delay.std()]

        delay = df.measured

        columns = ['delay', 'delay_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay.mean(), delay.std()]

        return timings