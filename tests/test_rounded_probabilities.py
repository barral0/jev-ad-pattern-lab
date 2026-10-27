import unittest
from pydantic import ValidationError
from inference import ChoiceAnswer

class RoundedNativeProbabilities(unittest.TestCase):
    def test_accepts_two_decimal_rounding_without_changing_values(self):
        probabilities={'Talking head':0.09,'Graphic':0.0,'Mixed':0.56,'UGC':0.02,'B-roll':0.32}
        result=ChoiceAnswer(type='choice',choice='Mixed',confidence=0.6,probabilities=probabilities)
        self.assertEqual(result.probabilities,probabilities)

    def test_rejects_materially_incomplete_distribution(self):
        with self.assertRaises(ValidationError):
            ChoiceAnswer(type='choice',choice='a',confidence=0.6,probabilities={'a':0.6,'b':0.2})

    def test_accepts_choice_one_rounding_step_below_the_top_probability(self):
        # Resposta nativa real: choice=convenience (0.47) e performance (0.48); arredondamento a duas casas.
        probabilities={'business_growth':0.0,'education':0.0,'convenience':0.47,'price':0.04,'experience':0.0,'performance':0.48,'trust':0.01,'identity':0.0,'unknown':0.0}
        result=ChoiceAnswer(type='choice',choice='convenience',confidence=0.42,probabilities=probabilities)
        self.assertEqual(result.probabilities,probabilities)
        self.assertEqual(result.choice,'convenience')

    def test_rejects_choice_materially_below_the_top_probability(self):
        with self.assertRaises(ValidationError):
            ChoiceAnswer(type='choice',choice='a',confidence=0.4,probabilities={'a':0.3,'b':0.7})
        with self.assertRaises(ValidationError):
            ChoiceAnswer(type='choice',choice='a',confidence=0.4,probabilities={'a':0.45,'b':0.55})
