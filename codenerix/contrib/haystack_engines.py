# from django.conf import settings
from haystack.backends.elasticsearch2_backend import (  # type: ignore[import-not-found] # noqa: E501
    Elasticsearch2SearchBackend,
    Elasticsearch2SearchEngine,
)


class AsciifoldingElasticBackend(Elasticsearch2SearchBackend):
    """
    Mounir Messelmeni - 13/December/2015
    https://mounirmesselmeni.github.io/2015/12/13/enable-asciifolding-in-elasticsearchhaystack/
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        analyzer = {
            "ascii_analyser": {
                "tokenizer": "standard",
                "filter": ["standard", "asciifolding", "lowercase"],
            },
            "ngram_analyzer": {
                "type": "custom",
                "tokenizer": "lowercase",
                "filter": ["haystack_ngram", "asciifolding"],
            },
            "edgengram_analyzer": {
                "type": "custom",
                "tokenizer": "lowercase",
                "filter": ["haystack_edgengram", "asciifolding"],
            },
        }
        self.DEFAULT_SETTINGS["settings"]["analysis"]["analyzer"] = analyzer

    def build_schema(self, fields):
        content_field_name, mapping = super().build_schema(fields)

        for field_name, field_class in fields.items():
            field_mapping = mapping[field_class.index_fieldname]

            if field_mapping["type"] == "string" and field_class.indexed:
                if not hasattr(
                    field_class,
                    "facet_for",
                ) and field_class.field_type not in ("ngram", "edge_ngram"):
                    field_mapping["analyzer"] = "ascii_analyser"

            mapping.update({field_class.index_fieldname: field_mapping})
        return (content_field_name, mapping)


class AsciifoldingElasticSearchEngine(Elasticsearch2SearchEngine):
    """
    Mounir Messelmeni - 13/December/2015
    https://mounirmesselmeni.github.io/2015/12/13/enable-asciifolding-in-elasticsearchhaystack/
    """

    backend = AsciifoldingElasticBackend
