from flora_tools.experiment import *


class MeasureTimeRx2RxTimeout(Experiment):
    def __init__(self):
        description = "Measures the time needed from a executed setRx() command (BUSY going high) " \
                      "to the Rx Timeout IRQ (DIO1 rising edge)"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations

        Experiment.run(self, bench)

        self.bench.scope.set_scale("COAX", 0.2)

        columns = ['time', 'window', 'precision', 'modulation', 'rx2rxtimeout']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration()
            #configuration = RadioConfiguration(0, 0, 0)
            configuration.tx = False

            self.bench.devkit_a.cmd(configuration.cmd)

            math = RadioMath(configuration)
            min_window = math.sync_time * 1.2 * 2.0
            min_precision = 1E-6
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)
            start = int(points * 0.4)

            self.bench.devkit_a.cmd("radio receive -s")
            self.bench.devkit_a.delay_cmd_time()

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window)
            self.bench.devkit_a.cmd("radio execute")

            wave = self.bench.scope.finish_measurement(channels=[1,2])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                if (len(nss_indices) > 0 and len(nss_indices) < 10):
                    nss_time = nss_indices[0][0]
                else:
                    nss_time = np.nan

                dio1_indices = utilities.get_edges(wave[1])
                if (len(dio1_indices) > 0 and len(dio1_indices) < 10):
                    rx2rxtimeout_time = (dio1_indices[0][0] - nss_time) * self.bench.scope.sample_period
                else:
                    rx2rxtimeout_time = np.nan

                if rx2rxtimeout_time < 0:
                    rx2rxtimeout_time = np.nan

                item = [dt.datetime.now(), window, precision, configuration.modulation, rx2rxtimeout_time]
            else:
                item = [dt.datetime.now(), window, precision, configuration.modulation, np.nan]

            df.loc[i] = item
            df.to_csv("{}.csv".format(self.name))
            print(item)

    def analyze(self, df):
        with plt.style.context("bmh"):
            df = df.dropna()

            mods = df.modulation.sort_values().unique();

            columns = ['modulation_name', 'sample_count', 'rx2rxtimeout_ref', 'rx2rxtimeout', 'rx2rxtimeout_err']
            delays = pd.DataFrame(columns=columns)
            delays.index.name = 'modulation'

            for i in mods:
                subset = df[df.modulation == i]

                config = RadioConfiguration(i)
                math = RadioMath(config)

                weights = np.ones(len(subset['rx2rxtimeout'])) * 1 / len(subset['rx2rxtimeout']) * 1E3
                n, bins, patches = plt.hist(subset['rx2rxtimeout'] * 1E3, 100, weights=weights, color=config.color)

                plt.title('Rx to Rx Timeout IRQ Delay for {}\n'.format(config.modulation_name) + '$\mu = ' + str(
                    subset['rx2rxtimeout'].mean() * 1E3) + '\ \mathrm{ms},\ \sigma = {' + str(
                    subset['rx2rxtimeout'].std() * 1E6) + '}$ µs')
                plt.xlabel('Delay [ms]')
                plt.ylabel('Probability [‰]')
                plt.show()

                delays.loc[i] = [config.modulation_name, len(subset['rx2rxtimeout']), math.get_preamble_time(), subset['rx2rxtimeout'].mean(), subset['rx2rxtimeout'].std()]

            plt.figure(figsize=(14, 5))
            plt.subplot(121)

            plt.title("Rx to Rx Timeout average delay")
            ax = plt.gca()
            rects = plt.bar(mods - 0.2, delays.loc[:, 'rx2rxtimeout'], width=0.4, log=True)
            ref_rects = plt.bar(mods + 0.2, delays.loc[:, 'rx2rxtimeout_ref'], width=0.4, log=True)
            for i, rect in zip(mods, rects):
                rect.set_fc(RadioConfiguration(i).color)
                height = rect.get_height()
                ax.text(rect.get_x() + rect.get_width() / 2., 1.02 * height,
                        "{:.2E}".format(delays.loc[i, 'rx2rxtimeout']),
                        ha='center', va='bottom')

            rect = ref_rects[0]
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    ax.get_ylim()[0] + np.power(10, np.average(np.log10([ax.get_ylim()[0], rect.get_height()]))),
                    "preamble time-on-air reference",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)
            plt.ylabel('$\mu$ [s]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            plt.subplot(122)

            plt.title("Rx to Rx Timeout Delay standard deviation")
            ax = plt.gca()
            rects = plt.bar(mods, delays.loc[:, 'rx2rxtimeout_err'] * 1E6)
            for i, rect in zip(mods, rects):
                rect.set_fc(RadioConfiguration(i).color)
                height = rect.get_height()
                if not np.isnan(height):
                    ax.text(rect.get_x() + rect.get_width() / 2., 1.01 * height,
                            "{:.2E}".format(delays.loc[i, 'rx2rxtimeout_err']),
                            ha='center', va='bottom')
            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)
            plt.ylabel('$\sigma$ [µs]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            plt.show()

            return delays

