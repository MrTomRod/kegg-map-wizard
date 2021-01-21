import os
from subprocess import run, PIPE
from tempfile import NamedTemporaryFile


# about 3x faster than OutlineStrokeInkscape
class OutlineStrokeJsLib:
    def __init__(self):
        # install outline-stroke standalone
        self.ROOT = os.path.dirname(os.path.abspath(__file__))
        self.bin = self.ROOT + '/outline-stroke-cli-1.1.1/outline-stroke-cli-linux'
        if not os.path.isfile(self.bin):
            cmd = ['tar', '-Jxvf', 'outline-stroke-cli-1.1.1.tar.xz']
            print(f'installing outline-stroke... ({" ".join(cmd)})')
            subprocess = run(cmd, cwd=self.ROOT, stdout=PIPE, stderr=PIPE, encoding='ascii')
            error_message = F'could execute command {cmd}\n stdout: {subprocess.stdout},\n stderr: {subprocess.stderr}'
            assert subprocess.stderr == '', error_message
            assert subprocess.returncode == 0, error_message

        assert os.path.isfile(self.bin), f'Failed to install outline-stroke! ({self.bin} does not exist.)'

    def outline_svg(self, svg: str) -> str:
        with NamedTemporaryFile(mode='w', suffix='.svg') as f:
            f.write(svg)
            f.flush()
            cmd = [self.bin, f.name]
            subprocess = run(cmd, cwd=self.ROOT, stdout=PIPE, stderr=PIPE, encoding='ascii')
            error_message = f'Failed to outline_path. {cmd=} {svg=}'
            assert subprocess.stderr == '', error_message
            assert subprocess.returncode == 0, error_message
            assert subprocess.stdout != '', error_message
        return subprocess.stdout

    def outline_path(self, path: str, stroke_width: int, svg_width: int, svg_height: int) -> str:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}">
        <path d="{path}" stroke="black" stroke-width="{stroke_width}" fill="none"/>
        </svg>'''
        outlined_svg = self.outline_svg(svg)
        return self.extract_path(outlined_svg)

    @staticmethod
    def extract_path(svg: str) -> str:
        path = svg.split('<path d="', maxsplit=1)[1].split('" stroke="', maxsplit=1)[0].rstrip()
        for bad_symbol in ['\n', '"', '=', '<', '>']:
            assert bad_symbol not in path, f'Failed to extract path:\n{svg=}\n{path=}'
        assert len(path) > 4, f'Failed to extract path:\n{svg=}\n{path=}'
        return path


if __name__ == '__main__':
    o_s = OutlineStrokeJsLib()

    test_input_1 = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="160" height="140" viewBox="0 0 160 140">
        <line x1="40" x2="120" y1="20" y2="20" stroke="black" stroke-width="20" stroke-linecap="butt"/>
        <line x1="40" x2="120" y1="60" y2="60" stroke="black" stroke-width="20" stroke-linecap="square"/>
        <line x1="40" x2="120" y1="100" y2="100" stroke="black" stroke-width="20" stroke-linecap="round"/>
    </svg>'''

    test_input_2 = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="4868" height="3178">
        <path d="M 4318,1518 L 4326,1518 L 4326,1518 L 4329,1518 L 4331,1519 L 4334,1520 L 4336,1522 L 4338,1524 L 4340,1526 L 4341,1529 L 4342,1531 L 4342,1534 L 4342,1534 L 4342,1591 L 4342,1591 L 4342,1594 L 4341,1596 L 4340,1599 L 4338,1601 L 4336,1603 L 4334,1605 L 4331,1606 L 4329,1607 L 4326,1607 L 4326,1607 L 4318,1607"
        stroke="black" stroke-width="10" fill="none"/>
    </svg>'''

    for test_input in (test_input_1, test_input_2):
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

    assert path == out_path
