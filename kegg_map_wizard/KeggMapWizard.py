import os

from kegg_map_wizard.kegg_download import DATA_DIR, download_rest_data, download_map_pngs, download_map_confs, map_png_path, map_conf_path
from kegg_map_wizard.KeggMap import KeggMap


class KeggMapWizard:
    def __init__(self, orgs: [str], reload_rest_data=False):
        self.orgs = orgs
        self.cdb_readers = download_rest_data(orgs=self.orgs, reload=reload_rest_data)
        self.all_mapids: {str: str} = self.__load_all_mapids()

    def __str__(self):
        return f'<KeggMapWizard: {self.org_string}>'

    @property
    def org_string(self):
        return "+".join(self.orgs)

    def download_configs(self, map_ids: [str] = None, reload: bool = False):
        if map_ids is None:
            map_ids = self.all_mapids.keys()
        if reload:
            download_rest_data(orgs=self.orgs, reload=False)
        for org in self.orgs:
            self.download_maps(org=org, map_ids=map_ids, reload=reload, nonexistent_file=True)

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

    def download_all_maps(self, reload=False):
        for org in self.orgs:
            self.download_maps(map_ids=self.all_mapids.keys(), org=org, reload=reload)

    def download_maps(self, org: str, map_ids: [str], reload=False, nonexistent_file=True) -> None:
        os.makedirs(f'{DATA_DIR}/maps_data/{org}', exist_ok=True)
        download_map_pngs(map_ids, reload=reload)
        found_maps = set(map.removesuffix('.png') for map in os.listdir(f'{DATA_DIR}/maps_png') if map.endswith('.png'))
        confs = [map for map in map_ids if map in found_maps]
        download_map_confs(org, confs, reload=reload, nonexistent_file=nonexistent_file)

    def __load_all_mapids(self) -> {str: str}:
        with open(f'{DATA_DIR}/rest_data/path.tsv', 'r') as f:
            path_file = f.readlines()  # ['path:map00010\tGlycolysis / Gluconeogenesis', ...]
        map_id_to_description = {map_id.lstrip('path:map'): title.rstrip() for map_id, title in
                                 (line.split('\t', maxsplit=1) for line in path_file)}  #

        for key in map_id_to_description.keys():
            assert len(key) == 5 and key.isnumeric()

        return map_id_to_description
