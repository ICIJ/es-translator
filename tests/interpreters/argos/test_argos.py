from unittest import TestCase
from es_translator.interpreters import Argos

class TestArgos(TestCase):
    @classmethod
    def setUpClass(self):
        self.spa2eng = Argos(source = 'spa', target = 'eng')
        self.eng2spa = Argos(source = 'eng', target = 'spa')
        self.fra2eng = Argos(source = 'fra', target = 'eng')
  
    def test_has_eng_to_spa_is_supported(self):
        self.assertTrue(self.eng2spa.is_pair_available)
    
    def test_has_spa_to_eng_is_supported(self):
        self.assertTrue(self.spa2eng.is_pair_available)
        
    def test_has_fra_to_eng_is_supported(self):
        self.assertTrue(self.fra2eng.is_pair_available)

    def test_has_ava_to_kau_isnt_supported(self): 
        with self.assertRaises(Exception):
          self.argos = Argos(source = 'ava', target = 'kau')
          self.assertFalse(self.argos.is_pair_available)

    def test_translation_from_fra_to_eng(self):
        self.assertEqual(self.fra2eng.translate('bonjour!').lower(), 'hello!')
            
    def test_translation_from_de_to_en(self):
        self.assertEqual(self.fra2eng.translate('bonjour monsieur, comment ça va ?'), 'Hello, sir, how are you?')