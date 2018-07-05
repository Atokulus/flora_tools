from flora_tools.experiment import *


class MeasureTimeCAD2Done(Experiment):
    def __init__(self):
        description = "Measures the time needed from setCAD() (NSS going low for SPI, as it cannot be timed with NSS high) " \
                      "to the rising of the IRQ_CAD_DONE interrupt on receiver side"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=1000):
        self.iterations = iterations

        Experiment.run(self, bench)

        self.bench.scope.set_scale("COAX", 0.2)

        columns = ['time', 'window','precision', 'modulation', 'band', 'cad2rf', 'cad2done', 'detected']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration(limit="LoRa")
            # configuration = RadioConfiguration(3, 0, 0)
            configuration.tx = False
            configuration_tx = copy(configuration)
            configuration_tx.tx = True


            math = RadioMath(configuration)
            min_window = (math.get_symbol_time() * 4.5) * 1.1
            min_precision = 0.1E-6
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)
            start = 0

            self.bench.devkit_a.cmd(configuration.cmd)

            if np.random.choice([True, False]):
                self.bench.devkit_b.cmd(configuration_tx.cmd)
                self.bench.devkit_b.cmd('radio preamble')

                detected = True
            else:
                self.bench.devkit_b.cmd('radio standby')
                detected = False

            self.bench.scope.init_measurement(window, trigger_rise=True,
                                              trigger_channel="NSS",
                                              points=points,
                                              start=start,
                                              text=("{}:{}".format(self.name, configuration)))
            self.bench.scope.delay_acquisition_setup_time(window)

            self.bench.devkit_a.cmd("radio cad")

            wave = self.bench.scope.finish_measurement(channels=[1,2,3])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                if len(nss_indices) > 4 and len(nss_indices) < 20:
                    setcad_time = nss_indices[4][0]
                else:
                    setcad_time = np.nan

                dio1_indices = utilities.get_edges(wave[1])
                if len(dio1_indices) > 0 and len(dio1_indices) < 5:
                    cad2cadirq_time = (dio1_indices[0][0] - setcad_time) * self.bench.scope.sample_period
                else:
                    cad2cadirq_time = np.nan

                busy_indices = utilities.get_edges(wave[2])
                if len(busy_indices) > 3 and len(busy_indices) < 20:
                    cad2rf_time = (busy_indices[3][0] - setcad_time) * self.bench.scope.sample_period
                else:
                    cad2rf_time = np.nan


                if cad2cadirq_time < 0:
                    cad2cadirq_time = np.nan
                if cad2rf_time < 0:
                    cad2rf_time = np.nan

                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band, cad2rf_time, cad2cadirq_time, detected]
            else:
                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band, np.nan, np.nan, detected]

            df.loc[i] = item
            df.to_csv("{}.csv".format(self.name))
            print(item)

    def analyze(self, df):
        with plt.style.context("bmh"):
            df = df.dropna()

            mods = df.modulation.sort_values().unique();

            columns = ['modulation_name', 'sample_count', 'cad_symbol_time', 'cad2rf', 'cad2rf_err', 'cad2done', 'cad2done_err', 'detected']
            delays_nodetection = pd.DataFrame(columns=columns)
            delays_nodetection.index.name = 'modulation'

            mods = df.modulation.sort_values().unique();

            delays_detected = pd.DataFrame(columns=columns)
            delays_detected.index.name = 'modulation'

            for i in mods:
                subset = df[(df.modulation == i)]

                config = RadioConfiguration(i)
                math = RadioMath(config)

                plt.figure(figsize=[14, 5])

                plt.suptitle('CAD for {}'.format(config.modulation_name), y=1.03)

                plt.subplot(131)

                weights = np.ones(len(subset['cad2rf'])) * 1 / len(subset['cad2rf']) * 1E3
                n, bins, patches = plt.hist(subset['cad2rf'] * 1E6, 100, weights=weights,
                                            color=config.color)

                mu = '$\mu = {:.2E} {}'.format(subset['cad2rf'].mean(),  '\mathrm{s}$')
                sigma = '$\sigma = {:.2E} {}'.format(subset['cad2rf'].std(), '\mathrm{s}$')
                title = 'to RF ({},{})'.format(mu, sigma)

                plt.title(title, fontsize=12)
                plt.xlabel('Delay [ms]')
                plt.ylabel('Probability [‰]')

                for j in [True, False]:
                    if j:
                        plt.subplot(132)
                    else:
                        plt.subplot(133)

                    delays = delays_detected if j else delays_nodetection
                    subset = df[(df.modulation == i) & (df.detected == j)]

                    weights = np.ones(len(subset['cad2done'])) * 1 / len(subset['cad2done']) * 1E3
                    n, bins, patches = plt.hist(subset['cad2done'] * 1E3, 100, weights=weights,
                                                color=config.color)

                    mu = '$\mu = {:.2E} {}'.format(subset['cad2done'].mean(), '\mathrm{s}$')
                    sigma = '$\sigma = {:.2E} {}'.format(subset['cad2done'].std(), '\mathrm{s}$')
                    title = 'DONE ({})\n{},{}'.format("activity" if j else "no activity", mu, sigma)

                    plt.title(title, fontsize=12)
                    plt.xlabel('Delay [us]')
                    plt.ylabel('Probability [‰]')

                    delays.loc[i] = [config.modulation_name, len(subset), math.get_symbol_time()*4, subset['cad2rf'].mean(), subset['cad2rf'].std(), subset['cad2done'].mean(), subset['cad2done'].std(), j]

            plt.show()

            fig = plt.figure(figsize=(14, 10))
            gs = gridspec.GridSpec(2, 2, height_ratios=[3, 2])


            ax = fig.add_subplot(gs[0, :])
            plt.title("setCAD() to CAD_DONE IRQ average delay")
            det_rects = ax.bar(mods-0.3, delays_detected.loc[:, 'cad2done'], width=0.3, log=True)
            rects = ax.bar(mods, delays_nodetection.loc[:, 'cad2done'], width=0.3, log=True)
            ref_rects = ax.bar(mods+0.3, delays.loc[:, 'cad_symbol_time'], width=0.3, log=True)
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

            rect = det_rects[0]
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    ax.get_ylim()[0] + np.power(10, np.average(np.log10([ax.get_ylim()[0], rect.get_height()]))),
                    "detection (preamble present)",
                    rotation=90,
                    ha='center', va='center',
                    color='white')

            rect = rects[0]
            ax.text(rect.get_x() + rect.get_width() / 2.,
                    ax.get_ylim()[0] + np.power(10, np.average(np.log10([ax.get_ylim()[0], rect.get_height()]))),
                    "no detection (no preamble present)",
                    rotation=90,
                    ha='center', va='center',
                    color='white')
            ax.grid(False)
            ax.grid(which='minor', axis='y', alpha=0.2)
            ax.grid(which='major', axis='y', alpha=0.5)
            plt.ylabel('$\mu$ [s]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            ax = fig.add_subplot(gs[1, 0])
            plt.title("setCAD() to Rf delay")
            rects = ax.bar(mods, delays_nodetection.loc[:,'cad2rf'], yerr=delays.loc[:,'cad2rf_err'], log=False)
            for i, rect in enumerate(rects):
                rect.set_fc(RadioConfiguration(i).color)
            plt.ylabel('Delay [s]')
            plt.xticks(mods, map(RadioConfiguration.get_modulation_name, mods))


            ax = fig.add_subplot(gs[1, 1])
            plt.title("CAD 2 Done delay standard deviation")
            rects = ax.bar(mods, delays_nodetection.loc[:, 'cad2done_err'] * 1E6 , width=0.8)
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

            return (delays_detected, delays_nodetection)











