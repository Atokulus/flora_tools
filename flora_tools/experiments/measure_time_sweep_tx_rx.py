from flora_tools.experiment import *


class MeasureTimeSweepTxRx(Experiment):
    def __init__(self):

        description = "Measures if packet is received correctly in case of Tx-Rx window offset."

        Experiment.__init__(self, description)

    def run(self, bench, iterations=100000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'preamble', 'offset', 'valid']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            self.bench.devkit_a.cmd("system reset")
            self.bench.devkit_b.cmd("system reset")

            time.sleep(0.5)

            configuration = RadioConfiguration.get_random_configuration(preamble=True)
            configuration_rx = copy(configuration)
            configuration_rx.tx = False

            math = RadioMath(configuration)

            large_offset = 96000
            offset = np.random.randint(0, 2.5 * int(math.get_preamble_time() * 8E6 + 1))
            # offset = int(math.get_preamble_time() * 8E6)

            correction_offset = int((
                                            2.1 +  # 2.1 us (Wire Sync Delay)
                                            126.2 -  # 126.2 us (Tx2Rf Delay)
                                            85.2  # 85.2 (Rx2Rf Delay)
                                    ) * 8)

            min_window = (large_offset / 8E6 + math.sync_time + offset / 8E6 + 0.005) * 2.0
            min_precision = 1E-7
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)

            self.bench.devkit_a.cmd(configuration_rx.cmd)
            self.bench.devkit_b.cmd(configuration.cmd)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="BUSY", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_b.cmd("test sync")
            self.bench.devkit_a.cmd("test sync -i -s 32000")

            self.bench.devkit_a.cmd("radio receive -s -v")
            self.bench.devkit_b.cmd("radio send '' -s")

            self.bench.devkit_a.cmd(
                "radio execute -d {:d}".format(large_offset + int(math.get_preamble_time() * 8E6) + correction_offset))
            self.bench.devkit_b.cmd("radio execute -c {:d}".format(large_offset + offset))

            wave = self.bench.scope.finish_measurement(channels=[2])

            if wave is not None:
                # nss_tx_indices = utilities.get_edges(wave[0])
                dio1_indices = utilities.get_edges(wave[0])
                # nss_rx_indices = utilities.get_edges(wave[2])

                if (0 < len(dio1_indices) < 10):
                    valid = True
                else:
                    valid = False

                item = [dt.datetime.now(), window, self.bench.scope.sample_period, configuration.modulation,
                        configuration.band, configuration.preamble, offset, valid]
            else:
                item = [dt.datetime.now(), window, self.bench.scope.sample_period, configuration.modulation,
                        configuration.band, configuration.preamble, offset, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df: pd.DataFrame):
        df.dropna()

        def calculate_color(row):
            if row['valid'] is True:
                config = RadioConfiguration(row.modulation)
                return config.color
            else:
                return '#0F0F0F02'

        colors = df.apply(calculate_color, axis=1)

        def calculate_relative_offset(row):
            config = RadioConfiguration(row.modulation, preamble=row.preamble)
            math = RadioMath(config)
            return (row.offset / 8E6) / math.get_preamble_time()

        relative_offsets = df.apply(calculate_relative_offset, axis=1) - 1

        fig = plt.figure(figsize=[12, 8])
        # fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(df.modulation, df.preamble, relative_offsets, c=colors)

        mods = df.modulation.sort_values().unique();
        ax.set_xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

        ax.set_xlabel("Modulation [index]")
        ax.set_ylabel("Preamble Length [#symbols]")
        ax.set_zlabel("Relative Offset")

        plt.show()

        for mod in mods:
            subset = df[df.modulation == mod]

            def calculate_absolute_offset(row):
                config = RadioConfiguration(row.modulation, preamble=row.preamble)
                math = RadioMath(config)
                return (row.offset / 8) - math.get_preamble_time() * 1E6

            absolute_offsets = subset.apply(calculate_absolute_offset, axis=1)

            colors = subset.apply(calculate_color, axis=1)
            plt.scatter(subset.preamble, absolute_offsets, c=colors)

            config2 = RadioConfiguration(modulation=mod, preamble=2)
            config14 = RadioConfiguration(modulation=mod, preamble=14)
            math2 = RadioMath(config2)
            math14 = RadioMath(config14)
            offset2_high = math2.get_preamble_time() * 1E6
            offset14_high = math14.get_preamble_time() * 1E6

            plt.title(config2.modulation_name)

            plt.plot([2, 14], [offset2_high, offset14_high], 'k-.')
            plt.plot([2, 14], [0, 0], 'k:')
            plt.plot([2, 14], [-offset2_high, -offset14_high], 'k-.')

            ax = plt.gca()
            ax.set_xlabel("Preamble length [#symbols]")
            ax.set_ylabel("Absolute Offset [us]")
            plt.show()
