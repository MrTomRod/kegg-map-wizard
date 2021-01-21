import os
import re
import requests
import time
from random import randint
import multiprocessing
import json
import cdblib
import base64
from io import BytesIO
from PIL import Image  # pip install Pillow
import sqlite3

from lib.OutlineStrokeJsLib import OutlineStrokeJsLib
from lib.OutlineStrokeInkscape import OutlineStrokeInkscape

outline_stroke = OutlineStrokeInkscape()


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


def load_png(png_path: str) -> json:
    with open(png_path + '.json') as f:
        return json.load(f)


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


import sqlite3


class KeyValueDb:
    def __init__(self, db_path, table_name='KeyValueDb'):
        self.db_path = db_path
        self.table_name = table_name
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        if not self.__table_exists():
            self.__create_table()

    def __table_exists(self) -> bool:
        return bool(self.cursor.execute(
            '''SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?''',
            (self.table_name,)
        ).fetchone()[0])

    def __create_table(self):
        self.cursor.execute(
            f'''CREATE TABLE {self.table_name} (key TEXT primary key, value TEXT)'''
        )

    def get(self, key: str) -> str:
        result = self.cursor.execute(f'''SELECT value FROM {self.table_name} WHERE key = ?''', (key,)).fetchone()
        if result is None:
            raise KeyError(f'path {key} not found in outline_db')
        else:
            return result[0]

    def set(self, key: str, value: str):
        print(key[:10], "->", value[:10])
        self.cursor.execute(f"INSERT INTO {self.table_name} VALUES (?,?)", (key, value,))
        self.connection.commit()

    def __getitem__(self, key: str) -> str:
        return self.get(key)

    def __setitem__(self, key: str, value: str):
        self.set(key, value)

    def __delitem__(self, key: str):
        self.cursor.execute(f'''DELETE FROM {self.table_name} WHERE key = ?''', (key,))
        self.connection.commit()

    def __contains__(self, item: str):
        return bool(self.cursor.execute(f'''SELECT count(*) FROM {self.table_name} WHERE key = ?''', (item,)).fetchone()[0])

    def __len__(self):
        return self.cursor.execute(f"SELECT count(*) FROM {self.table_name}").fetchone()[0]


outline_db = KeyValueDb(
    db_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/outline.db',
    table_name='Outlines'
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


ANNOTATION_SETTINGS = dict(
    K=dict(
        html_class='enzyme',
        type='KEGG Gene',
        pattern=re.compile('^K[0-9]{5}$'),
        rest_file='ko',
        descr_prefix='ko:'),
    EC=dict(
        html_class='enzyme',
        type='Enzyme Commission',
        pattern=re.compile('^[0-9]+(\.[0-9]+)+(\.-)?$'),
        rest_file='enzyme',
        descr_prefix='ec:'),
    R=dict(
        html_class='enzyme',
        type='KEGG Reaction',
        pattern=re.compile('^R[0-9]{5}$'),
        rest_file='rn',
        descr_prefix='rn:'),
    RC=dict(
        html_class='enzyme',
        type='KEGG Reaction Class',
        pattern=re.compile('^RC[0-9]{5}$'),
        rest_file='rc',
        descr_prefix='rc:'),
    C=dict(
        html_class='compound',
        type='KEGG Compound',
        pattern=re.compile('^C[0-9]{5}$'),
        rest_file='compound',
        descr_prefix='cpd:'),
    G=dict(
        html_class='compound',
        type='KEGG Glycan',
        pattern=re.compile('^G[0-9]{5}$'),
        rest_file='glycan',
        descr_prefix='gl:'),
    D=dict(
        html_class='compound',
        type='KEGG Drug',
        pattern=re.compile('^D[0-9]{5}$'),
        rest_file='drug',
        descr_prefix='dr:'),
    DG=dict(
        html_class='compound',
        type='KEGG Drug Group',
        pattern=re.compile('^DG[0-9]{5}$'),
        rest_file='dgroup',
        descr_prefix='dg:'),
    BR=dict(
        html_class='brite',
        type='KEGG Brite Entry',
        pattern=re.compile('^br:[0-9]{5}$'),
        rest_file='br',
        descr_prefix=''),
    MAP=dict(
        html_class='kegg-map',
        type='KEGG Map',
        pattern=re.compile('^([a-z]{2,3})[0-9]{5}$'),
        rest_file='path',
        descr_prefix='path:map')
)
