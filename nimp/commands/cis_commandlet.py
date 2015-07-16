# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.ue4         import *
from nimp.utilities.deployment  import *
from nimp.utilities.packaging   import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class CisCommandlet(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-commandlet', 'Executes an Unreal commandlet.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        CisCommand.configure_arguments(self, env, parser)

        parser.add_argument('commandlet',
                            help    = 'Commandlet name',
                            metavar = '<COMMAND>')

        parser.add_argument('args',
                            help    = 'Commandlet arguments',
                            metavar = '<ARGS>',
                            nargs    = argparse.REMAINDER)

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        with deploy_latest_revision(env, env.publish_version, env.revision, ['win64']):

            # Unreal Engine 4
            if hasattr(env, 'project_type') and env.project_type is 'UE4':
                return ue4_commandlet(env, env.commandlet, *env.args)

            # Unreal Engine 3
            if hasattr(env, 'project_type') and env.project_type is 'UE3':
                return ue3_commandlet(env.game, env.commandlet, list(env.args))
