import logging
from re import Pattern
from urllib.parse import quote
from kegg_map_wizard.kegg_download import get_description
from kegg_map_wizard.kegg_utils import ANNOTATION_SETTINGS


class InvalidAnnotationException(Exception):
    pass


class KeggAnnotation:
    def __init__(self, name: str, anno_type: str, html_class: str, description: str):
        if anno_type == 'EC':
            self.name = f'EC:{name}'
        else:
            self.name = name
        self.anno_type = anno_type
        self.html_class = html_class
        self.description = description

    def __str__(self):
        return f'<KeggAnnotation: {self.anno_type} - {self.name}>'

    def as_dict(self) -> dict:
        return dict(
            type=self.anno_type,
            name=self.name,
            description=quote(self.description)
        )

    @classmethod
    def create_annos(cls, cdb_readers, url: str, re_org_anno: Pattern, org: str):  # -> {tuple[str, str]: KeggAnnotation}

        url_prefix, annotations_hyperlink = url.split('?', maxsplit=1)

        assert url_prefix in ['/dbget-bin/www_bget', '/kegg-bin/show_pathway', '/kegg-bin/search_htext'], \
            f'Error while parsing annotations-url: "{url}": bad url-prefix'
        assert '?' not in annotations_hyperlink, \
            f'Error while parsing annotations-url: "{url}": bad annotations-hyperlink'

        if '/' in annotations_hyperlink:
            annotations = annotations_hyperlink.replace('/', '+')

        anno_queries = annotations_hyperlink.split('+')

        annos = {}
        for anno_query in anno_queries:
            try:
                anno = cls.create_anno(cdb_readers, anno_query, re_org_anno, org)
                assert (anno.anno_type, anno.name) not in annos, 'error: duplicate annotations in shape'
                annos[(anno.anno_type, anno.name)] = anno
            except InvalidAnnotationException as e:
                logging.warning(e)

        return annos

    @classmethod
    def create_anno(cls, cdb_readers, anno_query: str, re_org_anno: Pattern, org: str):  # -> KeggAnnotation:
        """
        Parse sometimes cryptic 2nd column of .config files

        anno_query examples:
          - 'K00716' from '/dbget-bin/www_bget?K00716+K07633+K07634'
          - 'htext=br08003' from '/kegg-bin/search_htext?htext=br08003'

        :param anno_query: part of a hyperlink
        :returns: KeggAnnotation object
        """

        # handle organism annotations
        if re_org_anno.match(anno_query):
            return cls(name=anno_query, anno_type=org, html_class='enzyme',
                                  description=get_description(cdb_readers[org], query=anno_query))

        # handle most common cases
        for anno_type, settings in ANNOTATION_SETTINGS.items():
            if settings['pattern'].match(anno_query):
                if anno_type == 'MAP':
                    anno_query = anno_query[-5:]
                query = f'{settings["descr_prefix"]}{anno_query}'
                return cls(
                    name=anno_query,
                    anno_type=anno_type,
                    html_class=settings['html_class'],
                    description=get_description(cdb_readers[settings['rest_file']], query=query)
                )

        # handle anomalies
        if anno_query.startswith('dr:D'):
            # sometimes drugs contain the 'dr:' prefix
            anno_type = 'D'
            name = anno_query.removeprefix('dr:')
        elif anno_query.startswith('htext=br'):
            # strange br: 'htext=br08003&search_string=%22Acridone%20alkaloids%22&option=-n'
            anno_type = 'BR'
            name = anno_query.removeprefix('htext=br').lstrip(':')
            name = f'br:{name[:5]}'
        elif anno_query == 'map4670':
            # strange anomaly
            anno_type, name = 'MAP', 'map04670'
        else:
            raise InvalidAnnotationException(f'Annotation {anno_query} does not match any pattern!')

        settings = ANNOTATION_SETTINGS[anno_type]
        assert settings['pattern'].match(name), f'annotation ({anno_type}) does not match pattern: {name}'
        if anno_type == 'MAP':
            name = name[-5:]
        query = f'{settings["descr_prefix"]}{name}'

        return cls(
            name=name,
            anno_type=anno_type,
            html_class=settings['html_class'],
            description=get_description(cdb_readers[settings['rest_file']], query=query)
        )
