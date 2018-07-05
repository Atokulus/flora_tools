from flora_tools.experiment import *


class MeasureTimeSetFS(Experiment):
    def __init__(self):

        description = "Measures the time needed to set radio into Tx or Rx mode"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'payload', 'tx', 'boost', 'measured']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        points = 100000
        window = 0.0004
        sample_period = window / (points - 1)

        self.bench.scope.set_scale("COAX", 0.2)

        for i in range(0, self.iterations):
            text = utilities.get_random_text(length=254)
            text_len = (len(text) + 1)

            configuration = RadioConfiguration.get_random_configuration(tx='randomize') # Does not work for FSK (random glitches on BUSY line)
            self.bench.devkit_a.cmd("radio standby")
            self.bench.devkit_a.cmd(configuration.cmd)

            if configuration.tx:
                self.bench.devkit_a.cmd("radio payload -d '" + text + "'")

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            boost = np.random.choice([True, False])

            if configuration.tx:
                self.bench.devkit_a.cmd("radio send -l")
            else:
                if boost:
                    self.bench.devkit_a.cmd("radio receive")
                else:
                    self.bench.devkit_a.cmd("radio receive -b false")

            wave = self.bench.scope.finish_measurement(channels=[1])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])

                if 0 < len(nss_indices) < 100:
                    nss_start = nss_indices[0][0]
                    delay = (nss_indices[-1][0] - nss_start) * self.bench.scope.sample_period
                else:
                    delay = np.nan

                if configuration.tx:
                    item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, text_len, configuration.tx, False, delay]
                else:
                    item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, 0, configuration.tx, boost, delay]
            else:
                if configuration.tx:
                    item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, text_len, configuration.tx, False, np.nan]
                else:
                    item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band, 0, configuration.tx, boost, np.nan]


            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df : pd.DataFrame):
        df.dropna()
        
        delay = df.measured

        columns = ['delay', 'delay_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay.mean(), delay.std()]

        delay_lora_tx = df.loc[(df.modulation < 8) & (df.tx == True)].measured
        delay_lora_rx = df.loc[(df.modulation < 8) & (df.tx == False) & (df.boost == False)].measured
        delay_lora_rx_boost = df.loc[(df.modulation < 8) & (df.tx == False) & (df.boost == True)].measured
        delay_fsk_tx = df.loc[(df.modulation >= 8) & (df.tx == True)].measured
        delay_fsk_rx = df.loc[(df.modulation >= 8) & (df.tx == False) & (df.boost == False)].measured
        delay_fsk_rx_boost = df.loc[(df.modulation >= 8) & (df.tx == False) & (df.boost == True)].measured

        columns = ['delay_lora_tx', 'delay_lora_tx_err',
                   'delay_lora_rx', 'delay_lora_rx_err',
                   'delay_lora_rx_boost', 'delay_lora_rx_boost_err',
                   'delay_fsk_tx', 'delay_fsk_tx_err',
                   'delay_fsk_rx', 'delay_fsk_rx_err',
                   'delay_fsk_rx_boost', 'delay_fsk_rx_boost_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay_lora_tx.mean(), delay_lora_tx.std(),
                          delay_lora_rx.mean(), delay_lora_rx.std(),
                          delay_lora_rx_boost.mean(), delay_lora_rx_boost.std(),
                          delay_fsk_tx.mean(), delay_fsk_tx.std(),
                          delay_fsk_rx.mean(), delay_fsk_rx.std(),
                          delay_fsk_rx_boost.mean(), delay_fsk_rx_boost.std()]

        return timings