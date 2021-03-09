import logging
from functools import cached_property
from kegg_map_wizard.KeggShape import *
from kegg_map_wizard.kegg_utils import encode_png, load_png, MAP_TEMPLATE

ROOT = os.path.dirname(__file__)

DATA_DIR = os.environ.get('KEGG_MAP_WIZARD_DATA')
if DATA_DIR is None:
    logging.info(msg='Environment variable KEGG_MAP_WIZARD_DATA is not set.')
    DATA_DIR = f'{os.path.dirname(ROOT)}/data'
    os.makedirs(DATA_DIR, exist_ok=True)


class KeggMap:
    _shapes = None

    def __init__(self, kegg_map_wizard, map_id: str):
        self.kegg_map_wizard = kegg_map_wizard
        self.map_id = map_id
        self.title = kegg_map_wizard.map_id_to_description[map_id]
        self._png_path = kegg_map_wizard.map_png_path(map_id)
        encoded_png_path = self._png_path + '.json'

        self._config_path = kegg_map_wizard.map_conf_path(map_id)

        for path in (self._png_path, self._config_path, encoded_png_path):
            assert os.path.isfile(path), F'File does not exist: {path}'

        self._png, self._width, self._height = None, None, None

    def __repr__(self):
        return f'<KeggMap {self.kegg_map_wizard.org}{self.map_id}: {self.title}>'

    def shapes(self) -> [KeggShape]:
        return self.shapes_dict().values()

    def shapes_dict(self) -> dict[str, KeggShape]:
        if self._shapes is None:
            self.__load_shapes()
        return self._shapes

    def __load_shapes(self):
        with open(self._config_path) as f:
            config_file = f.readlines()

        try:
            shapes = [KeggShape.generate(self, line) for line in config_file]
        except Exception as e:
            e.args = tuple([f'Exception occurred in {self}!\n{str(e)}'])
            raise e

        # some shapes may have same position. Example: ko00010, poly (576,199,567,202,567,195)
        self._shapes: dict[str, KeggShape] = {}
        for shape in shapes:
            assert type(shape) in [Circle, Rect, Line, Poly], 'sanity check'
            if shape.raw_position in self._shapes:
                # add new annotations to existing shape
                self._shapes[shape.raw_position].merge(shape)
            else:
                self._shapes[shape.raw_position] = shape

    @property
    def circles(self) -> [Circle]:
        return [s for s in self.shapes() if type(s) is Circle]

    @property
    def lines(self) -> [Line]:
        return [s for s in self.shapes() if type(s) is Line]

    @property
    def rects(self) -> [Rect]:
        return [s for s in self.shapes() if type(s) is Rect]

    @property
    def polys(self) -> [Poly]:
        return [s for s in self.shapes() if type(s) is Poly]

    @property
    def png(self) -> str:
        if self._png is None:
            self.__load_png()
        return self._png

    @property
    def width(self) -> str:
        if self._width is None:
            self.__load_png()
        return self._width

    @property
    def height(self) -> str:
        if self._height is None:
            self.__load_png()
        return self._height

    def __load_png(self):
        """
        Convert white to transparent, return base64-encoded image, width and height.
        """
        try:
            png_json = load_png(self._png_path)
        except FileNotFoundError:
            encode_png(self._png_path)
            png_json = load_png(self._png_path)

        self._png = png_json['image']
        self._width = png_json['width']
        self._height = png_json['height']

    def svg(self) -> str:
        try:
            return MAP_TEMPLATE.render(map=self)
        except Exception as e:
            e.args = tuple([f'Failed to render shape: {self}!\n{str(e)}'])
            raise e

    def save(self, out_path: str, svgz: bool = False):
        svg = self.svg()
        if svgz:
            import gzip
            with gzip.open(out_path, 'w', 9) as f:
                f.write(svg.encode('utf-8'))
        else:
            with open(out_path, 'w') as out:
                out.write(svg)

    def merge(self, other_map):
        assert self is not other_map and self.map_id == other_map.map_id
        my_shapes = self.shapes_dict()
        for raw_position, other_shape in other_map.shapes_dict().items():
            other_shape:KeggShape
            if raw_position in my_shapes:
                my_shapes[raw_position].merge(other_shape, expect_duplicates=True)
            else:
                my_shapes[raw_position]=other_shape
