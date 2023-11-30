import os
import base64
from io import BytesIO
from PIL import Image  # pip install Pillow
import json
import cdblib
import requests
import logging

if 'KEGG_MAP_WIZARD_DATA' in os.environ:
    DATA_DIR = os.environ['KEGG_MAP_WIZARD_DATA']
else:
    from platformdirs import user_data_dir

    DATA_DIR = user_data_dir('kegg-map-wizard', 'MrTomRod')
assert os.path.isdir(DATA_DIR), f'Directory not found: KEGG_MAP_WIZARD_DATA={DATA_DIR}'
logging.info(f'Setup: KEGG_MAP_WIZARD_DATA={DATA_DIR}')


def split(line: str) -> (str, str):
    if '\t' in line:
        return line.split('\t', maxsplit=1)
    else:
        return line, ''


def mk_cdb(file: str):
    cdb_file = file + '.cdb'
    with open(file) as in_f, open(cdb_file, 'wb') as out_f, cdblib.Writer(out_f) as writer:
        for line in in_f.readlines():
            k, v = split(line.strip())
            writer.put(k.encode('utf-8'), v.encode('utf-8'))


def get_cdb(file: str):
    cdb_file = file + '.cdb'
    reader = cdblib.Reader.from_file_path(cdb_file)
    return reader


def encode_png(png_path: str) -> None:
    img = Image.open(png_path)
    img = img.convert('RGBA')

    pixdata = img.load()

    width, height = img.size

    for y in range(height):
        for x in range(width):
            if pixdata[x, y] == (255, 255, 255, 255):
                pixdata[x, y] = (255, 255, 255, 0)

    buffer = BytesIO()
    img.save(buffer, 'PNG')
    img.close()

    with open(png_path + '.json', 'w') as f:
        json.dump(dict(
            width=width,
            height=height,
            image=base64.b64encode(buffer.getvalue()).decode()), f
        )


def fetch(
        session: requests.Session,
        url: str,
        save_path: str,
        raw: bool = False,
        make_cdb: bool = False,
        convert_png: bool = False,
        verbose: bool = True
) -> str:
    """
    Download a file and save it to disk.

    :param session: requests.Session()
    :param url: target url
    :param save_path: target path
    :param raw: if False: write in 'w'-mode, if True: write in 'wb'-mode,
    :param sort: if True: sort file using C/Python logic after download
    :param verbose: if True: print messages
    :returns: status of the download: if 200: success, if 404 and empty: non-existent, 'error' otherwise
    """
    if os.path.isfile(save_path):
        logging.info(f'Already downloaded: {save_path}')
        return 'success'

    print(f'Downloading: {url}')

    with session.get(url) as response:
        if raw:
            data = response.content
            mode = 'wb'
        else:
            data = response.text
            mode = 'w'

        if response.status_code != 200:
            if data == '' and response.status_code == 404:
                if verbose:
                    print(f'Non-existent found! :: {url}')
                return 'non-existent'
            else:
                raise AssertionError(f'FAILURE ({response.status_code})n'
                                     f'{url=}\nDATA:\n\n{data}')

        with open(save_path, mode) as out:
            out.write(data)

        if make_cdb:
            mk_cdb(save_path)

        if convert_png:
            encode_png(save_path)

        return 'success'


def rest_data_path(key: str, url=False) -> str:
    if url:
        return f'http://rest.kegg.jp/list/{key}'
    else:
        return f'{DATA_DIR}/rest_data/{key}.tsv'


def map_conf_path(org: str, map_id: str, url=False) -> str:
    if url:
        return f'http://rest.kegg.jp/get/{org}{map_id}/conf'
    else:
        return f'{DATA_DIR}/maps_data/{org}/{map_id}.conf'


def map_png_path(map_id: str, url=False) -> str:
    if url:
        return f'https://www.genome.jp/kegg/pathway/map/map{map_id}.png'
    else:
        return f'{DATA_DIR}/maps_png/{map_id}.png'


def download_rest_data(session, orgs: [str]) -> {str: cdblib.Reader}:
    os.makedirs(f'{DATA_DIR}/rest_data', exist_ok=True)
    os.makedirs(f'{DATA_DIR}/maps_png/', exist_ok=True)

    files = {'path', 'rn', 'compound', 'drug', 'glycan', 'dgroup', 'enzyme', 'br', 'rc', *orgs}

    resp = {}

    for file in files:
        save_path = rest_data_path(file)
        fetch(
            session=session,
            url=rest_data_path(file, url=True),
            save_path=save_path,
            raw=False,
            make_cdb=True
        )
        assert os.path.isfile(save_path), f'failed to download {save_path=}'
        resp[file] = get_cdb(save_path)

    return resp


def get_description(cdb_reader: cdblib.Reader, query: str) -> str:
    """
    Use rest data to get the description of an annotation.

    :param query: query annotation
    :param rest_file: file to be searched
    :return: description. If none is found, an empty string is returned and a warning is printed.
    """
    return cdb_reader.get(query.encode('utf-8'), default=b'').decode('utf-8')
