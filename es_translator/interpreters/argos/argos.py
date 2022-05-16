from argostranslate import package as argospackage
from argostranslate import translate as argostranslate
from argostranslate.utils import logger as argoslogger

from ..abstract import AbstractInterpreter
from ...logger import logger

class ArgosPairNotAvailable(Exception): pass

class Argos(AbstractInterpreter):
    name = 'ARGOS'
        
    def __init__(self, source = None, target = None, intermediary = None, pack_dir = None):
        super().__init__(source, target)
        # Raise an exception if an intermediary language is provded
        if intermediary is not None:
            logger.warn('Argos interpreter doesnt support intermediary language')
        if pack_dir is not None:
            logger.warn('Argos interpreter doesnt support custom pack directory')
        # Raise an exception if the language pair is unkown
        if not self.is_pair_available and self.has_pair:
            try:
                self.download_necessary_languages()
            except ArgosPairNotAvailable:
                raise Exception('The pair %s is not available' % self.pair)
        else:
            logger.info('Existing package(s) found for pair %s' % self.pair)
    
    @property    
    def is_pair_available(self):
        for package in argospackage.get_installed_packages():
            if package.from_code == self.source_alpha_2 and package.to_code == self.target_alpha_2:
                return True
        return False
    
    @property
    def local_languages(self):        
        try:
            installed_languages = argostranslate.get_installed_languages()
            return [ lang.code for lang in installed_languages ]
        except AttributeError:
            return []
    
    def download_necessary_languages(self):
        argospackage.update_package_index()
        for package in argospackage.get_available_packages():
            if package.from_code == self.source_alpha_2 and package.to_code == self.target_alpha_2:
                download_path = package.download()
                return argospackage.install_from_path(download_path)
        raise ArgosPairNotAvailable
    
    @property
    def translation(self):
        installed_languages = argostranslate.get_installed_languages()
        source = list(filter(lambda x: x.code == self.source_alpha_2, installed_languages))[0]
        target = list(filter(lambda x: x.code == self.target_alpha_2, installed_languages))[0]
        return source.get_translation(target)
    
    def translate(self, input):
        return self.translation.translate(input)