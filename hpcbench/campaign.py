import re

from . toolbox.collections_ext import Configuration


def from_file(campaign_file):
    campaign = Configuration.from_file(campaign_file)
    return fill_default_campaign_values(campaign)


def fill_default_campaign_values(campaign):
    default_campaign = dict(
        output_dir="benchmark-%Y%m%d-%H:%M:%S"
    )
    for k, v in default_campaign.items():
        campaign.setdefault(k, v)
    campaign.setdefault('network', {})
    campaign.network.setdefault('tags', {})
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
    return campaign
