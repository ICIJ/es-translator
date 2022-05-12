from abc import ABC, abstractmethod
from os.path import abspath

from ..alpha import to_alpha_2, to_alpha_3, to_name

class AbstractInterpreter(ABC):
    name = 'ABSTRACT'
    
    def __init__(self, source = None, target = None, intermediary = None, pack_dir = None):
        self.source = source
        self.target = target
        self.intermediary = intermediary
        # Create a temporary pack dir (if needed) to download language packs
        if pack_dir is not None:
            self.pack_dir = abspath(pack_dir) 
  
    @property
    def name(self):
        return self.__class__.name
    
    @property
    def source_alpha_2(self):
        return to_alpha_2(self.source)

    @property
    def source_alpha_3(self):
        return to_alpha_3(self.source)

    @property
    def source_name(self):
        return to_name(self.source_alpha_2)

    @property
    def target_alpha_2(self):
        return to_alpha_2(self.target)

    @property
    def target_alpha_3(self):
        return to_alpha_3(self.target)

    @property
    def intermediary_alpha_3(self):
        return to_alpha_3(self.intermediary)

    @property
    def target_name(self):
        return to_name(self.target_alpha_2)

    @property
    def pair(self):
        return '%s-%s' % (self.source, self.target)

    @property
    def pair_alpha_3(self):
        return '%s-%s' % (self.source_alpha_3, self.target_alpha_3)

    @property
    def pair_inverse(self):
        return '%s-%s' % (self.target, self.source)
      
    @property
    def has_pair(self):
        return self.source is not None and self.target is not None
      
    @abstractmethod
    def translate(self, input):
        return input
