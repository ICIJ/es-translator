# Module from the same package
from .apertium import Apertium

class Pairs:
    def __init__(self, data_dir, local = False):
        self.apertium = Apertium(pack_dir=data_dir)
        self.local = local

    @property
    def local_pairs(self):
        return self.apertium.local_pairs

    @property
    def remote_pairs(self):
        return self.apertium.remote_pairs

    @property
    def local_pairs_to_string(self):
        return '\n'.join(self.local_pairs)

    @property
    def remote_pairs_to_string(self):
        return '\n'.join(self.remote_pairs)

    def print_pairs(self):
        if self.local:
            print(self.local_pairs_to_string)
        else:
            print(self.remote_pairs_to_string)
