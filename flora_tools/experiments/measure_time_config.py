from flora_tools.experiment import *


class MeasureTimeConfig(Experiment):
    def __init__(self):

        description = "Measures the time needed to configure the radio"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'tx', 'measured']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        points = 100000
        window = 0.001
        sample_period = window / (points - 1)

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration(
                tx='randomize')  # Does not work for FSK (random glitches on BUSY line)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_a.cmd(configuration.cmd)

            wave = self.bench.scope.finish_measurement(channels=[1, 3])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                busy_indices = utilities.get_edges(wave[1])

                if 0 < len(nss_indices) < 100:
                    nss_start = nss_indices[0][0]
                else:
                    nss_start = np.nan

                if 3 <= len(busy_indices) < 100:
                    if (busy_indices[-1][0] > nss_indices[-1][0]):
                        delay = (busy_indices[-1][0] - nss_start) * self.bench.scope.sample_period
                    else:
                        delay = (nss_indices[-1][0] - nss_start) * self.bench.scope.sample_period
                else:
                    delay = np.nan

                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band,
                        configuration.tx, delay]
            else:
                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band,
                        configuration.tx, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df: pd.DataFrame):
        df.dropna()

        delay_lora_tx = df.loc[(df.modulation < 8) & (df.tx == True)].measured
        delay_lora_rx = df.loc[(df.modulation < 8) & (df.tx == False)].measured
        delay_fsk_tx = df.loc[(df.modulation >= 8) & (df.tx == True)].measured
        delay_fsk_rx = df.loc[(df.modulation >= 8) & (df.tx == False)].measured

        columns = ['delay_lora_tx', 'delay_lora_tx_err', 'delay_lora_tx_min', 'delay_lora_tx_max',
                   'delay_lora_rx', 'delay_lora_rx_err', 'delay_lora_rx_min', 'delay_lora_rx_max',
                   'delay_fsk_tx', 'delay_fsk_tx_err', 'delay_fsk_tx_min', 'delay_fsk_tx_max',
                   'delay_fsk_rx', 'delay_fsk_rx_err', 'delay_fsk_rx_min', 'delay_fsk_rx_max',
                   ]
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay_lora_tx.mean(), delay_lora_tx.std(), delay_lora_tx.min(), delay_lora_tx.max(),
                          delay_lora_rx.mean(), delay_lora_rx.std(), delay_lora_rx.min(), delay_lora_rx.max(),
                          delay_fsk_tx.mean(), delay_fsk_tx.std(), delay_fsk_tx.min(), delay_fsk_tx.max(),
                          delay_fsk_rx.mean(), delay_fsk_rx.std(), delay_fsk_rx.min(), delay_fsk_rx.max()]

        return timings
