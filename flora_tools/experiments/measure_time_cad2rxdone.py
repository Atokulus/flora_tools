from flora_tools.experiment import *


class MeasureTimeCAD2RxDone(Experiment):
    def __init__(self):
        description = "Measures the time needed from setCAD() (NSS going low for SPI, as it cannot be timed with NSS high) " \
                      "to the rising of the IRQ_SYNC and IRQ_RX_DONE interrupt on receiver side"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=1000):
        self.iterations = iterations

        Experiment.run(self, bench)

        self.bench.scope.set_scale("COAX", 0.2)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'cad2rf', 'cad2done']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration(limit="LoRa")
            # configuration = RadioConfiguration(3, 0, 0)
            configuration.tx = False

            math = RadioMath(configuration)
            min_window = (math.get_symbol_time() * 4.5) * 1.1 * 2.0
            min_precision = 0.1E-6
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)
            start = int(points * 0.4)

            self.bench.devkit_a.cmd(configuration.cmd)

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
                    cad2cadirq_time = (dio1_indices[0][0] - setcad_time) * self.bench.scope.sample_period
                else:
                    cad2cadirq_time = np.nan

                busy_indices = utilities.get_edges(wave[2])
                if len(busy_indices) > 0 and len(busy_indices) < 20:
                    cad2rf_time = (busy_indices[3][0] - setcad_time) * self.bench.scope.sample_period
                else:
                    cad2rf_time = np.nan

                if cad2cadirq_time < 0:
                    cad2cadirq_time = np.nan
                if cad2rf_time < 0:
                    cad2rf_time = np.nan

                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band, cad2rf_time,
                        cad2cadirq_time]
            else:
                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band, np.nan,
                        np.nan]

            df.loc[i] = item
            df.to_csv("{}.csv".format(self.name))
            print(item)

    def analyze(self, df):
        with plt.style.context("bmh"):
            df = df.dropna()

            mods = df.modulation.sort_values().unique();

            columns = ['modulation_name', 'sample_count', 'cad_symbol_time', 'cad2rf', 'cad2rf_err', 'cad2done',
                       'cad2done_err']
            delays = pd.DataFrame(columns=columns)
            delays.index.name = 'modulation'

            for i in mods:
                subset = df[df.modulation == i]

                config = RadioConfiguration(i)
                math = RadioMath(config)
                weights = np.ones(len(subset['cad2done'])) * 1 / len(subset['cad2done']) * 1E3
                n, bins, patches = plt.hist(subset['cad2done'] * 1E3, 100, weights=weights,
                                            color=config.color)

                plt.title('setCAD to Rf delay for {}\n'.format(config.modulation_name) + '$\mu = ' + str(
                    subset['cad2done'].mean() * 1E3) + '\ \mathrm{ms},\ \sigma = {' + str(
                    subset['cad2done'].std() * 1E6) + '}$ µs')
                plt.xlabel('Delay [ms]')
                plt.ylabel('Probability [‰]')
                plt.show()

                weights = np.ones(len(subset['cad2rf'])) * 1 / len(subset['cad2rf']) * 1E3
                n, bins, patches = plt.hist(subset['cad2rf'] * 1E6, 100, weights=weights,
                                            color=config.color)

                plt.title('setCAD to CAD_DONE IRQ delay for {}\n'.format(config.modulation_name) + '$\mu = ' + str(
                    subset['cad2rf'].mean() * 1E6) + '\ \mathrm{us},\ \sigma = {' + str(
                    subset['cad2rf'].std() * 1E6) + '}$ µs')
                plt.xlabel('Delay [us]')
                plt.ylabel('Probability [‰]')
                plt.show()

                delays.loc[i] = [config.modulation_name, len(subset), math.get_symbol_time() * 4,
                                 subset['cad2rf'].mean(), subset['cad2rf'].std(), subset['cad2done'].mean(),
                                 subset['cad2done'].std()]

            plt.title("setCAD() to Rf delay")
            rects = plt.bar(mods, delays.loc[:, 'cad2rf'], yerr=delays.loc[:, 'cad2rf_err'], log=False)
            for i, rect in enumerate(rects):
                rect.set_fc(RadioConfiguration(i).color)
            plt.ylabel('Delay [s]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))
            plt.show()

            plt.figure(figsize=(10, 8))
            plt.title("setCAD() to CAD_DONE IRQ average delay")

            ax = plt.gca()
            rects = plt.bar(mods - 0.2, delays.loc[:, 'cad2done'], width=0.4, log=True)
            ref_rects = plt.bar(mods + 0.2, delays.loc[:, 'cad_symbol_time'], width=0.4, log=True)
            for i, rect in zip(mods, rects):
                rect.set_fc(RadioConfiguration(i).color)
                height = rect.get_height()
                ax.text(rect.get_x() + rect.get_width() / 2., 1.02 * height,
                        "{:.2E}".format(delays.loc[i, 'cad2done']),
                        ha='center', va='bottom')

            rect = ref_rects[0]
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    ax.get_ylim()[0] + np.power(10, np.average(np.log10([ax.get_ylim()[0], rect.get_height()]))),
                    "4 symbols time-on-air reference",
                    rotation=90,
                    ha='center', va='center',
                    color='white')
            plt.tight_layout()

            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)

            plt.ylabel('$\mu$ [s]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            plt.show()

            plt.figure(figsize=(10, 8))

            plt.title("CAD 2 Done delay standard deviation")

            ax = plt.gca()
            rects = plt.bar(mods, delays.loc[:, 'cad2done_err'] * 1E6)
            for i, rect in zip(mods, rects):
                rect.set_fc(RadioConfiguration(i).color)
                height = rect.get_height()
                if not np.isnan(height):
                    ax.text(rect.get_x() + rect.get_width() / 2., 1.01 * height,
                            "{:.2E}".format(delays.loc[i, 'cad2done_err']),
                            ha='center', va='bottom')

            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)

            plt.ylabel('$\sigma$ [µs]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            plt.show()

            return delays
