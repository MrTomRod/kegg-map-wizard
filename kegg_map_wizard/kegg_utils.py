import os
import re
import json
from math import floor, ceil
from jinja2 import Template

ROOT = os.path.dirname(__file__)


def round_up(number: float, digits: int = 5) -> float:
    return ceil((10 ** digits) * number) / (10 ** digits)


def round_down(number: float, digits: int = 5) -> float:
    return floor((10 ** digits) * number) / (10 ** digits)


def load_template(name: str) -> Template:
    with open(f'{ROOT}/template/{name}.svg') as f:
        template = f.read()
        return Template(template)


def load_png(png_path: str) -> json:
    with open(png_path + '.json') as f:
        return json.load(f)


MAP_TEMPLATE = load_template('map')
LINE_TEMPLATE = load_template('line')
RECT_TEMPLATE = load_template('rect')
POLY_TEMPLATE = load_template('poly')
CIRCLE_TEMPLATE = load_template('circle')

ANNOTATION_SETTINGS = dict(
    K=dict(
        html_class='enzyme',
        type='KEGG Gene',
        pattern=re.compile('^K[0-9]{5}$'),
        rest_file='ko',
        descr_prefix=''),
    EC=dict(
        html_class='enzyme',
        type='Enzyme Commission',
        pattern=re.compile('^[0-9]+(\.[0-9]+)+(\.-)?$'),
        rest_file='enzyme',
        descr_prefix=''),
    R=dict(
        html_class='enzyme',
        type='KEGG Reaction',
        pattern=re.compile('^R[0-9]{5}$'),
        rest_file='rn',
        descr_prefix=''),
    RC=dict(
        html_class='enzyme',
        type='KEGG Reaction Class',
        pattern=re.compile('^RC[0-9]{5}$'),
        rest_file='rc',
        descr_prefix=''),
    C=dict(
        html_class='compound',
        type='KEGG Compound',
        pattern=re.compile('^C[0-9]{5}$'),
        rest_file='compound',
        descr_prefix=''),
    G=dict(
        html_class='compound',
        type='KEGG Glycan',
        pattern=re.compile('^G[0-9]{5}$'),
        rest_file='glycan',
        descr_prefix=''),
    D=dict(
        html_class='compound',
        type='KEGG Drug',
        pattern=re.compile('^D[0-9]{5}$'),
        rest_file='drug',
        descr_prefix=''),
    DG=dict(
        html_class='compound',
        type='KEGG Drug Group',
        pattern=re.compile('^DG[0-9]{5}$'),
        rest_file='dgroup',
        descr_prefix=''),
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
        descr_prefix='map')
)
