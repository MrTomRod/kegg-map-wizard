import os
import re
import logging
from tempfile import NamedTemporaryFile
from typing import Callable

from kegg_map_wizard.KeggShape import KeggShape, Poly, Circle, Rect, Line
from kegg_map_wizard.kegg_utils import MAP_TEMPLATE, load_png
from kegg_map_wizard.kegg_download import encode_png
from kegg_map_wizard.KeggAnnotation import KeggAnnotation
from kegg_map_wizard.KeggShape import BBox
from kegg_map_wizard.kegg_download import map_conf_path

default_color_function = lambda shape: 'transparent'


class KeggMap:
    def __init__(self, orgs: [str], map_id: str, title: str, png_path: str):
        self.orgs = orgs
        self.map_id = map_id
        self.title = title
        self.png_path = png_path
        self.encoded_png_path = self.png_path + '.json'
        self.shapes: {str: KeggShape} = {}  # raw position -> KeggShape

        for path in (self.png_path, self.encoded_png_path):
            assert os.path.isfile(path), f'File does not exist: {path}'

        self.encoded_png, self.width, self.height = self._load_png()

    def __repr__(self):
        return f'<KeggMap: {self.org_string}{self.map_id} - {self.title}>'

    @property
    def id(self):
        return f'kegg-{self.org_string}-{self.map_id}-png'  # {{ map.kegg_map_wizard.org }}-{{ map.map_id }}

    @property
    def org_string(self):
        return "+".join(self.orgs)

    def color_function(self, shape: KeggShape):
        return 'transparent'

    def svg(self, color_function: Callable = None, calculate_bboxes: bool = True) -> str:
        if color_function is None:
            color_function = default_color_function
        if calculate_bboxes:
            self._load_bounding_boxes()
        try:
            svg = MAP_TEMPLATE.render(map=self, color_function=color_function)
        except Exception as e:
            e.args = tuple([f'Failed to render map: {self}!\n{str(e)}'])
            raise e
        return svg

    def save_svg(self, out_path: str, color_function: Callable = None, calculate_bboxes: bool = True):
        svg = self.svg(color_function=color_function, calculate_bboxes=calculate_bboxes)
        with open(out_path, 'w') as out:
            out.write(svg)

    def save_svgz(self, out_path: str, color_function: Callable = None, calculate_bboxes: bool = True):
        svg = self.svg(color_function=color_function, calculate_bboxes=calculate_bboxes)
        import gzip
        with gzip.open(out_path, 'w', 9) as f:
            f.write(svg.encode('utf-8'))

    def add_shapes(self, cdb_readers, map_id: str, org: str) -> None:
        config_path = map_conf_path(org, map_id)

        if not os.path.isfile(config_path):
            return

        with open(config_path) as f:
            config_file = f.readlines()

        re_org_anno = re.compile(r'^eco:b[0-9]+$') if org == 'eco' else re.compile(rf'^{org}:[0-9]+$')

        try:
            for line in config_file:
                raw_position, url, description = [l for l in line.rstrip().split('\t')]
                annotations = KeggAnnotation.create_annos(cdb_readers=cdb_readers, url=url, re_org_anno=re_org_anno, org=org)
                shape = KeggShape.create_shape(raw_position, description, annotations)
                self.add_shape(shape)
        except Exception as e:
            e.args = tuple([f'Exception occurred in {self}!\n{str(e)}'])
            raise e

    def add_shape(self, shape: KeggShape):
        # some shapes may have same position. Example: ko00010, poly (576,199,567,202,567,195)
        if shape.raw_position in self.shapes:
            # add new annotations to existing shape
            self.shapes[shape.raw_position].merge(shape)
        else:
            self.shapes[shape.raw_position] = shape

    def circles(self) -> [Circle]:
        return [s for s in self.shapes.values() if type(s) is Circle]

    def lines(self) -> [Line]:
        return [s for s in self.shapes.values() if type(s) is Line]

    def rects(self) -> [Rect]:
        return [s for s in self.shapes.values() if type(s) is Rect]

    def polys(self) -> [Poly]:
        return [s for s in self.shapes.values() if type(s) is Poly]

    def _load_png(self):
        """
        Convert white to transparent, return base64-encoded image, width and height.
        """
        if not os.path.isfile(self.png_path):
            encode_png(self.png_path)
        png_json = load_png(self.png_path)
        return png_json['image'], png_json['width'], png_json['height']

    def _load_bounding_boxes(self) -> None:
        """
        Calculate bounding boxes of all shapes.

        1) create a svg map in calculate_bboxes
        2) use PySide6.QtSvg to calculate bounding boxes
        3) add bounding boxes to shapes
        """
        from PySide6 import QtSvg

        with NamedTemporaryFile(mode='w') as tmp_svg:
            tmp_svg.write(MAP_TEMPLATE.render(map=self, color_function=default_color_function, load_bbox_mode=True))
            tmp_svg.flush()
            svg_renderer = QtSvg.QSvgRenderer()
            svg_renderer.load(tmp_svg.name)
            for raw_position, shape in self.shapes.items():
                qrectf = svg_renderer.boundsOnElement(shape.hash)
                shape.bbox = BBox(
                    x=qrectf.x(),
                    y=qrectf.y(),
                    width=qrectf.width(),
                    height=qrectf.height()
                )
                if shape.bbox.width == shape.bbox.height == 0:
                    logging.warning(f'Error in map={self.map_id} shape={shape.raw_position} {shape.description=}: Could not get valid bbox.')
