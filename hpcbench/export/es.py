"""Export campaign data in Elasticsearch
"""

import collections
import logging

from cached_property import cached_property
from elasticsearch import Elasticsearch
import six

from hpcbench.campaign import from_file, get_metrics, ReportNode
from hpcbench.toolbox.collections_ext import dict_merge
from hpcbench.toolbox.functools_ext import chunks


class ESExporter(object):
    """Export a campaign to Elasticsearch
    """

    PY_TYPE_TO_ES_FIELD_TYPE = {
        bool: 'boolean',
        float: 'float',
        int: 'long',
        six.text_type: 'keyword',
        str: 'keyword',
    }
    PROPERTIES_FIELD_TYPE = dict(date='date')
    ES_DOC_TYPE = 'hpcbench_metric'

    def __init__(self, path, hosts):
        """
        :param path: path to existing campaign
        :type path: str
        :param hosts: Elasticsearch cluster
        :rtype: str or list or str
        """
        self.campaign = from_file(path, expandcampvars=False)
        self.report = ReportNode(path)
        self.hosts = hosts

    @cached_property
    def es_client(self):
        """Get Elasticsearch client
        """
        es_conf = self.campaign.export.elasticsearch
        return Elasticsearch(self.hosts, **es_conf.connection_params)

    @cached_property
    def index_client(self):
        """Get Elasticsearch index client
        """
        return self.es_client.indices

    @cached_property
    def index_name(self):
        """Get Elasticsearch index name associated to the campaign
        """
        fmt = self.campaign.export.elasticsearch.index_name
        fields = dict(date=self.report['date'])
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
        self.index_client.create(self.index_name, dict(mappings=self.index_mapping))

    def _push_data(self):
        doc_count = 0
        for runs in chunks(self._documents, 20):
            resp = self.es_client.bulk(body=runs, index=self.index_name)
            if resp['errors']:
                raise Exception('Could not push documents')
            doc_count += len(resp['items'])
        logging.info(
            'pushed %s documents in Elasticsearch index "%s"',
            doc_count,
            self.index_name,
        )

    @cached_property
    def index_mapping(self):
        """Get Elasticsearch index mapping
        """
        return self._get_document_mapping

    @property
    def _documents(self):
        for metric in self._metrics:
            yield dict(index=dict(_type=self.ES_DOC_TYPE, _id=self.document_id(metric)))
            metric['campaign_id'] = self.campaign.campaign_id
            yield metric

    def document_id(self, doc):
        return doc['id'] + '/' + str(hash(frozenset(doc['context'].items())))

    @property
    def _get_document_mapping(self):
        fields = {}
        for metric in self._metrics:
            dict_merge(fields, ESExporter._get_dict_mapping(self.ES_DOC_TYPE, metric))
        return fields

    @classmethod
    def _get_dict_mapping(cls, prop, data, root=None):
        mapping = {}
        for name, value in data.items():
            if isinstance(value, (dict, collections.Mapping)):
                ctx = (root or tuple()) + (name,)
                dict_merge(mapping, cls._get_dict_mapping(name, value, ctx))
            else:
                dict_merge(mapping, cls._get_field_mapping(name, value, root))
        return {prop: {'properties': mapping}}

    @classmethod
    def _get_field_type(cls, value):
        if isinstance(value, list):
            if value:
                return cls._get_field_type(value[0])
            else:
                value = 'a_string'
        return type(value)

    @classmethod
    def _get_field_mapping(cls, name, value, root):
        extra_params = {}
        field_type = cls.PROPERTIES_FIELD_TYPE.get(name)
        if field_type is None:
            obj_type = cls._get_field_type(value)
            if obj_type == dict:
                if isinstance(value, list):
                    value = value[0]
                extra_params = cls._get_dict_mapping(None, value)[None]
                extra_params['dynamic'] = False
                field_type = 'nested'
            elif root == ('metas',) and isinstance(value, six.string_types):
                field_type = 'text'
            else:
                field_type = cls.PY_TYPE_TO_ES_FIELD_TYPE[obj_type]
        mapping = {name: {'type': field_type}}
        mapping[name].update(extra_params)
        return mapping

    @property
    def _runs(self):
        for attrs, runs in get_metrics(self.campaign, self.report):
            for run in runs:
                yield attrs, run

    @property
    def _metrics(self):
        for attrs, run in self._runs:
            if run.get('command_succeeded', False):
                metrics = run.pop('metrics')
                for metric in metrics:
                    eax = dict(metric)
                    eax.update(run)
                    eax.update(attrs)
                    yield eax
