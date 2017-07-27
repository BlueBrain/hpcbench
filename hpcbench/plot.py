"""Draw figures from extracted metrics
"""
import hashlib
import operator

from hpcbench.toolbox.collections_ext import flatten_dict
from hpcbench.toolbox.edsl import kwargsql
from hpcbench.toolbox.functools_ext import compose


class Plotter(object):
    """Use matplotlib to draw figures
    """
    def __init__(self, metrics, **kwargs):
        self.metrics = metrics
        self.kwargs = kwargs

    def __call__(self, desc):
        """Draw figure
        :param desc: Figure description
        """

        metrics = self.select_metrics(desc)
        metrics = self.sort_metrics(desc, metrics)
        meta_series, metric_series = self.build_series(desc, metrics)
        title = desc['name'].format(**self.kwargs)
        import matplotlib.pyplot as plt

        plt.title(title)
        desc['plotter'](
            plt,
            desc,
            meta_series,
            metric_series
        )
        plt.savefig(self.get_filename(desc))
        plt.close()

    @classmethod
    def get_filename(cls, desc):
        """
        :return: figure output filename
        :rtype: string
        """
        desc = dict((k, v) for k, v in desc.items() if k != 'plotter')
        flatdict = flatten_dict(desc)
        sha256 = hashlib.sha256()
        sha256.update(repr(tuple(sorted(flatdict.items()))).encode('utf-8'))
        return sha256.hexdigest() + '.png'

    @classmethod
    def sort_metrics(cls, desc, metrics):
        """Order data series"""
        metas = desc['series'].get('metas') or []
        if metas:
            key_builder = []
            for meta in metas:
                if meta.startswith('-'):
                    key_builder.append(compose(
                        operator.neg,
                        operator.itemgetter(meta[1:])
                    ))
                else:
                    key_builder.append(operator.itemgetter(meta))

            def _key_builder_func(metric):
                return [
                    getter(metric['metas'])
                    for getter in key_builder
                ]
            metrics.sort(key=_key_builder_func)
        return metrics

    def select_metrics(self, desc):
        """
        :return: metrics required to draw the figure
        :rtype: dictionary
        """
        selectables = desc.get('select') or []
        if not selectables:
            return self.metrics
        return [
            m for m in self.metrics
            if kwargsql.and_(m, **selectables)
        ]

    @classmethod
    def build_series(cls, desc, metrics):
        """Transform JSON metrics to data series used by matplotlib
        """
        meta_names = [
            m[1:] if m.startswith('-') else m
            for m in desc['series'].get('metas') or []
        ]
        metric_names = desc['series']['metrics']
        meta_series = dict()
        metric_series = dict()
        for run in metrics:
            def _search_in_dict(keys, dico, serie, with_kwargsql=False):
                for name in keys:
                    if not with_kwargsql:
                        value = dico.get(name)
                    else:
                        value = kwargsql.get(dico, name)
                    if value is not None:
                        serie.setdefault(name, []).append(value)
            _search_in_dict(meta_names, run.get('metas') or {}, meta_series)
            _search_in_dict(metric_names,
                            run.get('metrics') or {},
                            metric_series, with_kwargsql=True)
        return meta_series, metric_series
