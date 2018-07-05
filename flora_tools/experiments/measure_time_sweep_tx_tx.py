from flora_tools.experiment import *


class MeasureTimeSweepTxTx(Experiment):
    def __init__(self):

        description = "Measures if a packet can be received correctly if there are arbitrary offsets between two senders' Tx and one receiver's Rx windows"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=100000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'preamble', 'offset_1', 'offset_2', 'valid']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            self.bench.devkits[0].cmd("system reset")
            self.bench.devkits[1].cmd("system reset")
            self.bench.devkits[2].cmd("system reset")

            time.sleep(0.3)

            configuration = RadioConfiguration.get_random_configuration(preamble=True, power=[-10])
            configuration_rx = copy(configuration)
            configuration_rx.tx = False

            math = RadioMath(configuration)

            large_offset = 96000
            offset_b = np.random.randint(0, 2.5 * int(math.get_preamble_time() * 8E6) + 1)
            offset_c = np.random.randint(offset_b, 2.5 * int(math.get_preamble_time() * 8E6) + 1)

            correction_offset = int((
                2.1 +  # 2.1 us (Wire Sync Delay)
                126.2 -  # 126.2 us (Tx2Rf Delay)
                85.2  # 85.2 (Rx2Rf Delay)
            ) * 8)

            min_window = (large_offset / 8E6 + math.sync_time + offset_c / 8E6 + 0.005) * 1.2
            min_precision = 1E-4
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)

            self.bench.devkits[0].cmd(configuration_rx.cmd)
            self.bench.devkits[1].cmd(configuration.cmd)
            self.bench.devkits[2].cmd(configuration.cmd)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="BUSY", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkits[0].cmd("test sync -i -s 32000")
            self.bench.devkits[1].cmd("test sync")
            self.bench.devkits[2].cmd("test sync")

            self.bench.devkits[0].cmd("radio receive -s -v")
            self.bench.devkits[1].cmd("radio send '' -s")
            self.bench.devkits[2].cmd("radio send '' -s")

            self.bench.devkits[0].cmd("radio execute -d {:d}".format(large_offset + int(math.get_preamble_time() * 8E6) + correction_offset))
            self.bench.devkits[1].cmd("radio execute -c {:d}".format(large_offset + offset_b))
            self.bench.devkits[2].cmd("radio execute -c {:d}".format(large_offset + offset_c))

            wave = self.bench.scope.finish_measurement(channels=[2])

            if wave is not None:
                #nss_tx_indices = utilities.get_edges(wave[0])
                dio1_indices = utilities.get_edges(wave[0])
                #nss_rx_indices = utilities.get_edges(wave[2])

                if (0 < len(dio1_indices) < 10):
                    valid = True
                else:
                    valid = False

                item = [dt.datetime.now(), window, self.bench.scope.sample_period, configuration.modulation, configuration.band, configuration.preamble, offset_b, offset_c, valid]
            else:
                item = [dt.datetime.now(), window, self.bench.scope.sample_period, configuration.modulation, configuration.band, configuration.preamble, offset_b, offset_c, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df : pd.DataFrame):
        df.dropna()

        colormap = plt.cm.viridis

        def calculate_color(row):
            if row['valid'] is True:
                return colormap(row.preamble/12)
            else:
                return '#0F0F0F10'

        mods = df.modulation.sort_values().unique();

        for mod in mods:
            subset = df[df.modulation == mod]

            def calculate_absolute_offset(row):
                config = RadioConfiguration(row.modulation, preamble=row.preamble)
                math = RadioMath(config)
                return (pd.Series([row.offset_1, row.offset_2]) / 8) - math.get_preamble_time() * 1E6

            absolute_offsets = subset.apply(calculate_absolute_offset, axis=1)

            colors = subset.apply(calculate_color, axis=1)

            fig = plt.figure(figsize=[14, 6])
            # fig = plt.figure()
            ax = fig.add_subplot(121, projection='3d')
            ax.scatter(subset.preamble, absolute_offsets.loc[:,0], absolute_offsets.loc[:,1], c=colors)

            mods = df.modulation.sort_values().unique();
            ax.set_xticks(mods, map(RadioConfiguration.get_modulation_name, mods))

            ax.set_xlabel("Preamble Length [#symbols]")
            ax.set_ylabel("Absolute Offset Sender 1 [us]")
            ax.set_zlabel("Absolute Offset Sender 2 [us]")

            config = RadioConfiguration(modulation=mod)
            plt.title(config.modulation_name)

            plt.subplot(122)

            preambles = subset.preamble.sort_values().unique()

            def calc_relative_offset(row):
                config = RadioConfiguration(row.modulation, preamble=row.preamble)
                math = RadioMath(config)
                return ((pd.Series([row.offset_1, row.offset_2]) / 8E6 - math.get_preamble_time())) / math.get_preamble_time()

            relative_offsets = subset.apply(calc_relative_offset, axis=1)

            ax = plt.gca()
            ax.set_xlim(-1.0, 1.5)
            ax.set_ylim(-1.0, 1.5)

            plt.xlabel("Relative Offset Sender 1")
            plt.ylabel("Relative Offset Sender 2")

            plt.scatter(relative_offsets[0], relative_offsets[1], c=colors)

            plt.title(config.modulation_name)

            plt.tight_layout()

            plt.show()



