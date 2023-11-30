import json
import os

import requests

from kegg_map_wizard.kegg_download import DATA_DIR, download_rest_data, map_png_path, map_conf_path, fetch
from kegg_map_wizard.KeggMap import KeggMap


class KeggMapWizard:
    def __init__(self, orgs: [str]):
        self.orgs = orgs
        with requests.Session() as session:
            self.cdb_readers = download_rest_data(session, orgs=self.orgs)
        self.all_mapids: {str: str} = self.__load_all_mapids()

    def __repr__(self):
        return f'<KeggMapWizard: {self.org_string}>'

    @property
    def org_string(self):
        return "+".join(self.orgs)

    def download_configs(self, map_ids: [str] = None, reload: bool = False):
        if map_ids is None:
            map_ids = self.all_mapids.keys()

        with requests.Session() as session:
            if reload:
                download_rest_data(session=session, orgs=self.orgs)
            for org in self.orgs:
                self._download_maps(session=session, org=org, map_ids=map_ids, reload=reload)

    def create_map(self, map_id: str) -> KeggMap:
        assert map_id in self.all_mapids, f'Map {map_id} does not exist for {self}'
        map = KeggMap(orgs=self.orgs, map_id=map_id, title=self.all_mapids[map_id], png_path=map_png_path(map_id))
        self.download_configs(map_ids=[map_id])
        for org in self.orgs:
            map.add_shapes(cdb_readers=self.cdb_readers, map_id=map_id, org=org)
        return map

    def create_maps(self, map_ids: [str] = None) -> {str: KeggMap}:
        if map_ids is None:
            map_ids = self._available_maps()
        return {map_id: self.create_map(map_id) for map_id in map_ids}

    def _available_maps(self) -> {str}:
        for org in self.orgs:
            data_dir = f'{DATA_DIR}/maps_data/{org}'
            assert os.path.isdir(data_dir), f'Organism seems not to have been downloaded: {org=}; {data_dir} is empty'

        map_ids = {
            filename.removesuffix('.conf')
            for org in self.orgs
            for filename in os.listdir(f'{DATA_DIR}/maps_data/{org}')
            if filename.endswith('.conf')
        }
        for map_id in map_ids:
            assert len(map_id) == 5 and map_id.isnumeric(), f'Conf file does not start with map_id: {map_id=}'
        return map_ids

    def download_maps(self, map_ids: [str] = None, reload=False):
        if map_ids is None:
            map_ids = self.all_mapids.keys()

        for org in self.orgs:
            with requests.Session() as session:
                self._download_maps(session, map_ids=map_ids, org=org, reload=reload)

    def _download_maps(self, session, org: str, map_ids: [str], reload=False) -> None:
        os.makedirs(f'{DATA_DIR}/maps_data/{org}', exist_ok=True)

        non_existent_file = f'{DATA_DIR}/maps_data/{org}/non-existent.json'
        if os.path.isfile(non_existent_file):
            with open(non_existent_file) as f:
                non_existent = json.load(f)
        else:
            non_existent = []

        for map_id in map_ids:
            path_url = map_png_path(map_id, url=True)

            if path_url in non_existent:
                continue

            response = fetch(
                session=session,
                url=map_png_path(map_id, url=True),
                save_path=map_png_path(map_id, url=False),
                raw=True,
                make_cdb=False,
                convert_png=True,
            )

            if response == 'non_existent':
                non_existent.append(path_url)
                with open(f'{DATA_DIR}/maps_data/{org}/non-existent.json', 'w') as f:
                    json.dump(non_existent, f)

        found_maps = set(map.removesuffix('.png') for map in os.listdir(f'{DATA_DIR}/maps_png') if map.endswith('.png'))

        for map_id in found_maps.intersection(map_ids):
            response = fetch(
                session=session,
                url=map_conf_path(org, map_id, url=True),
                save_path=map_conf_path(org, map_id, url=False),
                raw=False,
                make_cdb=False
            )

            if response == 'non_existent':
                non_existent.append(path_url)
                with open(f'{DATA_DIR}/maps_data/{org}/non-existent.json', 'w') as f:
                    json.dump(non_existent, f)

    def __load_all_mapids(self) -> {str: str}:
        with open(f'{DATA_DIR}/rest_data/path.tsv', 'r') as f:
            path_file = f.readlines()  # ['path:map00010\tGlycolysis / Gluconeogenesis', ...]
        map_id_to_description = {
            map_id.removeprefix('map'): title.rstrip()
            for map_id, title in
            (line.split('\t', maxsplit=1) for line in path_file if line.startswith('map'))
        }

        for key in map_id_to_description.keys():
            assert len(key) == 5 and key.isnumeric()

        return map_id_to_description
