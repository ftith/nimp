# -*- coding: utf-8 -*-

import argparse
import copy

#-------------------------------------------------------------------------------
class Command:
    #---------------------------------------------------------------------------
    def __init__(self,
                 name,
                 help,
                 dependencies=[]):
        self._name = name
        self._help = help
        self._dependencies = dependencies

    #---------------------------------------------------------------------------
    def name(self):
        return self._name

    #---------------------------------------------------------------------------
    def help(self):
        return self._help

    #---------------------------------------------------------------------------
    def dependencies(self):
        return self._dependencies

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        assert(False)

    #---------------------------------------------------------------------------
    def check(self, env):
        return True

