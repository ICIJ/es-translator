import tempfile
import sys
from glob import glob
from sh import apertium, apertium_get, echo, pushd, mkdir, cp

class Apertium:
    def __init__(self, source, target, pack_dir = None):
        self.source = source
        self.target = target
        # Create a temporary pack dir (if needed)
        self.pack_dir = pack_dir or tempfile.mkdtemp()
        # Raise an exception if the language pair is unkown
        if self.is_pair_available() and not self.attempt_to_download_pair():
            raise Exception('The pair is not available')

    def pair(self):
        return '%s-%s' % (self.source, self.target)

    def is_pair_available(self):
        return self.pair() not in self.available_pairs()

    def attempt_to_download_pair(self):
        # All commands must be run from the pack dir
        with pushd(self.pack_dir):
            # Get the pair and print-out the result
            apertium_get(self.pair(), '-s')
            # Create a modes directory to save all modes files
            mkdir('-p', './modes')
            # Copy all the mode files
            cp(glob('./*/modes/*.mode'), './modes')
        return True

    def translate(self, input):
        # Create a sub-process witch can receive a input
        return apertium(echo(input), self.pair(), '-d', self.pack_dir)

    def available_pairs(self):
        output = apertium('-d', self.pack_dir, '-l').strip()
        return [ s.strip() for s in output.split('\n') ]
