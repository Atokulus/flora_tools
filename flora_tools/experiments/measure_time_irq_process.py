from flora_tools.experiment import *


class MeasureTimeIRQProcess(Experiment):
    def __init__(self):

        description = "Measures the time needed for an IRQ to be processed."

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'react', 'finish']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):

            configuration = RadioConfiguration.get_random_configuration(tx=False, irq_direct=True)
            self.bench.devkit_a.cmd(configuration.cmd)

            math = RadioMath(configuration)
            min_window = 0.0001
            min_precision = 5E-6
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)

            time.sleep(0.01)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="DIO1", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_a.cmd("radio send")

            wave = self.bench.scope.finish_measurement(channels=[1, 2])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                dio1_indices = utilities.get_edges(wave[1])

                if 3 < len(nss_indices) < 100:
                    nss_react = nss_indices[0][0]
                    nss_finish = nss_indices[3][0]
                else:
                    nss_react = np.nan
                    nss_finish = np.nan

                if 1 < len(dio1_indices) < 100:
                    dio1_rise = dio1_indices[0][0]
                    delay_react = (nss_react - dio1_rise) * self.bench.scope.sample_period
                    delay_finish = (nss_finish - dio1_rise) * self.bench.scope.sample_period
                else:
                    delay_react = np.nan
                    delay_finish = np.nan

                item = [dt.datetime.now(), window, self.bench.scope.sample_period, configuration.modulation,
                        configuration.band, delay_react, delay_finish]
            else:
                item = [dt.datetime.now(), window, self.bench.scope.sample_period, configuration.modulation,
                        configuration.band, np.nan, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df: pd.DataFrame):
        df.dropna()

        delay_react = df.react
        delay_finish = df.finish

        columns = ['delay_react', 'delay_react_err', 'delay_finish', 'delay_finish_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay_react.mean(), delay_react.std(), delay_finish.mean(), delay_finish.std()]

        return timings
