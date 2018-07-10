from flora_tools.experiment import *


class MeasureTimeSetPayload(Experiment):
    def __init__(self):

        description = "Measures the time needed to set a full payload buffer (255 bytes) on the radio"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'payload', 'measured']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        points = 100000
        window = 0.002
        sample_period = window / (points - 1)

        for i in range(0, self.iterations):
            text = utilities.get_random_text(length=254)
            text_len = (len(text) + 1)

            configuration = RadioConfiguration.get_random_configuration(
                tx='randomize')  # Does not work for FSK (random glitches on BUSY line)
            self.bench.devkit_a.cmd(configuration.cmd)

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_a.cmd("radio payload -d '" + text + "'")

            wave = self.bench.scope.finish_measurement(channels=[1])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])

                if 0 < len(nss_indices) < 100:
                    nss_start = nss_indices[0][0]
                    delay = (nss_indices[-1][0] - nss_start) * self.bench.scope.sample_period
                else:
                    delay = np.nan

                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band,
                        text_len, delay]
            else:
                item = [dt.datetime.now(), window, sample_period, configuration.modulation, configuration.band,
                        text_len, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df: pd.DataFrame):
        df.dropna()

        delay = df.measured

        columns = ['delay', 'delay_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay.mean(), delay.std()]

        delay_lora = df.loc[df.modulation < 8].measured
        delay_fsk = df.loc[df.modulation >= 8].measured

        columns = ['delay_lora', 'delay_lora_err',
                   'delay_fsk', 'delay_fsk_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay_lora.mean(), delay_lora.std(),
                          delay_fsk.mean(), delay_fsk.std()]

        return timings
