from flora_tools.experiment import *


class MeasureTimeTx2RxDone(Experiment):
    def __init__(self):
        description = "Measures the time needed from a executed setTx() command on the transmitter node (NSS going high) " \
                      "to the Rx Done IRQ on the receiver node (DIO1 rising edge)"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations

        Experiment.run(self, bench)

        self.bench.scope.set_scale("COAX", 0.2)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'power', 'payload', 'tx2rxdone']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration()
            configuration_rx = copy(configuration)
            configuration_rx.tx = False

            self.bench.devkit_a.cmd(configuration.cmd)
            self.bench.devkit_b.cmd(configuration_rx.cmd)

            text = utilities.get_random_text()
            if text is not None:
                text_len = (len(text) + 1)
            else:
                txt_len = 0

            math = RadioMath(configuration)
            min_window = math.get_message_toa(payload_size=text_len) * 1.1
            min_precision = 5E-6
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)

            self.bench.devkit_b.cmd('radio receive')
            if text is not None:
                self.bench.devkit_a.cmd("radio send '" + text + "' -s")
            else:
                self.bench.devkit_a.cmd("radio send -s")
            self.bench.devkit_a.delay_cmd_time(text_len)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window)
            self.bench.devkit_a.cmd("radio execute")

            wave = self.bench.scope.finish_measurement(channels=[1, 2])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                if (len(nss_indices) > 0 and len(nss_indices) < 10):
                    nss_time = nss_indices[0][0]
                else:
                    nss_time = np.nan

                dio1_indices = utilities.get_edges(wave[1])
                if (len(dio1_indices) > 2 and len(dio1_indices) < 10):
                    tx2rxdone_time = (dio1_indices[2][0] - nss_time) * self.bench.scope.sample_period
                else:
                    tx2rxdone_time = np.nan

                if tx2rxdone_time < 0:
                    tx2rxdone_time = np.nan

                item = [dt.datetime.now(), window, precision, configuration.modulation, configuration.band,
                        configuration.power, text_len, tx2rxdone_time]
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

            columns = ['modulation_name', 'sample_count', 'offset', 'offset_err', 'm', 'b', 'fit_err']
            delays = pd.DataFrame(columns=columns)
            delays.index.name = 'modulation'

            for i in mods:
                subset = df[df.modulation == i]

                config = RadioConfiguration(i)
                math = RadioMath(config)

                plt.figure(figsize=[12, 5])

                plt.subplot(121)

                plt.scatter(subset.payload, subset.tx2rxdone, c=config.color)
                plt.title("Tx2RxDone Delay vs. Payload Size\n{}".format(config.modulation_name))
                ax = plt.gca()
                ax.set_xlabel('Payload [bytes]')
                ax.set_ylabel('Tx2RxDone [s]')
                fit = np.polyfit(subset.payload, subset.tx2rxdone, 1)
                fit_fn = np.poly1d(fit)
                # fit_fn is now a function which takes in x and returns an estimate for y
                x = [0, 255 * 1.1]
                plt.plot(x, fit_fn(x), ':k', linewidth=1.0)

                plt.subplot(122)

                payloads = df.payload.sort_values().unique()
                columns = ['error']
                payload_estimation = pd.DataFrame(columns=columns)
                payload_estimation.index.name = 'payload'
                for j in payloads:
                    payload_subset = subset[subset.payload == j].loc[:, 'tx2rxdone']
                    payload_estimation.loc[j] = [payload_subset.std()]
                plt.title("Tx2RxDone stdev. vs. Payload Size\n{}".format(config.modulation_name))
                ax = plt.gca()
                ax.set_xlabel('Payload [bytes]')
                ax.set_ylabel('$\sigma$ [s]')
                plt.plot(payload_estimation.index.values, payload_estimation.error, c=config.color, linewidth=1.0)

                plt.show()

                def get_offsets(item):
                    offset = (item['tx2rxdone'] - math.get_message_toa(item['payload']))
                    return offset

                offsets = subset.apply(get_offsets, axis=1)
                fit_err = (subset.tx2rxdone - fit_fn(subset.payload)).std()

                delays.loc[i] = [config.modulation_name, len(subset), offsets.mean(), offsets.std(), fit[0], fit[1],
                                 fit_err]

            return delays
