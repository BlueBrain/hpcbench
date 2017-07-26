"""Draw figures from extracted metrics
"""
import hashlib
import operator

from hpcbench.toolbox.edsl import kwargsql
from hpcbench.toolbox.functools_ext import compose
from hpcbench.toolbox.collections_ext import flatten_dict


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

    def sort_metrics(self, desc, metrics):
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

            def key_builder_func(metric):
                return list(
                    map(
                        lambda g: g(metric['metas']),
                        key_builder
                    )
                )
            metrics.sort(key=key_builder_func)
        return metrics

    def select_metrics(self, desc):
        """
        :return: metrics required to draw the figure
        :rtype: dictionary
        """
        selectables = desc.get('select') or []
        if not selectables:
            return self.metrics
        return filter(
            lambda m: kwargsql.and_(m, **selectables),
            self.metrics
        )

    def build_series(self, desc, metrics):
        """Transform JSON metrics to data series used by matplotlib
        """
        meta_names = list(
            map(
                lambda m: m[1:] if m.startswith('-') else m,
                desc['series'].get('metas') or []
            )
        )
        metric_names = desc['series']['metrics']
        meta_series = dict()
        metric_series = dict()
        for run in metrics:
            def search_in_dict(keys, d, serie, with_kwargsql=False):
                for name in keys:
                    if not with_kwargsql:
                        value = d.get(name)
                    else:
                        value = kwargsql.get(d, name)
                    if value is not None:
                        serie.setdefault(name, []).append(value)
            search_in_dict(meta_names, run.get('metas') or {}, meta_series)
            search_in_dict(metric_names,
                           run.get('metrics') or {},
                           metric_series, with_kwargsql=True)
        return meta_series, metric_series
