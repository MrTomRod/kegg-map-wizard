from unittest import TestCase
from kegg_map_wizard.KeggMapWizard import KeggMapWizard, KeggMap, KeggShape, KeggAnnotation
from kegg_map_wizard.KeggShape import Poly, Circle, Rect, Line
import os

PACKAGE_ROOT = os.path.dirname(os.path.dirname(__file__))

type_to_color = {
    Poly: 'red',
    Circle: 'yellow',
    Rect: 'green',
    Line: 'blue'
}


def color_function_test(shape: KeggShape):
    return type_to_color[type(shape)]


class TestKeggMapWizard(TestCase):
    def setUp(self) -> None:
        self.kmw = KeggMapWizard(org='ko')
        self.kmw.download_all_maps()

    def test_download_rest_files(self):
        self.kmw.download_rest_data(reload=False)

    def test_reload_map(self):
        self.kmw.download_map('00400', reload=True)

    def test_get_map(self):
        self.kmw.get_map('00400')
        with self.assertRaises(AssertionError):
            self.kmw.get_map('00000')

    def test_kegg_annotation(self):
        kas = KeggAnnotation.generate(self.kmw, url='/kegg-bin/show_pathway?map00905')
        for ka in kas:
            print(ka, ka.description)

    def test_kegg_shape(self):
        ks = KeggShape.generate(
            self.kmw.get_map('00400'),
            'rect (332,725) (378,742)	/dbget-bin/www_bget?K00832+K00838	K00832 (tyrB), K00838 (ARO8)'
        )
        print(ks)

    def test_map_shapes(self):
        for m in self.kmw.maps():
            kss = m.shapes
            for ks in kss:
                pass

    def test_map_anno(self):
        m = self.kmw.get_map(map_id='01058')
        kss = m.shapes
        for ks in kss:
            for anno in ks.annotations:
                print(anno, anno.description)

        print('done')

    def test_map_annos(self):
        for m in self.kmw.maps():
            print(m)
            kss = m.shapes
            for ks in kss:
                for anno in ks.annotations:
                    x = anno.description

        print('done')

    def test_render_single_map(self):
        map_id = '01110'  # problematic map: 04930

        self.kmw.color_function = color_function_test

        map = self.kmw.get_map(map_id)
        svg = map.svg()
        map.save(out_path=f'{PACKAGE_ROOT}/tests/out/{self.kmw.org}{map_id}.svg')

    def test_render_key_maps(self):
        map_ids = ['00400', '01240', '01110', '04723', '04930']

        self.kmw.color_function = color_function_test

        for map_id in map_ids:
            map = self.kmw.get_map(map_id)
            map.save(out_path=f'{PACKAGE_ROOT}/tests/out/{self.kmw.org}{map_id}.svg')

    def test_render_all_maps_ko_transparent(self):
        for map in self.kmw.maps():
            print(map)
            svg = map.svg()
            map.save(out_path=f'{PACKAGE_ROOT}/tests/out/ko-transparent/KEGG {self.kmw.org}{map.map_id}.svg')

    def test_render_all_maps_ko(self):
        self.kmw.color_function = color_function_test

        for map in self.kmw.maps():
            print(map)
            svg = map.svg()
            map.save(out_path=f'{PACKAGE_ROOT}/tests/out/{self.kmw.org}{map.map_id}.svg')

    def test_render_all_maps_rn(self):
        kmw = KeggMapWizard(org='rn')
        kmw.download_all_maps()
        kmw.color_function = color_function_test
        for map in kmw.maps():
            print(map)
            svg = map.svg()
            map.save(out_path=f'{PACKAGE_ROOT}/tests/out/{kmw.org}{map.map_id}.svg')

    def test_render_all_maps_ec(self):
        kmw = KeggMapWizard(org='ec')
        kmw.download_all_maps()
        kmw.color_function = color_function_test
        for map in kmw.maps():
            print(map)
            svg = map.svg()
            map.save(out_path=f'{PACKAGE_ROOT}/tests/out/{kmw.org}{map.map_id}.svg')

    def test_render_all_maps_hsa(self):
        kmw = KeggMapWizard(org='hsa')
        kmw.download_all_maps()
        kmw.color_function = color_function_test
        for map in kmw.maps():
            print(map)
            svg = map.svg()
            map.save(out_path=f'{PACKAGE_ROOT}/tests/out/{kmw.org}{map.map_id}.svg')

    def test_render_all_maps_eco(self):
        kmw = KeggMapWizard(org='eco')
        kmw.download_all_maps()
        kmw.color_function = color_function_test
        for map in kmw.maps():
            print(map)
            svg = map.svg()
            map.save(out_path=f'{PACKAGE_ROOT}/tests/out/{kmw.org}{map.map_id}.svg')
