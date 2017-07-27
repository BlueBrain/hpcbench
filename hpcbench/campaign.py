"""HPCBench campaign helper functions
"""
import re
import uuid

from . toolbox.collections_ext import (
    Configuration,
    nameddict,
)


def from_file(campaign_file):
    """Load campaign from YAML file

    :param campaign_file: path to YAML file
    :return: memory representation of the YAML file
    :rtype: dictionary
    """
    campaign = Configuration.from_file(campaign_file)
    return fill_default_campaign_values(campaign)


def fill_default_campaign_values(campaign):
    """Fill an existing campaign with default
    values for optional keys

    :param campaign: dictionary
    :return: object provided in parameter
    :rtype: dictionary
    """
    default_campaign = dict(
        output_dir="hpcbench-%Y%m%d-%H:%M:%S"
    )
    for key, value in default_campaign.items():
        campaign.setdefault(key, value)
    campaign.setdefault('network', nameddict())
    campaign['network'].setdefault('nodes', ['localhost'])
    campaign.setdefault('campaign_id', str(uuid.uuid4()))
    campaign.network.setdefault('tags', {})
    campaign.benchmarks.setdefault('*', {})
    for tag in list(campaign.network.tags):
        config = campaign.network.tags[tag]
        if isinstance(config, dict):
            config = [config]
            campaign.network.tags[tag] = config
        for pattern in config:
            for mode in list(pattern):
                if mode == 'match':
                    pattern[mode] = re.compile(pattern[mode])
                elif mode == 'nodes':
                    if not isinstance(pattern[mode], list):
                        raise Exception('Invalid "nodes" value type.'
                                        ' list expected')
                    pattern[mode] = set(pattern[mode])
                else:
                    raise Exception('Unknown tag association pattern: %s',
                                    mode)
    set_export_campaign_section(campaign)
    return campaign


def set_export_campaign_section(campaign):
    """Add default values for the ``export`` section
    """
    campaign.setdefault('export', nameddict())
    campaign.export.setdefault('elasticsearch', nameddict())
    campaign.export.elasticsearch.setdefault('host', 'localhost')
    campaign.export.elasticsearch.setdefault('connection_params', {})
    campaign.export.elasticsearch.setdefault('index_name',
                                             'hpcbench-{date}')
    return campaign


def get_benchmark_types(campaign):
    """Get of benchmarks referenced in the configuration

    :return: benchmarks
    :rtype: string generator
    """
    for benchmarks in campaign.benchmarks.values():
        for benchmark in benchmarks.values():
            yield benchmark.type


def get_metrics(campaign):
    """Get all metrics of a campaign

    :return: metrics
    :rtype: dictionary generator
    """
    for hostname, host_driver in campaign.traverse():
        for tag, tag_driver in host_driver.traverse():
            for suite, bench_obj in tag_driver.traverse():
                for category, cat_obj in bench_obj.traverse():
                    yield (
                        dict(
                            hostname=hostname,
                            tag=tag,
                            category=category,
                            suite=suite,
                            campaign_id=campaign.campaign.campaign_id,
                        ),
                        cat_obj.metrics
                    )
