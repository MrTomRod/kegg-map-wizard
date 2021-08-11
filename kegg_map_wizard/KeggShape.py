import os
import re
import json
import logging
from math import ceil, floor

from kegg_map_wizard.kegg_utils import Template, LINE_TEMPLATE, RECT_TEMPLATE, POLY_TEMPLATE, CIRCLE_TEMPLATE, round_up, round_down
from kegg_map_wizard.KeggAnnotation import KeggAnnotation

ROOT = os.path.dirname(__file__)


class BBox:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def x1(self) -> float:
        return round_down(self.x)

    @property
    def x2(self) -> float:
        return round_up(self.x + self.width)

    @property
    def y1(self) -> float:
        return round_down(self.y)

    @property
    def y2(self) -> float:
        return round_up(self.y + self.height)

    def serialized(self) -> str:
        return json.dumps({'x1': self.x1, 'x2': self.x2, 'y1': self.y1, 'y2': self.y2})

    def __str__(self) -> str:
        return self.serialized()


class KeggShape:
    type: str
    re_geometry: re.Pattern
    template: Template  # jinja2.Template
    bbox: BBox = None
    definition_html: str = None

    def __init__(self, kegg_map, type, geometry, url, description, raw_position):
        self.kegg_map = kegg_map
        self.type = type  # 'rect', 'poly' or 'circle'
        self.url = url
        self.description = description
        self.raw_position = raw_position
        self.hash = str(hash(raw_position))

        assert self.re_geometry.match(geometry) is not None, \
            f'Error in {self}: geometry {repr(geometry)} does not match regex!'

        try:
            self.coords = self.calc_geometry(geometry)
        except Exception as e:
            e.args = tuple([f'Error occurred while parsing geometry: {repr(geometry)}\n{str(e)}'])
            raise e

        self.annotations_dict = KeggAnnotation.generate(self.kegg_map.kegg_map_wizard, url)

    def __str__(self):
        return self.description

    def annotations(self) -> list:
        return list(self.annotations_dict.values())

    def color(self) -> str:
        return self.kegg_map.kegg_map_wizard.color_function(shape=self)

    def classes(self):
        classes = set(anno.html_class for anno in self.annotations())
        if len(classes) > 1:
            print('Weird. A shape should have only one class.', self, classes)
        return classes

    def annotations_serialized(self) -> str:
        return json.dumps([anno.as_dict() for anno in self.annotations()])

    def svg(self):
        try:
            return self.template.render(shape=self)
        except Exception as e:
            e.args = tuple([f'Failed to render shape: {self}!\n{str(e)}'])
            raise e

    @staticmethod
    def generate(kegg_map, line: str):  # -> KeggShape
        try:
            raw_position, url, description = [l for l in line.rstrip().split('\t')]
            shape_type, geometry = raw_position.split(' ', maxsplit=1)

            if shape_type in ['circle', 'filled_circ', 'circ']:
                return Circle(kegg_map, shape_type, geometry, url, description, raw_position)
            elif shape_type == 'rect':
                return Rect(kegg_map, shape_type, geometry, url, description, raw_position)
            elif shape_type == 'poly':
                return Poly(kegg_map, shape_type, geometry, url, description, raw_position)
            elif shape_type == 'line':
                return Line(kegg_map, shape_type, geometry, url, description, raw_position)
            else:
                raise AssertionError(f'Line does not match any type: {shape_type}')

        except Exception as e:
            e.args = tuple([f'Exception occurred in this line: {repr(line)}!\n{str(e)}'])
            raise e

    def calc_geometry(self, geometry: str):
        raise NotImplementedError('This is an abstract class!')

    def merge(self, other_shape, expect_duplicates=True):
        my_annos = self.annotations_dict
        for key, other_anno in other_shape.annotations_dict.items():
            if key in my_annos:
                if expect_duplicates:
                    logging.info(f'Duplicate annotations: {other_anno} in {self.kegg_map} at {self.raw_position}')
            else:
                self.annotations_dict[key] = other_anno


class Poly(KeggShape):
    type = 'poly'
    re_geometry = re.compile(r'^([(,][0-9]+)+\)$')  # (341,292,332,295,332,288), (670,909,661,912,664,909,661,905)
    template = POLY_TEMPLATE

    def calc_geometry(self, geometry: str) -> str:
        # x1,y1,x2,y2,..,xn,yn 	Specifies the coordinates of the edges of the polygon.
        coords = geometry[1:-1].split(',')
        for c in coords:
            assert c.isdigit(), f'Error in {self}: geometry contains non-integer! {geometry}'
        assert len(coords) % 2 == 0, f'number of polygon coordinates must be odd! {geometry} -> {coords}'
        return ",".join([str(c) for c in coords])


class Circle(KeggShape):
    type = 'circle'
    re_geometry = re.compile(r'^\([0-9]+,[0-9]+\) [0-9]+$')  # (246,236) 4
    template = CIRCLE_TEMPLATE

    def calc_geometry(self, geometry: str) -> str:
        cx, cy, r = [int(i) for i in geometry[1:].replace(') ', ',').split(',')]
        return f'cx="{cx}" cy="{cy}" r="{r}"'


class Rect(KeggShape):
    type = 'rect'
    re_geometry = re.compile(r'^\([0-9]+,[0-9]+\) \([0-9]+,[0-9]+\)$')  # (259,192) (305,209)
    template = RECT_TEMPLATE

    def calc_geometry(self, geometry: str) -> str:  # '(620,271) (666,288)' -> []
        coords = geometry[1:-1].replace(') (', ',')
        x, y, rx, ry = [int(i) for i in coords.split(',')]
        w, h = rx - x, ry - y

        # minor adjustment
        if w > 46 and h > 17:
            x = x + 1
            y = y + 1
            r = 10
        else:
            r = 0

        return f'x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}"'


class Line(Rect):
    type = 'line'
    re_geometry = re.compile(r'^\([0-9]+(,[0-9]+)+\) [0-9]+$')  # '(138,907,158,907) 2' or longer: '(723,2164,775,2164,775,2164) 3'
    template = LINE_TEMPLATE

    def calc_geometry(self, geometry: str) -> str:  # '(138,907,158,907) 2' -> 'M 138.0,907.0 L 158.0,907.0'
        geometry, radius = geometry.rsplit(' ', maxsplit=1)
        coords = [int(i) for i in geometry[1:-1].split(',')]  # convert to int to catch errors
        assert len(coords) % 2 == 0, f'number of polygon coordinates must be odd! {geometry} -> {coords}'
        points = [(coords[l * 2], coords[l * 2 + 1]) for l in range(len(coords) // 2)]
        path = 'M ' + ' L '.join(f'{x},{y}' for x, y in points)
        return path
