from flora_tools.experiment import *


class MeasureTimeRx2Rf(Experiment):
    def __init__(self):
        description = "Measures the time needed from the execution moment of setRx() command (NSS going high) " \
                      "to the falling edge of BUSY"

        Experiment.__init__(self, description)

    def run(self, bench: Oscilloscope, iterations=10000):
        self.iterations = iterations

        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'rx2rf']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        min_window = 100E-6 * 1.1 * 2.0
        min_precision = 0.01E-6
        window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)
        start = int(points * 0.4)

        self.bench.scope.set_scale("COAX", 0.2)

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration()
            configuration.tx = False

            self.bench.devkit_a.cmd(configuration.cmd)

            self.bench.devkit_a.cmd("radio receive -s")
            self.bench.devkit_a.delay_cmd_time()

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points, start=start)
            self.bench.scope.delay_acquisition_setup_time(window=window)
            self.bench.devkit_a.cmd("radio execute")

            wave = self.bench.scope.finish_measurement(channels=[1,3])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                if (len(nss_indices) > 0 and len(nss_indices) < 10):
                    nss_time = nss_indices[0][0]
                else:
                    nss_time = np.nan

                busy_indices = utilities.get_edges(wave[1])
                if (len(busy_indices) >= 2):
                    rx2rf_time = (busy_indices[1][0] - nss_time) * self.bench.scope.sample_period
                else:
                    rx2rf_time = np.nan

                if rx2rf_time < 0:
                    rx2rf_time = np.nan

                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band, rx2rf_time]
            else:
                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band, np.nan]
            df.loc[i] = item
            print(item)

            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df):
        with plt.style.context("bmh"):
            df = df.dropna()

            colors = df.modulation.map(RadioConfiguration.get_color)

            plt.scatter(df.band, df.rx2rf * 1E6, c=colors)

            ax = plt.gca()

            ax.set_xlabel('Band')
            ax.set_ylabel('Rx2Rf Delay [µs]')

            plt.show()

            mods = df.modulation.sort_values().unique();

            columns = ['modulation_name', 'sample_count', 'rx2rf', 'rx2rf_err']
            mod_delays = pd.DataFrame(columns=columns)
            mod_delays.index.name = 'modulation'

            for i in mods:
                config = RadioConfiguration(i)
                subset = df[df.modulation == i]
                mod_delays.loc[i] = [config.modulation_name, len(subset['rx2rf']), subset['rx2rf'].mean(), subset['rx2rf'].std()]

            bands = df.band.sort_values().unique();
            columns = ['sample_count', 'rx2rf', 'rx2rf_err']
            band_delays = pd.DataFrame(columns=columns)
            band_delays.index.name = 'band'

            for i in bands:
                subset = df[df.band == i]
                band_delays.loc[i] = [len(subset['rx2rf']), subset['rx2rf'].mean(), subset['rx2rf'].std()]

            return mod_delays, band_delays











