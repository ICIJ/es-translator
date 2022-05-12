from unittest import TestCase
from es_translator.interpreters import Argos

class TestArgos(TestCase):
  
    def test_has_eng_to_spa_is_supported(self):
        self.argos = Argos(source = 'eng', target = 'spa')
        self.assertTrue(self.argos.is_pair_available)
    
    def test_has_spa_to_eng_is_supported(self):
        self.argos = Argos(source = 'spa', target = 'eng')
        self.assertTrue(self.argos.is_pair_available)
        
    def test_has_fra_to_eng_is_supported(self):
        self.argos = Argos(source = 'fra', target = 'eng')
        self.assertTrue(self.argos.is_pair_available)

    def test_has_ava_to_kau_isnt_supported(self): 
        with self.assertRaises(Exception):
          self.argos = Argos(source = 'ava', target = 'kau')
          self.assertFalse(self.argos.is_pair_available)

    def test_translation_from_fra_to_eng(self):
        self.argos = Argos(source = 'fra', target = 'eng')
        self.assertEqual(self.argos.translate('bonjour!').lower(), 'hello!')
            
    def test_translation_from_de_to_en(self):
        self.argos = Argos(source = 'fr', target = 'en')
        self.assertEqual(self.argos.translate('bonjour monsieur, comment ça va ?'), 'Hello, sir, how are you?')