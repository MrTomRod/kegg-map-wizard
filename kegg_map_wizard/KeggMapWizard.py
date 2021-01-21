import os
import re
import logging
from functools import cached_property

from kegg_map_wizard.kegg_utils import get_cdb, fetch_all, ANNOTATION_SETTINGS
from kegg_map_wizard.KeggMap import KeggMap, KeggShape, KeggAnnotation
from kegg_map_wizard.KeggAnnotation import InvalidAnnotationException
from jinja2 import Template  # pip install Jinja2

ROOT = os.path.dirname(__file__)

DATA_DIR = os.environ.get('KEGG_MAP_WIZARD_DATA')
if DATA_DIR is None:
    logging.info(msg='Environment variable KEGG_MAP_WIZARD_DATA is not set.')
    DATA_DIR = f'{os.path.dirname(ROOT)}/data'


def load_template(name: str) -> Template:
    with open(f'{ROOT}/template/{name}.svg') as f:
        template = f.read()
        return Template(template)


class KeggMapWizard:
    MAP_TEMPLATE = load_template('map')
    LINE_TEMPLATE = load_template('line')
    RECT_TEMPLATE = load_template('rect')
    POLY_TEMPLATE = load_template('poly')
    CIRCLE_TEMPLATE = load_template('circle')

    def __init__(self, org='ko', n_parallel=6, reload_rest_data=False):
        self.org = org
        if org == 'eco':
            self.re_org_anno = re.compile(r'^eco:b[0-9]+$')  # 'eco:b2286'
        else:
            self.re_org_anno = re.compile(rf'^{org}:[0-9]+$')  # 'ko:15988'
        self._n_parallel = n_parallel

        for dir in (
                F'{DATA_DIR}/rest_data',
                F'{DATA_DIR}/maps_png/',
                F'{DATA_DIR}/maps_data/{org}'
        ):
            os.makedirs(dir, exist_ok=True)

        self.download_rest_data(reload=reload_rest_data)

    def __str__(self):
        return f'<KeggMapWizard: {self.org} ({len(self.map_ids)} maps)>'

    @staticmethod
    def color_function(shape: KeggShape):
        return 'transparent'

    def maps(self) -> [KeggMap]:
        for map_id in self.map_id_to_description.keys():
            map_png = self.map_png_path(map_id)
            map_json = map_png + '.json'
            map_conf = self.map_conf_path(map_id)
            if os.path.isfile(map_png) and os.path.isfile(map_conf):
                assert os.path.isfile(map_json), f'File {map_png} has no corresponding json file! ({map_json})'
                yield self.get_map(map_id)

    def get_map(self, map_id: str) -> KeggMap:
        assert map_id in self.map_ids, f'There is no map with map_id {map_id} for this organism.'
        return KeggMap(kegg_map_wizard=self, map_id=map_id)

    @cached_property
    def map_ids(self) -> [str]:
        dir = F'{DATA_DIR}/maps_data/{self.org}'
        map_ids = [filename.rstrip('.conf') for filename in os.listdir(dir) if filename.endswith('.conf')]
        for map_id in map_ids:
            assert len(map_id) == 5 and map_id.isnumeric(), f'File in {dir} '
        return map_ids

    def download_rest_data(self, reload=False) -> None:
        files = ['path', 'rn', 'compound', 'drug', 'glycan', 'dgroup', 'enzyme', 'br', 'rc', self.org]

        to_download = [
            (  # parameters for fetch function (except for session)
                self.rest_data_path(file, url=True),  # url
                self.rest_data_path(file, url=False),  # save_path
                False,  # raw
                True  # create cdb
            )
            # dict(url=F'http://rest.kegg.jp/list/{file}', save_path=F'{self.KEGG_REST_PATH}/{file}.tsv', raw=False)
            for file in files
        ]

        fetch_all(args_list=to_download, n_parallel=self._n_parallel, reload=reload)

        for args in to_download:
            assert os.path.isfile(args[1]), F'failed to download {args}'

        self.files = {file: get_cdb(self.rest_data_path(file)) for file in files}

    def download_all_maps(self, reload=False):
        all_map_ids = self.map_id_to_description.keys()
        self.download_maps(map_ids=all_map_ids, reload=reload)

    def download_map(self, map_id: str, reload=False):
        self.download_maps([map_id], reload=reload, nonexistent_file=False)

    def download_maps(self, map_ids: [str], reload=False, nonexistent_file=True) -> None:
        self.__download_map_pngs(map_ids, reload=reload)
        found_maps = [map.rstrip('.png') for map in os.listdir(F'{DATA_DIR}/maps_png') if map.endswith('.png')]
        self.__download_map_confs(found_maps, reload=reload, nonexistent_file=nonexistent_file)

    def __download_map_pngs(self, map_ids: [str], reload: bool = False) -> None:
        to_download = []
        for map_id in map_ids:
            to_download.append(
                (
                    self.map_png_path(map_id, url=True),  # url
                    self.map_png_path(map_id, url=False),  # save_path
                    True,  # raw
                    False,  # create cdb
                    True  # encode png
                )
            )

        fetch_all(args_list=to_download, n_parallel=self._n_parallel, reload=reload)

        for args in to_download:
            assert os.path.isfile(args[1]), F'failed to download {args}'

    def __download_map_confs(self, map_ids: [str], reload: bool = False, nonexistent_file=True):
        to_download = []
        for map_id in map_ids:
            to_download.append(
                (
                    self.map_conf_path(map_id, url=True),  # url
                    self.map_conf_path(map_id, url=False),  # save_path
                    False,  # raw
                    False  # create cdb
                )
            )

        if nonexistent_file:
            nonexistent_file = F'{DATA_DIR}/maps_data/{self.org}/non-existent.json'

        fetch_all(args_list=to_download, n_parallel=self._n_parallel, reload=reload,
                  nonexistent_file=nonexistent_file)

    @cached_property
    def map_id_to_description(self) -> dict:
        with open(F'{DATA_DIR}/rest_data/path.tsv', 'r') as f:
            path_file = f.readlines()  # ['path:map00010\tGlycolysis / Gluconeogenesis', ...]
        map_id_to_description = {map_id.lstrip('path:map'): title.rstrip() for map_id, title in
                                 (line.split('\t', maxsplit=1) for line in path_file)}  #

        for key in map_id_to_description.keys():
            assert len(key) == 5 and key.isnumeric()

        return map_id_to_description

    @staticmethod
    def rest_data_path(key: str, url=False) -> str:
        if url:
            return f'http://rest.kegg.jp/list/{key}'
        else:
            return f'{DATA_DIR}/rest_data/{key}.tsv'

    def map_conf_path(self, map_id: str, url=False) -> str:
        if url:
            return f'http://rest.kegg.jp/get/{self.org}{map_id}/conf'
        else:
            return F'{DATA_DIR}/maps_data/{self.org}/{map_id}.conf'

    @staticmethod
    def map_png_path(map_id: str, url=False) -> str:
        if url:
            return f'https://www.genome.jp/kegg/pathway/map/map{map_id}.png'
        else:
            return F'{DATA_DIR}/maps_png/{map_id}.png'

    def get_description(self, query: str, rest_file: str) -> str:
        """
        Use rest data to get the description of an annotation.

        :param query: query annotation
        :param rest_file: file to be searched
        :return: description. If none is found, an empty string is returned and a warning is printed.
        """
        try:
            description = self.files[rest_file].get(query.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logging.warning(f'could not find description for {query} in {rest_file}')
            return ''
        return description

    def parse_anno(self, name: str) -> KeggAnnotation:
        """
        """

        # handle organism annotations
        if self.re_org_anno.match(name):
            return KeggAnnotation(kegg_map_wizard=self, name=name, anno_type=self.org, html_class='enzyme',
                                  description=self.get_description(query=name, rest_file=self.org))

        # handle most common cases
        for anno_type, settings in ANNOTATION_SETTINGS.items():
            if settings['pattern'].match(name):
                if anno_type == 'MAP':
                    name = name[-5:]
                query = f'{settings["descr_prefix"]}{name}'
                return KeggAnnotation(
                    kegg_map_wizard=self,
                    name=name,
                    anno_type=anno_type,
                    html_class=settings['html_class'],
                    description=self.get_description(query=query, rest_file=settings['rest_file'])
                )

        # handle anomalies
        if name.startswith('dr:D'):
            # sometimes drugs contain the 'dr:' prefix
            anno_type = 'D'
            name = name.lstrip('dr:')
        elif name.startswith('htext=br'):
            # strange br: 'htext=br08003&search_string=%22Acridone%20alkaloids%22&option=-n'
            anno_type = 'BR'
            name = name.lstrip('htext=br').lstrip(':')
            name = f'br:{name[:5]}'
        elif name == 'map4670':
            # strange anomaly
            anno_type, name = 'MAP', 'map04670'
        else:
            raise InvalidAnnotationException(f'Annotation {name} does not match any pattern!')

        settings = ANNOTATION_SETTINGS[anno_type]
        assert settings['pattern'].match(name), f'annotation ({anno_type}) does not match pattern: {name}'
        if anno_type == 'MAP':
            name = name[-5:]
        query = f'{settings["descr_prefix"]}{name}'

        return KeggAnnotation(
            kegg_map_wizard=self,
            name=name,
            anno_type=anno_type,
            html_class=settings['html_class'],
            description=self.get_description(query=query, rest_file=settings['rest_file'])
        )
