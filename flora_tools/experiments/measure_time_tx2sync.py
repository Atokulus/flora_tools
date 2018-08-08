from flora_tools.experiment import *


class MeasureTimeTx2Sync(Experiment):
    def __init__(self):
        description = "Measures the time needed from the execution moment of setTx() (NSS going high) " \
                      "to the detection of IRQ_HEADER_VALID on receiver side"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=50000):
        self.iterations = iterations

        Experiment.run(self, bench)

        self.bench.scope.set_scale("COAX", 0.2)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'power', 'payload', 'measured']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            self.bench.devkit_a.cmd('system reset')
            self.bench.devkit_b.cmd('system reset')
            time.sleep(0.3)

            configuration = RadioConfiguration.get_random_configuration(modulation_range=[3,5,7,9])
            configuration_rx = copy(configuration)
            configuration_rx.tx = False

            math = RadioMath(configuration)
            min_window = (math.sync_time + 126e-6) * 1.3
            min_precision = 0.2E-6
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)
            start = 0

            self.bench.devkit_a.cmd(configuration.cmd)
            self.bench.devkit_b.cmd(configuration_rx.cmd)

            self.bench.devkit_b.cmd("radio receive")

            text = utilities.get_random_text(max_length=20)
            if text is not None:
                text_len = (len(text) + 1)
            else:
                text_len = 0

            if text is not None:
                self.bench.devkit_a.cmd("radio send '" + text + "' -s")
            else:
                self.bench.devkit_a.cmd("radio send -s")

            self.bench.devkit_a.delay_cmd_time(text_len)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points,
                                              start=start, text=("{}:{}".format(self.name, configuration)))
            self.bench.scope.delay_acquisition_setup_time(window)
            self.bench.devkit_a.cmd("radio execute")

            wave = self.bench.scope.finish_measurement(channels=[1, 2])

            if wave is not None:
                nss_min = np.amin(wave[0])
                nss_max = np.amax(wave[0])
                nss_digital = np.digitize(wave[0], [(nss_min + nss_max) / 2.0])
                nss_diff = np.diff(nss_digital)
                nss_indices = np.argwhere(nss_diff)
                if len(nss_indices) > 0:
                    txex2headervalid_time = nss_indices[0][0]
                else:
                    txex2headervalid_time = np.nan

                dio1_min = np.amin(wave[1])
                dio1_max = np.amax(wave[1])
                dio1_digital = np.digitize(wave[1], [(dio1_min + dio1_max) / 2.0])
                dio1_diff = np.diff(dio1_digital)
                dio1_indices = np.argwhere(dio1_diff)
                if 0 < len(dio1_indices) < 5:
                    txex2headervalid_time = (dio1_indices[0][
                                                 0] - txex2headervalid_time) * self.bench.scope.sample_period
                else:
                    txex2headervalid_time = np.nan

                if txex2headervalid_time < 0:
                    txex2headervalid_time = np.nan

                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band,
                        configuration.power, text_len, txex2headervalid_time]
            else:
                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band,
                        configuration.power, text_len, np.nan]

            df.loc[i] = item
            df.to_csv("{}.csv".format(self.name))

            print(item)

    def analyze(self, df):
        with plt.style.context("bmh"):
            df = df.dropna()

            mods = df.modulation.sort_values().unique()

            columns = ['modulation_name', 'sample_count', 'txex2sync', 'sync2irq', 'total', 'total_err']
            delays = pd.DataFrame(columns=columns)
            delays.index.name = 'modulation'

            for i in mods:
                subset = df[df.modulation == i]

                config = RadioConfiguration(i, 48, 0)
                math = RadioMath(config)

                weights = np.ones(len(subset['measured'])) * 1 / len(subset['measured']) * 1E3
                n, bins, patches = plt.hist(subset['measured'] * 1E3, 100, weights=weights, color=config.color)

                plt.title('Tx to header/sync IRQ delay for {}\n'.format(config.modulation_name) + '$\mu = ' + str(
                    subset['measured'].mean() * 1E3) + '\ \mathrm{ms},\ \sigma = {' + str(
                    subset['measured'].std() * 1E6) + '}$ µs')
                plt.xlabel('Delay [ms]')
                plt.ylabel('Probability [‰]')
                plt.show()

                delays.loc[i] = [config.modulation_name, len(subset['measured']), math.sync_time,
                                 subset['measured'].mean() - math.sync_time, subset['measured'].mean(),
                                 subset['measured'].std()]

            plt.figure(figsize=(14, 5))

            plt.subplot(121)

            plt.title("Tx to header/sync IRQ average delay")
            ax = plt.gca()
            rects = plt.bar(mods - 0.2, delays.loc[:, 'total'], width=0.4, log=True)
            ref_rects = plt.bar(mods + 0.2, delays.loc[:, 'txex2sync'], width=0.4, log=True)
            for i, rect in zip(mods, rects):
                rect.set_fc(RadioConfiguration(i).color)
                height = rect.get_height()
                ax.text(rect.get_x() + rect.get_width() / 2., 1.02 * height,
                        "{:.2E}".format(delays.loc[i, 'total']),
                        ha='center', va='bottom')

            rect = ref_rects[0]
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    ax.get_ylim()[0] + np.power(10, np.average(np.log10([ax.get_ylim()[0], rect.get_height()]))),
                    "sync delay time-on-air reference",
                    rotation=90,
                    ha='center', va='center',
                    color='white')
            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)

            plt.ylabel('$\mu$ [s]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            plt.subplot(122)

            plt.title("standard deviation")
            ax = plt.gca()
            rects = plt.bar(mods, delays.loc[:, 'total_err'] * 1E6)
            for i, rect in zip(mods, rects):
                rect.set_fc(RadioConfiguration(i).color)
                height = rect.get_height()
                if not np.isnan(height):
                    ax.text(rect.get_x() + rect.get_width() / 2., 1.01 * height,
                            "{:.2E}".format(delays.loc[i, 'total_err']),
                            ha='center', va='bottom')

            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)

            plt.ylabel('$\sigma$ [µs]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            plt.show()

            plt.figure(figsize=(14, 5))
            plt.subplot(121)

            colors = df.modulation.map(RadioConfiguration.get_color)

            def get_relative_error(item):
                error = (item['measured'] - delays.loc[item['modulation'], 'total']) / delays.loc[
                    item['modulation'], 'total_err']
                return error

            errors = df.apply(get_relative_error, axis=1)
            plt.scatter(df.power, errors, c=colors)
            plt.title("Tx2Sync vs. Power Configurations")
            ax = plt.gca()
            ax.set_xlabel('Power [dBm]')
            ax.set_ylabel('Relative Tx2Sync Delay')

            plt.subplot(122)

            plt.scatter(df.band, errors, c=colors)
            plt.title("Relative Tx2Sync vs. Band Configurations")
            ax = plt.gca()
            ax.set_xlabel('Band [index]')
            ax.set_ylabel('Relative Tx2Sync Delay')

            plt.show()

            return delays
