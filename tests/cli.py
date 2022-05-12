from click import BadParameter
from unittest import TestCase
from es_translator.cli import validate_interpreter
from es_translator.interpreters import Apertium, Argos

class TestCli(TestCase):

    def test_it_validates_apertium_interpreter_in_uppercase(self):
        validated = validate_interpreter(None, None, 'APERTIUM')
        self.assertEqual(validated, Apertium)
        
    def test_it_validates_apertium_interpreter_in_lowercase(self):
        validated = validate_interpreter(None, None, 'apertium')
        self.assertEqual(validated, Apertium)
        
    def test_it_validates_apertium_interpreter_in_titlecase(self):
        validated = validate_interpreter(None, None, 'Apertium')
        self.assertEqual(validated, Apertium)
            
    def test_it_validates_argos_interpreter_in_uppercase(self):
        validated = validate_interpreter(None, None, 'ARGOS')
        self.assertEqual(validated, Argos)
        
    def test_it_validates_argos_interpreter_in_lowercase(self):
        validated = validate_interpreter(None, None, 'argos')
        self.assertEqual(validated, Argos)
        
    def test_it_validates_argos_interpreter_in_titlecase(self):
        validated = validate_interpreter(None, None, 'Argos')
        self.assertEqual(validated, Argos)
        
    def test_it_doesnt_validate_foo_interpreter(self):
        with self.assertRaises(BadParameter):
            validate_interpreter(None, None, 'foo')
    