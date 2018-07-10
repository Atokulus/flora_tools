from flora_tools.experiment import *


class MeasureTimeSniffMode(Experiment):
    def __init__(self):

        description = "Measures the periods and duty cycles of different sniff mode configurations"

        Experiment.__init__(self, description)

    def run(self, bench, iterations=10000):
        self.iterations = iterations
        Experiment.run(self, bench)

        columns = ['time', 'window', 'precision', 'modulation', 'band', 'rx', 'sleep', 'period', 'measured']
        df = pd.DataFrame(columns=columns)
        df.index.name = 'sample'

        points = 20000000
        window = 2.0
        sample_period = window / (points - 1)

        for i in range(0, self.iterations):
            configuration = RadioConfiguration.get_random_configuration(tx=False,
                                                                        limit="LoRa")  # Does not work for FSK (random glitches on BUSY line)
            self.bench.devkit_a.cmd(configuration.cmd)

            rx = np.random.randint(10, 32000)  # 1/2 second (in 15.625us steps)
            sleep = np.random.randint(10, 32000)  # 1/2 second (in 15.625us steps)

            self.bench.devkit_a.cmd("radio receive {:d} {:d} -s".format(rx, sleep))
            self.bench.devkit_a.delay_cmd_time()

            self.bench.scope.init_measurement(window, trigger_rise=True, trigger_channel="NSS", points=points)
            self.bench.scope.delay_acquisition_setup_time(window=window)

            self.bench.devkit_a.cmd("radio execute")

            wave = self.bench.scope.finish_measurement(channels=[1, 3])

            if wave is not None:
                nss_indices = utilities.get_edges(wave[0])
                busy_indices = utilities.get_edges(wave[1])
                if (len(nss_indices) > 0 and len(nss_indices) < 10 and len(busy_indices) >= 2):
                    setup_time = (busy_indices[1][0] - nss_indices[0][0]) * self.bench.scope.sample_period
                    if not np.isnan(setup_time) and setup_time > 0:
                        item = [dt.datetime.now(), window, 1E-7, configuration.modulation, configuration.band, rx,
                                sleep, 'setup', setup_time]
                        row = pd.DataFrame(dict(zip(columns, item)), index=[0])
                        df = df.append(row, ignore_index=True)
                        print(item)

                    for j in range(1, len(busy_indices) - 1):
                        period = (busy_indices[j + 1][0] - busy_indices[j][0]) * self.bench.scope.sample_period
                        if not np.isnan(period) and period > 0:
                            item = [dt.datetime.now(), window, 1E-7, configuration.modulation, configuration.band, rx,
                                    sleep, ('rx' if (j % 2) == 1 else 'sleep'), period]
                            row = pd.DataFrame(dict(zip(columns, item)), index=[0])
                            df = df.append(row, ignore_index=True)
                            print(item)

            df.index.name = 'sample'
            df.to_csv("{}.csv".format(self.name))

    def analyze(self, df):
        def rx_f(x):
            offset = x['measured'] - x['rx'] * 15.625E-6
            return offset

        def sleep_f(x):
            offset = x['measured'] - x['sleep'] * 15.625E-6
            return offset

        with plt.style.context('bmh'):
            df = df.dropna()

            plt.figure(figsize=[14, 5])

            plt.subplot(121)

            rx = df.loc[df.period == 'rx']
            rx_offsets = rx.apply(rx_f, axis=1)
            rx = rx.copy()
            rx.loc[:, 'offset'] = rx_offsets
            rx = rx.loc[(rx.offset > -0.01) & (rx.offset < 0.01)]
            colors = rx.modulation.map(RadioConfiguration.get_color)
            plt.scatter(rx.rx * 15.625E-6, rx.offset, c=colors)
            ax = plt.gca()
            ax.set_xlabel('Set Rx period [s]')
            ax.set_ylabel('Measured Offset [s]')

            fit_rx = np.polyfit(rx.rx * 15.625E-6, rx.offset, 1)
            fit_fn_rx = np.poly1d(fit_rx)
            # fit_fn is now a function which takes in x and returns an estimate for y
            x = [0, 0.6]
            ax.plot(x, fit_fn_rx(x), ':k', linewidth=1.0)

            plt.subplot(122)

            sleep = df.loc[df.period == 'sleep']
            sleep_offsets = sleep.apply(sleep_f, axis=1)
            sleep = sleep.copy()
            sleep.loc[:, 'offset'] = sleep_offsets
            sleep = sleep.loc[(sleep.offset > -0.01) & (sleep.offset < 0.01)]
            colors = sleep.modulation.map(RadioConfiguration.get_color)
            plt.scatter(sleep.sleep * 15.625E-6, sleep.offset, c=colors)
            ax = plt.gca()
            ax.set_xlabel('Set sleep period [s]')
            ax.set_ylabel('Measured Offset [s]')

            fit_sleep = np.polyfit(sleep.sleep * 15.625E-6, sleep.offset, 1)
            fit_fn_sleep = np.poly1d(fit_sleep)
            # fit_fn is now a function which takes in x and returns an estimate for y
            x = [0, 0.6]
            ax.plot(x, fit_fn_sleep(x), ':k', linewidth=1.0)

            plt.show()

            columns = ['setup', 'setup_err', 'rx_offset', 'rx_err', 'sleep_offset', 'sleep_err']
            timings = pd.DataFrame(columns=columns)

            def interpolation_error_rx(x):
                error = x['offset'] - fit_fn_sleep(x['rx'] * 15.625E-6)
                return error

            def interpolation_error_sleep(x):
                error = x['offset'] - fit_fn_sleep(x['sleep'] * 15.625E-6)
                return error

            setup = df[df.period == 'setup'].measured
            rx_error = rx.apply(interpolation_error_rx, axis=1)
            sleep_error = sleep.apply(interpolation_error_sleep, axis=1)

            timings.loc[0] = [setup.mean(), setup.std(), rx.offset.mean(), rx_error.std(), sleep.offset.mean(),
                              sleep_error.std()]

            return timings
