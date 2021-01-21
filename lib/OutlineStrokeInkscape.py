import time
import pexpect
from tempfile import NamedTemporaryFile


# 3x slower than OutlineStrokeJsLib, but arguably better quality
# view logs: tail -f /tmp/inkscape-outline-bot.txt
class OutlineStrokeInkscape:
    def __init__(self):
        # only start inkscape when necessary
        self.p = None

    def __load(self):
        if self.p is None:
            self.p = pexpect.spawn('inkscape -g --shell')
            self.p.logfile = open('/tmp/inkscape-outline-bot.txt', 'ab')
            self.p.expect('>')

    def __del__(self):
        if self.p is None:
            return

        print('Shutting down Inkscape gracefully.')
        self.p.sendline('window-close;')
        time.sleep(0.5)
        self.p.sendline('quit')
        time.sleep(2)
        self.p.kill(0)
        time.sleep(0.5)
        self.p.close()

    def outline_svg(self, svg: str) -> str:
        self.__load()
        with NamedTemporaryFile(mode='w', suffix='.svg') as f:
            f.write(svg)
            f.flush()
            self.p.sendline(f'file-open:{f.name};window-open;select-all;verb:StrokeToPath;verb:FileSave;verb:FileClose;')
            self.p.expect('>')
            import time
            time.sleep(3)
            with open(f.name) as of:
                output = of.read()
        assert svg != output, 'Error in outline_svg: Inkscape had no effect on svg!'
        return output

    def outline_path(self, path: str, stroke_width: int, svg_width: int, svg_height: int) -> str:
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">
            <path d="{path}"
            stroke="black" stroke-width="{stroke_width}" fill="none"/>
        </svg>'''
        outlined_svg = self.outline_svg(svg)
        return self.extract_path(outlined_svg)

    @staticmethod
    def extract_path(svg: str) -> str:
        path = svg.split('     d="', maxsplit=1)[1].split('"\n', maxsplit=1)[0].upper()
        for bad_symbol in ['\n', '"', '=', '<', '>']:
            assert bad_symbol not in path, f'Failed to extract path:\n{svg=}\n{path=}'
        assert len(path) > 4, f'Failed to extract path:\n{svg=}\n{path=}'
        return path


if __name__ == '__main__':
    o_s = OutlineStrokeInkscape()

    test_input = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="4868" height="3178">
        <path d="M 4318,1518 L 4326,1518 L 4326,1518 L 4329,1518 L 4331,1519 L 4334,1520 L 4336,1522 L 4338,1524 L 4340,1526 L 4341,1529 L 4342,1531 L 4342,1534 L 4342,1534 L 4342,1591 L 4342,1591 L 4342,1594 L 4341,1596 L 4340,1599 L 4338,1601 L 4336,1603 L 4334,1605 L 4331,1606 L 4329,1607 L 4326,1607 L 4326,1607 L 4318,1607"
        stroke="black" stroke-width="10" fill="none"/>
    </svg>'''

    print('testing outline_svg')
    out_svg = o_s.outline_svg(svg=test_input)

    print('testing extract_path')
    out_path = o_s.extract_path(svg=out_svg)

    print('testing outline_path')
    path = o_s.outline_path(
        path='M 4318,1518 L 4326,1518 L 4326,1518 L 4329,1518 L 4331,1519 L 4334,1520 L 4336,1522 L 4338,1524 L 4340,1526 L 4341,1529 L 4342,'
             '1531 L 4342,1534 L 4342,1534 L 4342,1591 L 4342,1591 L 4342,1594 L 4341,1596 L 4340,1599 L 4338,1601 L 4336,1603 L 4334,1605 L 4331,'
             '1606 L 4329,1607 L 4326,1607 L 4326,1607 L 4318,1607',
        svg_width=4868, svg_height=3178, stroke_width=10
    )

    assert out_path == path

    from OutlineStrokeJsLib import OutlineStrokeJsLib

    o_s_ = OutlineStrokeJsLib()
    other_path = o_s_.outline_path(
        path='M 4318,1518 L 4326,1518 L 4326,1518 L 4329,1518 L 4331,1519 L 4334,1520 L 4336,1522 L 4338,1524 L 4340,1526 L 4341,1529 L 4342,'
             '1531 L 4342,1534 L 4342,1534 L 4342,1591 L 4342,1591 L 4342,1594 L 4341,1596 L 4340,1599 L 4338,1601 L 4336,1603 L 4334,1605 L 4331,'
             '1606 L 4329,1607 L 4326,1607 L 4326,1607 L 4318,1607',
        svg_width=4868, svg_height=3178, stroke_width=10
    )

    print('\n'.join([out_path, path, other_path]))
