import logging
from urllib.parse import quote


class InvalidAnnotationException(Exception):
    pass


class KeggAnnotation:
    def __init__(self, kegg_map_wizard, name: str, anno_type: str, html_class: str, description: str):
        if anno_type == 'EC':
            self.name = f'EC:{name}'
        else:
            self.name = name
        self.kegg_map_wizard = kegg_map_wizard
        self.anno_type = anno_type
        self.html_class = html_class
        self.description = description

    def __repr__(self):
        return F'<KeggAnnotation ({self.anno_type}): {self.name}>'

    @property
    def as_dict(self) -> dict:
        return dict(
            type=self.anno_type,
            name=self.name,
            description=quote(self.description)
        )

    @staticmethod
    def generate(kegg_map_wizard, url: str) -> list:

        url_prefix, annotations = url.split('?', maxsplit=1)

        assert url_prefix in ['/dbget-bin/www_bget', '/kegg-bin/show_pathway', '/kegg-bin/search_htext'], \
            f'Error while parsing annotations-url: "{url}": bad url-prefix'
        assert '?' not in annotations

        if '/' in annotations:
            annotations = annotations.replace('/', '+')

        ids = annotations.split('+')

        annos = []
        for id in ids:
            try:
                annos.append(kegg_map_wizard.parse_anno(id))
            except InvalidAnnotationException as e:
                logging.warning(e)

        return annos
