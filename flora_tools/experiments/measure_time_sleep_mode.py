from flora_tools.experiment import *


class MeasureTimeSleepMode(Experiment):
    def __init__(self):

        description = "Measures the time needed for entering and leaving sleep mode"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'delay', 'sleep', 'wakeup']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        points = 100000
        window = 0.4
        sample_period = window / (points - 1)

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration(tx='randomize') # Does not work for FSK (random glitches on BUSY line)
            self.bench.devkit_a.cmd(configuration.cmd)
            self.bench.devkit_a.delay_cmd_time()

            random_delay = np.random.uniform(0.0, 0.2)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_a.cmd("radio sleep")
            time.sleep(random_delay)
            self.bench.devkit_a.cmd("radio standby")

            wave = self.bench.scope.finish_measurement(channels=[1,3])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                busy_indices = utilities.get_edges(wave[1])

                if 3 <= len(nss_indices) < 100:
                    nss_sleep = nss_indices[0][0]
                    nss_wakeup = nss_indices[2][0]
                else:
                    nss_sleep = np.nan
                    nss_wakeup = np.nan

                if 3 <= len(busy_indices) < 100:
                    sleep_delay = (busy_indices[0][0] - nss_sleep) * self.bench.scope.sample_period
                    wakeup_delay = (busy_indices[3][0] - nss_wakeup) * self.bench.scope.sample_period
                else:
                    sleep_delay = np.nan
                    wakeup_delay = np.nan

                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, random_delay, sleep_delay, wakeup_delay]
            else:
                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, sleep_delay, np.nan, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df : pd.DataFrame):
        df.dropna()

        columns = ['sleep', 'sleep_err', 'wakeup', 'wakeup_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [df.sleep.mean(), df.sleep.std(), df.wakeup.mean(), df.wakeup.std()]

        return timings