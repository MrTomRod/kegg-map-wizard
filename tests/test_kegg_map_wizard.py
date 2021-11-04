from typing import Callable
from unittest import TestCase
from kegg_map_wizard.KeggMapWizard import KeggMapWizard, KeggMap
from kegg_map_wizard.KeggShape import KeggShape
from kegg_map_wizard.KeggAnnotation import KeggAnnotation
from kegg_map_wizard.KeggShape import KeggShape, Poly, Circle, Rect, Line
import os
import re
import shutil

from random import randint

get_random_color = lambda: f'#{randint(0, 255):02X}{randint(0, 255):02X}{randint(0, 255):02X}'

PACKAGE_ROOT = os.path.dirname(os.path.dirname(__file__))

type_to_color = {
    Poly: 'red',
    Circle: 'yellow',
    Rect: 'green',
    Line: 'blue'
}


def color_function_test(shape: KeggShape):
    return type_to_color[type(shape)]


def color_function_multigroups(shape: KeggShape):
    n_colors = randint(2, 5)
    random_colors = [get_random_color() for i in range(n_colors)]
    stops = ''
    for i in range(n_colors - 1):
        offset = ((i + 1) / n_colors) * 100
        color_before = random_colors[i]
        color_after = random_colors[i + 1]
        stops += f'<stop offset="{offset}%" stop-color="{color_before}"></stop>'
        stops += f'<stop offset="{offset}%" stop-color="{color_after}"></stop>'

    shape.definition = f'''
        <linearGradient
            id="{shape.hash}"
            gradientUnits="userSpaceOnUse"
            x1="{shape.bbox.x1}" x2="{shape.bbox.x2}">
            {stops}
        </linearGradient>'''
    return f'url(#{shape.hash})'


def mk_or_empty_dir(dir: str):
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    os.mkdir(dir)
    return dir


class TestKeggMapWizard(TestCase):
    def test_download_org(self):
        kmw = KeggMapWizard(orgs=['eco'])
        kmw.download_all_maps()

    def test_single_map(self):
        kmw = KeggMapWizard(orgs=['ko'])
        map = kmw.create_map('00400')
        self.assertGreater(len(map.shapes), 0)

    def test_get_nonexistent_map(self):
        kmw = KeggMapWizard(orgs=['ko'])
        with self.assertRaises(AssertionError):
            kmw.create_map('00000')

    def test_kegg_annotations(self):
        org = 'ko'
        kmw = KeggMapWizard(orgs=[org])
        annotations = KeggAnnotation.create_annos(kmw.cdb_readers, re_org_anno=re.compile(rf'^{org}:[0-9]+$'), org=org,
                                                  url='/kegg-bin/show_pathway?map00905')
        for position, ka in annotations.items():
            print(position, ka, ka.description)

    def test_kegg_shape(self):
        org = 'ko'
        kmw = KeggMapWizard(orgs=[org])
        line = 'rect (332,725) (378,742)	/dbget-bin/www_bget?K00832+K00838	K00832 (tyrB), K00838 (ARO8)'
        raw_position, url, description = [l for l in line.rstrip().split('\t')]
        annotations = KeggAnnotation.create_annos(kmw.cdb_readers, re_org_anno=re.compile(rf'^{org}:[0-9]+$'), org=org,
                                                  url='/kegg-bin/show_pathway?map00905')
        ks = KeggShape.create_shape(raw_position, description, annotations)
        print(ks, 'with', len(ks.annotations), 'annotations')

    def test_single_map_merge(self):
        kmw = KeggMapWizard(orgs=['ko', 'rn', 'ec'])
        map = kmw.create_map('00400')
        self.assertGreater(len(map.shapes), 0)

    def test_single_map_merge_render(self):
        kmw = KeggMapWizard(orgs=['ko', 'rn', 'ec'])
        map = kmw.create_map('00400')
        svg = map.svg(color_function=lambda shape: 'fake-color-orange', calculate_bboxes=True)
        self.assertIn(member='fake-color-orange', container=svg)

    def test_render_key_maps(self):
        out_path = mk_or_empty_dir(f'{PACKAGE_ROOT}/tests/out/key_maps')

        map_ids = ['00400', '00601', '01110', '01240', '04723', '04930', '00401']

        kmw = KeggMapWizard(orgs=['ko', 'rn', 'ec'])
        for map_id in map_ids:
            map = kmw.create_map(map_id)
            map.save_svg(out_path=f'{out_path}/{kmw.org_string}{map_id}.svg', color_function=color_function_multigroups)


def run_wizard(orgs: [str], color_function: Callable = None, dirname: str = None, calculate_bboxes=True):
    kmw = KeggMapWizard(orgs=orgs)

    if not dirname:
        dirname = kmw.org_string

    out_path = mk_or_empty_dir(f'{PACKAGE_ROOT}/tests/out/{dirname}')

    for map_id in kmw._available_maps():
        map = kmw.create_map(map_id)
        map.save_svg(out_path=f'{out_path}/{kmw.org_string}{map.map_id}.svg', color_function=color_function, calculate_bboxes=calculate_bboxes)


class TestLots(TestCase):
    def test_render_all_maps_ko_transparent(self):
        run_wizard(orgs=['eco'], dirname='ko-transparent')

    def test_render_all_maps_ko(self):
        run_wizard(orgs=['ko'], color_function=color_function_test)

    def test_render_all_maps_rn(self):
        run_wizard(orgs=['rn'], color_function=color_function_test)

    def test_render_all_maps_ec(self):
        run_wizard(orgs=['ec'], color_function=color_function_test)

    def test_render_all_maps_hsa(self):
        run_wizard(orgs=['hsa'], color_function=color_function_test)

    def test_render_all_maps_eco(self):
        run_wizard(orgs=['eco'], color_function=color_function_test)

    def test_merge_organisms(self):
        run_wizard(dirname='merge', orgs=['ko', 'rn', 'ec'], color_function=color_function_test)

    def test_merge_organisms_transparent(self):
        run_wizard(dirname='merge-transparent', orgs=['ko', 'rn', 'ec'], calculate_bboxes=False)
