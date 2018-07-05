from flora_tools.experiment import *


class MeasureTimeSync(Experiment):
    def __init__(self):

        description = "Measures the time taking for an IRQ interrupt propagating to NSS high"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'offset', 'measured']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'



        self.bench.scope.set_scale("COAX", 0.2)

        for i in range(0, self.iterations):
            offset = np.random.randint(800, 8000 + 1)  # Minimum 10us

            min_window = offset * 0.125E-6 * 5.0
            min_precision = 10E-9
            window, points, precision = self.bench.scope.get_next_valid_window(min_window, min_precision)

            self.bench.devkit_b.cmd("test sync -d {:d}".format(offset))

            self.bench.scope.init_measurement(window, trigger_rise=False, trigger_channel="DIO1", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_a.cmd("test sync -i")

            wave = self.bench.scope.finish_measurement(channels=[2, 3])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                dio1_indices = utilities.get_edges(wave[1])

                if (0 < len(nss_indices) < 10) & (0 < len(nss_indices) < 10):
                    dio1_interrupt = dio1_indices[0][0]
                    nss_react = nss_indices[0][0]
                    delay = (nss_react - dio1_interrupt) * self.bench.scope.sample_period
                else:
                    delay = np.nan

                item = [dt.datetime.now(), window, self.bench.scope.sample_period, offset, delay]
            else:
                item = [dt.datetime.now(), window, self.bench.scope.sample_period, offset, np.nan]

            df.loc[i] = item
            print(item)
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df : pd.DataFrame):
        df.dropna()

        plt.scatter(df.offset * 0.125E-6, df.measured)
        ax = plt.gca()
        ax.set_xlabel('HS Timer reaction offset [s]')
        ax.set_ylabel('Actual delay [s]')

        fit_rx = np.polyfit(df.offset * 0.125E-6, df.measured, 1)
        fit_fn_rx = np.poly1d(fit_rx)
        # fit_fn is now a function which takes in x and returns an estimate for y
        x = [0, 0.001]
        ax.plot(x, fit_fn_rx(x), ':k', linewidth=1.0)
        ax.set_xlim(0, 0.0011)
        ax.set_ylim(0, 0.0011)

        plt.show()

        #error = df.measured - fit_fn_rx(df.offset * 0.125E-6)
        delay = (df.measured - df.offset * 0.125E-6).mean()
        error = df.measured - delay - df.offset * 0.125E-6
        plt.scatter(df.offset * 0.125E-6, error)
        ax = plt.gca()
        ax.set_xlabel('HS Timer reaction offset [s]')
        ax.set_ylabel('HS Timer reaction delay [s]')
        ax.set_xlim(0, 0.0011)
        ax.set_ylim(-1E-7, +1E-7)

        plt.show()

        columns = ['delay', 'delay_err']
        timings = pd.DataFrame(columns=columns)
        timings.loc[0] = [delay, error.std()]

        return timings