# -*- coding: utf-8 -*-

from nimp.commands._cis_command      import *
from nimp.utilities.ue3              import *
from nimp.utilities.deployment       import *
from nimp.utilities.ue3_deployment   import *

#-------------------------------------------------------------------------------
class CisUe3Ship(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-ship', 'Cooks and publish a final version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        CisCommand.configure_arguments(self, context, parser)

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'Dlc to cook',
                            metavar = '<dlc>',
                            default = None)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        platforms = ["Win64"]

        if not context.is_win64:
            platforms += [context.platform]

        #with deploy_latest_revision(context, context.cis_version_directory, context.revision, platforms):
        if not ue3_ship(context):
            return False

        return True