from random import randint

GRADIENT_TEMPLATE = '''
<linearGradient id="{id}" gradientUnits="userSpaceOnUse" x1="{x1}" x2="{x2}">
{stops}
</linearGradient>
'''.replace('\n', '')

STOP_TEMPLATE = '''
<stop offset="{offset:.4g}%" stop-color="{color_1}"></stop><stop offset="{offset:.4g}%" stop-color="{color_2}"></stop>
'''.replace('\n', '')


class ColorMaker:
    GRADIENT_TEMPLATE = GRADIENT_TEMPLATE
    STOP_TEMPLATE = STOP_TEMPLATE

    @staticmethod
    def _calculate_offset(i: int, n_colors: int) -> float:
        """
        Calculate where color change should happen.

        Example:
          - Color 1 out of 4 should end at 25 %.
          - Color 2 out of 4 should end at 50 %.
          - Color 3 out of 4 should end at 75 %.
          - Color 4 out of 4 should end at 100 %.

        :param i: index of the color
        :param n_colors: number of colors
        :return: offset in percent
        """
        assert 1 <= i <= n_colors, f'{i}'
        return 100 * i / n_colors

    @classmethod
    def svg_gradient(cls, colors: [str], id: str, x1: int, x2: int) -> str:
        """
        Returns a color gradient in SVG format.

        :param colors: list of colors
        :param id: desired id of the gradient
        :param x1: start position of gradient
        :param x2: end position of gradient
        :return: string in SVG format
        """
        stops = [
            cls.STOP_TEMPLATE.format(
                offset=cls._calculate_offset(i, len(colors)),
                color_1=colors[i - 1],
                color_2=colors[i]
            )
            for i in range(1, len(colors))]

        return cls.GRADIENT_TEMPLATE.format(id=id, x1=x1, x2=x2, stops=''.join(stops))

    @staticmethod
    def random_color():
        return f'#{randint(0, 255):02X}{randint(0, 255):02X}{randint(0, 255):02X}'
