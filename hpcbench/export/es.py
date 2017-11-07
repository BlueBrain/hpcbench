"""Export campaign data in Elasticsearch
"""

import collections

from cached_property import cached_property
from elasticsearch import Elasticsearch
import six

from hpcbench.campaign import (
    get_benchmark_types,
    get_metrics,
)
from hpcbench.toolbox.collections_ext import dict_merge
from hpcbench.toolbox.functools_ext import chunks


class ESExporter(object):
    """Export a campaign to Elasticsearch
    """

    PY_TYPE_TO_ES_FIELD_TYPE = {
        float: 'float',
        int: 'long',
        six.text_type: 'text',
        str: 'keyword',
    }
    PROPERTIES_FIELD_TYPE = dict(date='date')

    COMMON_INDEX_MAPPING = dict(
        benchmark=dict(
            type='text',
        ),
        category=dict(
            type='text',
        ),
        date=dict(
            type='date',
        ),
        elapsed=dict(
            type='float',
        ),
        exit_status=dict(
            type='short'
        ),
    )

    def __init__(self, campaign):
        """
        :param campaign: instance of ``hpcbench.driver.CampaignDriver``
        """
        self.campaign = campaign

    @cached_property
    def es_client(self):
        """Get Elasticsearch client
        """
        es_conf = self.campaign.campaign.export.elasticsearch
        return Elasticsearch(es_conf.hosts, **es_conf.connection_params)

    @cached_property
    def index_client(self):
        """Get Elasticsearch index client
        """
        return self.es_client.indices

    @cached_property
    def index_name(self):
        """Get Elasticsearch index name associated to the campaign
        """
        fmt = self.campaign.campaign.export.elasticsearch.index_name
        fields = dict(
            date=self.campaign.report.date,
        )
        return fmt.format(**fields).lower()

    def export(self):
        """Create Elasticsearch index and feed it with campaign data
        """
        self.es_client.ping()
        self._prepare_index()
        self._push_data()

    def remove_index(self):
        """Remove Elasticsearch index associated to the campaign"""
        self.index_client.close(self.index_name)
        self.index_client.delete(self.index_name)

    def _prepare_index(self):
        if self.index_client.exists(self.index_name):
            raise Exception('Index already exists: %s' % self.index_name)
        else:
            self._create_index()

    def _create_index(self):
        self.index_client.create(
            self.index_name,
            dict(
                mappings=self.index_mapping
            )
        )

    def _push_data(self):
        for runs in chunks(self._documents, 20):
            resp = self.es_client.bulk(
                body=runs,
                index=self.index_name
            )
            if resp['errors']:
                raise Exception('Could not push documents')

    @cached_property
    def index_mapping(self):
        """Get Elasticsearch index mapping
        """
        fields = dict(
            (doc_type, self._get_document_mapping(doc_type)) for
            doc_type in self._document_types
        )
        return fields

    @property
    def _documents(self):
        for run in ESExporter._get_runs(self.campaign):
            yield dict(
                index=dict(
                    _type=run['benchmark'],
                    _id=run['id']
                )
            )
            yield run

    @cached_property
    def _document_types(self):
        return [
            benchmark
            for benchmark in get_benchmark_types(self.campaign.campaign)
        ]

    def _get_document_mapping(self, benchmark):
        fields = {}
        for run in ESExporter._get_benchmark_runs(self.campaign, benchmark):
            dict_merge(fields, ESExporter._get_dict_mapping(benchmark, run))
        return fields

    @classmethod
    def _get_dict_mapping(cls, prop, data):
        mapping = {}
        for name, value in data.items():
            if isinstance(value, (dict, collections.Mapping)):
                dict_merge(mapping, cls._get_dict_mapping(name, value))
            else:
                dict_merge(mapping, cls._get_field_mapping(name, value))
        return {
            prop: {
                'properties': mapping
            }
        }

    @classmethod
    def _get_field_mapping(cls, name, value):
        field_type = cls.PROPERTIES_FIELD_TYPE.get(name)
        if field_type is None:
            field_type = cls.PY_TYPE_TO_ES_FIELD_TYPE[type(value)]
        return {
            name: {
                'type': field_type
            }
        }

    @classmethod
    def _get_runs(cls, campaign):
        for attrs, metrics in get_metrics(campaign):
            for run in metrics:
                eax = dict()
                eax.update(attrs)
                eax.update(run)
                yield eax

    @classmethod
    def _get_benchmark_runs(cls, campaign, benchmark):
        for attrs, metrics in get_metrics(campaign):
            for run in metrics:
                if run['benchmark'] == benchmark:
                    eax = dict()
                    eax.update(attrs)
                    eax.update(run)
                    yield eax
