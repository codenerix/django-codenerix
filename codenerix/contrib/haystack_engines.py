from haystack.backends.elasticsearch7_backend import (
    Elasticsearch7SearchBackend,
    Elasticsearch7SearchEngine,
)


class AsciifoldingElasticBackend(Elasticsearch7SearchBackend):
    """
    Asciifolding analyzer for Elasticsearch 7.x via django-haystack.
    Adapted from Mounir Messelmeni (2015) for the ES7 backend:
    https://mounirmesselmeni.github.io/2015/12/13/enable-asciifolding-in-elasticsearchhaystack/
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.DEFAULT_SETTINGS["settings"]["analysis"]["analyzer"].update(
            {
                "ascii_analyser": {
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            },
        )
        for name in ("ngram_analyzer", "edgengram_analyzer"):
            self.DEFAULT_SETTINGS["settings"]["analysis"]["analyzer"][name]["filter"].append(
                "asciifolding"
            )

    def build_schema(self, fields):
        content_field_name, mapping = super().build_schema(fields)

        for _, field_class in fields.items():
            field_mapping = mapping[field_class.index_fieldname]

            if field_mapping["type"] == "text" and field_class.indexed:
                if not hasattr(
                    field_class,
                    "facet_for",
                ) and field_class.field_type not in ("ngram", "edge_ngram"):
                    field_mapping["analyzer"] = "ascii_analyser"

            mapping.update({field_class.index_fieldname: field_mapping})
        return (content_field_name, mapping)

    def extract_file_contents(self, *args, **kwargs):
        raise NotImplementedError(
            "AsciifoldingElasticSearchEngine does not support file content extraction.",
        )


class AsciifoldingElasticSearchEngine(Elasticsearch7SearchEngine):
    """
    Asciifolding search engine for Elasticsearch 7.x.
    """

    backend = AsciifoldingElasticBackend
