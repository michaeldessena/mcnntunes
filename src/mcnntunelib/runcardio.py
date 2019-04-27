# -*- coding: utf-8 -*-
"""
Performs MC tunes using Neural Networks
@authors: Stefano Carrazza & Simone Alioli
"""

import yaml, glob
from .tools import show, error

class ConfigError(ValueError): pass


class Config(object):
    """the yaml parser"""

    def __init__(self, content):
        """load lhe files"""
        self.content = content
        self.patterns = self.get('input', 'patterns')
        self.unpatterns = self.get('input', 'unpatterns')
        self.expfiles = self.get('input', 'expfiles')
        self.seed = self.get('model', 'seed')
        self.scan = self.get('model', 'scan')
        if not self.scan:
            self.noscan_setup = self.get('model', 'noscan_setup')
        else:
            self.scan_setup = self.get('model', 'scan_setup')
        self.bounds = self.get('minimizer','bounds')
        self.restarts = self.get('minimizer','restarts')

    def discover_yodas(self):
        try:
            self.yodafiles = []
            folders = self.content['input']['folders']
            for folder in folders:
                for f in glob.glob('%s/*.yoda' % folder):
                    self.yodafiles.append(f)
                if len(self.yodafiles) == 0:
                    error('No yoda files found in %s' % folder)
            self.yodafiles.sort()
            show('\n- Detected %d files with MC runs from:' % len(self.yodafiles))
            for folder in folders:
                show('  ==] %s' % folder)
        except:
            error('Error "input" keyword not found in runcard.')

    def get(self, node, key):
        """"""
        try:
            return self.content[node][key]
        except:
            error('Error key "%s" not found in node "%s"' % (key, node))

    @classmethod
    def from_yaml(cls, stream):
        """read yaml from stream"""
        try:
            return cls(yaml.load(stream))
        except yaml.error.MarkedYAMLError as e:
            error('Failed to parse yaml file: %s' % e)
