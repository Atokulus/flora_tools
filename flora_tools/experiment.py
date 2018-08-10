class Experiment:
    def __init__(self, description):
        self.name = self.__class__.__name__
        self.iterations = 100
        self.description = description
        self.bench = None

    def run(self, bench):
        self.bench = bench
        print("\n\n[{}]: {}".format(self.name, self.description))
