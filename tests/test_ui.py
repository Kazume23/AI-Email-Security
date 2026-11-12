import unittest
from streamlit.testing.v1 import AppTest
from pathlib import Path


class UITests(unittest.TestCase):
    def test_start_page(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, 'AI Email Security')
        self.assertTrue(app.button[0].disabled)

    def test_report_display(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        app.session_state['fingerprint'] = None
        app.session_state['report'] = {
            'analysis': {'verdict': 'dangerous', 'risk': 'high', 'explanation': 'Test analizy',
                         'evidence': ['Test sygnału'], 'recommendation': 'Nie odpowiadaj.'},
            'rule_signals': [], 'limitations': 'Test ograniczeń'}
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.subheader[0].value, 'Niebezpieczny')
        self.assertIn('Test analizy', [x.value for x in app.text])


if __name__ == '__main__':
    unittest.main()
