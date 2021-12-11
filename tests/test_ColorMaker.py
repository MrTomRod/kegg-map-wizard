from unittest import TestCase
from kegg_map_wizard.ColorMaker import ColorMaker


class TestColorMaker(TestCase):
    def test_offset(self):
        results = []
        for i in range(6):
            try:
                results.append(ColorMaker._calculate_offset(i, 4))
                print(i, ColorMaker._calculate_offset(i, 4))
            except AssertionError:
                results.append('exception')
        self.assertEqual(results, ['exception', 25.0, 50.0, 75.0, 100.0, 'exception'])

    def test_gradient(self):
        colors = ['#1', '#2', '#3', '#4']
        result = ColorMaker.svg_gradient(colors, 'id', 11, 22)

        self.assertEqual(result, '''
<linearGradient id="id" gradientUnits="userSpaceOnUse" x1="11" x2="22">
    <stop offset="25%" stop-color="#1"></stop><stop offset="25%" stop-color="#2"></stop>
    <stop offset="50%" stop-color="#2"></stop><stop offset="50%" stop-color="#3"></stop>
    <stop offset="75%" stop-color="#3"></stop><stop offset="75%" stop-color="#4"></stop>
</linearGradient>
'''.strip())
