from unittest import TestCase
from kegg_map_wizard.KeggMapWizard import KeggMapWizard, KeggMap, KeggShape, KeggAnnotation
from kegg_map_wizard.KeggShape import Poly, Circle, Rect, Line
import os
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


def mk_or_empty_dir(dir: str):
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    os.mkdir(dir)
    return dir


def run_wizard(org, color_function=None, dirname: str = None, with_bboxes: bool = False):
    if not dirname:
        assert type(org) is str
        dirname = org

    out_path = mk_or_empty_dir(f'{PACKAGE_ROOT}/tests/out/{dirname}')

    if type(org) is list:
        kmw = KeggMapWizard.merge_organisms(organisms=org)
    else:
        kmw = KeggMapWizard(org=org)

    if color_function:
        kmw.set_color_function(color_function)

    for map in kmw.maps():
        print(map)
        map.save(out_path=f'{out_path}/{kmw.org}{map.map_id}.svg', with_bboxes=with_bboxes)


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


class TestKeggMapWizard(TestCase):
    def test_download_rest_files(self):
        kmw = KeggMapWizard(org='ko')
        kmw.download_rest_data(reload=False)

    # def test_reload_map(self):
    #     kmw = KeggMapWizard(org='ko')
    #     kmw.download_map('00400', reload=True)

    def test_get_map(self):
        kmw = KeggMapWizard(org='ko')
        kmw.get_map('00400')
        with self.assertRaises(AssertionError):
            kmw.get_map('00000')

    def test_kegg_annotation(self):
        kmw = KeggMapWizard(org='ko')
        kas = KeggAnnotation.generate(kmw, url='/kegg-bin/show_pathway?map00905')
        for position, ka in kas.items():
            print(position, ka, ka.description)

    def test_kegg_shape(self):
        kmw = KeggMapWizard(org='ko')
        ks = KeggShape.generate(
            kmw.get_map('00400'),
            'rect (332,725) (378,742)	/dbget-bin/www_bget?K00832+K00838	K00832 (tyrB), K00838 (ARO8)'
        )
        print(ks)

    def test_map_shapes(self):
        kmw = KeggMapWizard(org='ko')
        for m in kmw.maps():
            kss = m.shapes()
            for ks in kss:
                pass

    def test_map_anno(self):
        kmw = KeggMapWizard(org='ko')
        m = kmw.get_map(map_id='01058')
        kss = m.shapes()
        for ks in kss:
            for anno in ks.annotations():
                print(anno, anno.description)

    def test_map_annos(self):
        kmw = KeggMapWizard(org='ko')
        for m in kmw.maps():
            print(m)
            kss = m.shapes()
            for ks in kss:
                for anno in ks.annotations():
                    x = anno.description

    def test_render_single_map(self):
        out_path = mk_or_empty_dir(f'{PACKAGE_ROOT}/tests/out/single_map')

        map_id = '01110'  # problematic map: 04930

        kmw = KeggMapWizard(org='ko')
        kmw.set_color_function(color_function_test)

        map = kmw.get_map(map_id)
        map.save(out_path=f'{out_path}/{kmw.org}{map_id}.svg')

    def test_render_key_maps(self):
        out_path = mk_or_empty_dir(f'{PACKAGE_ROOT}/tests/out/key_maps')

        map_ids = ['00400', '00601', '01110', '01240', '04723', '04930']

        kmw = KeggMapWizard(org='ko')
        kmw.set_color_function(color_function_multigroups)
        for map_id in map_ids:
            map = kmw.get_map(map_id)
            map.save(out_path=f'{out_path}/{kmw.org}{map_id}.svg', with_bboxes=True)

    def test_render_all_maps_ko_transparent(self):
        run_wizard(org='eco', dirname='ko-transparent')

    def test_render_all_maps_ko(self):
        run_wizard(org='ko', color_function=color_function_test, with_bboxes=True)

    def test_render_all_maps_rn(self):
        run_wizard(org='rn', color_function=color_function_test)

    def test_render_all_maps_ec(self):
        run_wizard(org='ec', color_function=color_function_test)

    def test_render_all_maps_hsa(self):
        run_wizard(org='hsa', color_function=color_function_test)

    def test_render_all_maps_eco(self):
        run_wizard(org='eco', color_function=color_function_test)

    def test_merge_organisms(self):
        run_wizard(dirname='merge', org=['ko', 'rn', 'ec'], color_function=color_function_test)

    def test_merge_organisms_transparent(self):
        run_wizard(dirname='merge-transparent', org=['ko', 'rn', 'ec'])

    def test_map_to_annos(self):
        kmw = KeggMapWizard.merge_organisms(organisms=['ko', 'rn', 'ec'])
        # maps = [kmw.get_map(map_id=map_id) for map_id in ['00400', '00790', '00380']]
        maps = kmw.maps()
        print(len(maps))
        # [a.name for map in maps for shape in map.shapes() for a in shape.annotations()]
        res = {map.map_id: [a.name for shape in map.shapes() for a in shape.annotations()] for map in maps}
        import json
        with open('/home/thomas/Downloads/map_to_annos.json', 'w') as f:
            json.dump(res, f, indent=4)
