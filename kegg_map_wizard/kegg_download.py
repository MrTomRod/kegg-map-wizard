import os
import base64
from io import BytesIO
from PIL import Image  # pip install Pillow
import json
import cdblib
import requests
import time
from random import randint
import multiprocessing
import logging

N_PARALLEL_DOWNLOADS = os.environ.get('KEGG_MAP_WIZARD_PARALLEL', '6')
assert N_PARALLEL_DOWNLOADS.isdecimal(), f'The environment variable KEGG_MAP_WIZARD_PARALLEL must be decimal. ' \
                                         f'KEGG_MAP_WIZARD_PARALLEL={N_PARALLEL_DOWNLOADS}'
N_PARALLEL_DOWNLOADS = int(N_PARALLEL_DOWNLOADS)

assert 'KEGG_MAP_WIZARD_DATA' in os.environ, \
    f'Please set the environment variable KEGG_MAP_WIZARD_DATA to the directory where KEGG data will be stored'
DATA_DIR = os.environ['KEGG_MAP_WIZARD_DATA']
assert os.path.isdir(DATA_DIR), f'Directory not found: KEGG_MAP_WIZARD_DATA={DATA_DIR}'
logging.warning(f'Setup: KEGG_MAP_WIZARD_DATA={DATA_DIR}; KEGG_MAP_WIZARD_PARALLEL={N_PARALLEL_DOWNLOADS}')


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
        timeout: tuple = (2, 5),
        verbose: bool = True
) -> str:
    """
    Download a file and save it to disk.

    :param session: requests.Session()
    :param url: target url
    :param save_path: target path
    :param raw: if False: write in 'w'-mode, if True: write in 'wb'-mode,
    :param sort: if True: sort file using C/Python logic after download
    :param timeout: wait between timeout[0] and timeout[1] seconds before attempting download, to avoid overloading API
    :param verbose: if True: print messages
    :returns: status of the download: if 200: success, if 404 and empty: non-existent, 'error' otherwise
    """
    print(save_path)
    if timeout:
        timeout = randint(*timeout)
        if verbose: print(f'Downloading: {url} (after sleeping for {timeout} s)')
        time.sleep(timeout)
    else:
        if verbose: print(f'Downloading: {url}')

    with session.get(url) as response:
        if raw:
            data = response.content
            mode = 'wb'
        else:
            data = response.text
            mode = 'w'

        if response.status_code != 200:
            if data == '' and response.status_code == 404:
                if verbose: print(f'Non-existent found! :: {url}')
                return 'non-existent'
            else:
                if verbose: print(f'FAILURE ({response.status_code}) :: {url}\nDATA:\n\n{data}')
                return 'error'

        with open(save_path, mode) as out:
            out.write(data)

        if make_cdb:
            mk_cdb(save_path)

        if convert_png:
            encode_png(save_path)

        return 'success'


def fetch_all(
        args_list: [tuple],
        n_parallel: int,
        reload: bool,
        nonexistent_file: str = None,
        verbose: bool = True
) -> None:
    """
    Multiprocess the fetch function.

    :param args_list: List of arguments for fetch function, excluding session: [(url, save_path, raw, sort), ...]
    :param n_parallel: Number of parallel downloads
    :param reload: if True: overwrite existing files, if False: only download non-existing files
    :param nonexistent_file: path to json-file that conains list of non-existent files
    :param verbose: if True: print summary
    """
    non_existent = []  # his list holds urls that did not lead to a real file

    # load previous nonexistent file
    if not reload and nonexistent_file and os.path.isfile(nonexistent_file):
        with open(nonexistent_file) as f:
            non_existent = json.load(f)

    if not reload:
        # download only files that do not exist yet and do not try to download previous non_existent again
        args_list = [args for args in args_list if not os.path.isfile(args[1]) and args[0] not in non_existent]  # args[0] url, args[1]: save_path

    if len(args_list) == 0:
        # no files to download
        return

    with requests.Session() as session:
        # download
        statuses = process_all(
            func=fetch,
            args_list=[tuple([session, *args]) for args in args_list],  # add session to arguments
            n_parallel=n_parallel
        )

    summary = {status: [] for status in set(statuses)}
    for args, status in zip(args_list, statuses):
        summary[status].append(args[0])  # args[0] url
        if status == 'non-existent':
            non_existent.append(args[0])  # args[0] url

    if verbose:
        print('Download status:', {status: len(urls) for status, urls in summary.items()})
        if 'error' in summary and len(summary['error']) > 0:
            print(f"\terror: {len(summary['error'])}")

    if nonexistent_file:
        with open(nonexistent_file, 'w') as f:
            json.dump(non_existent, f)


def process_all(func, args_list: [tuple], n_parallel: int) -> list:
    """
    Multiprocess a function. Returns list of return values.

    :param func: function to multiprocess
    :param args_list: list of arguments for the function
    :param n_parallel: number of parallel tasks
    :return: list of return values
    """
    with multiprocessing.Pool(processes=n_parallel) as pool:
        result = pool.starmap(func=func, iterable=args_list)

    return result


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


def download_rest_data(orgs: [str], reload=False) -> {str: cdblib.Reader}:
    os.makedirs(f'{DATA_DIR}/rest_data', exist_ok=True)
    os.makedirs(f'{DATA_DIR}/maps_png/', exist_ok=True)

    files = ['path', 'rn', 'compound', 'drug', 'glycan', 'dgroup', 'enzyme', 'br', 'rc', *orgs]

    to_download = [
        (  # parameters for fetch function (except for session)
            rest_data_path(file, url=True),  # url
            rest_data_path(file, url=False),  # save_path
            False,  # raw
            True  # create cdb
        )
        # dict(url=f'http://rest.kegg.jp/list/{file}', save_path=F'{self.KEGG_REST_PATH}/{file}.tsv', raw=False)
        for file in files
    ]

    fetch_all(args_list=to_download, n_parallel=N_PARALLEL_DOWNLOADS, reload=reload)

    for args in to_download:
        assert os.path.isfile(args[1]), f'failed to download {args}'

    return {file: get_cdb(rest_data_path(file)) for file in files}


def download_map_pngs(map_ids: [str], reload: bool = False) -> None:
    to_download = []
    for map_id in map_ids:
        to_download.append(
            (
                map_png_path(map_id, url=True),  # url
                map_png_path(map_id, url=False),  # save_path
                True,  # raw
                False,  # create cdb
                True  # encode png
            )
        )

    fetch_all(args_list=to_download, n_parallel=N_PARALLEL_DOWNLOADS, reload=reload)

    for args in to_download:
        assert os.path.isfile(args[1]), f'failed to download {args}'


def download_map_confs(org: str, map_ids: [str], reload: bool = False, nonexistent_file=True):
    to_download = []
    for map_id in map_ids:
        to_download.append(
            (
                map_conf_path(org, map_id, url=True),  # url
                map_conf_path(org, map_id, url=False),  # save_path
                False,  # raw
                False  # create cdb
            )
        )

    if nonexistent_file:
        nonexistent_file = f'{DATA_DIR}/maps_data/{org}/non-existent.json'

    fetch_all(args_list=to_download, n_parallel=N_PARALLEL_DOWNLOADS, reload=reload,
              nonexistent_file=nonexistent_file)


def get_description(cdb_reader: cdblib.Reader, query: str) -> str:
    """
    Use rest data to get the description of an annotation.

    :param query: query annotation
    :param rest_file: file to be searched
    :return: description. If none is found, an empty string is returned and a warning is printed.
    """
    return cdb_reader.get(query.encode('utf-8'), default=b'').decode('utf-8')
