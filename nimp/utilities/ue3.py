# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil

from nimp.utilities.build            import *
from nimp.utilities.deployment       import *
from nimp.utilities.ue3_deployment   import *

VERSION_FILE_PATH = "Development\\Src\\Engine\\DNE\\DNEOnlineSuiteBuildId.h"

#-------------------------------------------------------------------------------
def load_ue3_context(context):
    if hasattr(context, "platform"):
        build_platforms = {"PS4"       : "Orbis",
                           "XboxOne"   : "Dingo",
                           "Win64"     : "Win64",
                           "Win32"     : "Win32",
                           "XBox360"   : "Xbox360",
                           "PS3"       : "PS3" }
        cook_platforms = { "PS4"       : "Orbis",
                           "XboxOne"   : "Dingo",
                           "Win64"     : "PC",
                           "Win32"     : "PCConsole",
                           "XBox360"   : "Xbox360",
                           "PS3"       : "PS3" }


        context.ue3_cook_platform  = cook_platforms[context.platform]
        context.ue3_build_platform = build_platforms[context.platform]

        if  hasattr(context, 'dlc'):
            if context.dlc is None:
                context.dlc = context.project

        configuration = context.configuration.lower() if hasattr(context, 'configuration') else 'final'
        dlc           = context.dlc if hasattr(context, 'dlc') else context.project
        suffix        = 'Final' if configuration in ['test', 'final'] else ''

        if dlc == context.project:
            context.ue3_cook_directory = '{0}\\Cooked{1}{2}'.format(context.game, context.ue3_cook_platform, suffix)
        else:
           context.ue3_cook_directory = '{0}\\DLC\\{1}\\{2}\\Cooked{1}{3}'.format(context.game, context.ue3_cook_platform, context.dlc, suffix)

#-------------------------------------------------------------------------------
def generate_toc(context, dlc):
    for language in context.languages:
        call_process(".", [ "Binaries\CookerSync.exe",
                            context.game,
                            "-p", context.ue3_cook_platform,
                            "-x",  "Loc",
                            "-r", language,
                            "-nd",
                            "-final",
                            "-dlcname", dlc])

    call_process(".", [ "Binaries\CookerSync.exe",
                        context.game,
                        "-p", context.ue3_cook_platform,
                        "-x",  "ConsoleSyncProgrammer",
                        "-r", "INT",
                        "-nd",
                        "-final",
                        "-dlcname", dlc])
    return True

#---------------------------------------------------------------------------
def ue3_build(context):
    load_ue3_context(context)
    solution        = context.solution
    configuration   = context.configuration
    vs_version      = context.vs_version
    result          = True
    version_file_cl = None

    log_verbose("Building UBT")
    if not _ue3_build_project(solution, "Development/Src/UnrealBuildTool/UnrealBuildTool.csproj", 'Release', vs_version):
        log_error("Error building UBT")
        return False

    def _build():
        if context.is_win64:
            if not _ue3_build_editor_dlls(solution, configuration, vs_version):
                return False

        overrided_solution      = solution
        overrided_vs_version    = vs_version
        if context.is_x360:
            overrided_vs_version = "10"
            overrided_solution   = "whatif_vs2010.sln"

        if not _ue3_build_game(overrided_solution, context.ue3_build_platform, configuration, overrided_vs_version):
            return False

        return True

    if context.generate_version_file:
        with _ue3_generate_version_file():
            return _build()
    else:
        return _build()

#---------------------------------------------------------------------------
def ue3_ship(context, destination = None):
    load_ue3_context(context)
    master_directory = context.format(context.cis_master_directory)

    if os.path.exists(master_directory):
        log_notification("Found a master at {0} : I'm going to build a patch", master_directory)
        if context.dlc == context.project:
            return _ship_game_patch(context, destination or context.cis_ship_patch_directory)
        else:
            log_error("Sry, building a DLC patch is still not implemented")
    else:
        if context.dlc == context.project:
            log_error("Sry, building a game master is still not implemented")
        else:
            _ship_dlc(context, destination or context.cis_ship_directory)

#---------------------------------------------------------------------------
def _ship_dlc(context, destination):
    dlc_config_file = context.format(context.dlc_config_path)
    if not context.load_config_file(dlc_config_file):
        log_error("Unable to load config file at {0}", dlc_config_file)
        return False

    map = context.cook_maps[context.dlc.lower()]

    deploy_master = robocopy(context).override(dlc = context.project).files().recursive().frm(context.cis_master_directory)
    log_notification("***** Deploying master...")
    if not all(deploy_master()):
        return False

    log_notification("***** Deploying master patch...")
    deploy_master_patch = robocopy(context).override(dlc = context.project).files().recursive().frm(context.cis_ship_patch_directory)
    if not all(deploy_master_patch()):
        return False

    log_notification("***** Cooking...")
    if not ue3_cook(context.game,
                    map,
                    context.languages,
                    context.dlc,
                    context.ue3_cook_platform,
                    'final',
                    incremental = True):
        return False

    log_notification("***** Generating toc...")
    if not generate_toc(context, context.dlc):
        return False

    log_notification("***** Copying DLC to output directory...")
    publish_dlc = robocopy(context).to(destination)
    return all(ue3_map_dlc(publish_dlc))

#---------------------------------------------------------------------------
def _ship_game_patch(context, destination):
    patch_config_file = context.format(context.patch_config_path)
    if not context.load_config_file(patch_config_file):
        log_error("Unable to load path config file at {0}", patch_config_file)
        return False

    map = context.cook_maps[context.dlc.lower()]

    deploy_master = robocopy(context).files().recursive().frm(context.cis_master_directory)
    log_notification("***** Deploying master...")
    if not all(deploy_master()):
        return False

    log_notification("***** Cooking on top of master...")
    if not ue3_cook(context.game,
                    map,
                    context.languages,
                    None,
                    context.ue3_cook_platform,
                    'final',
                    incremental = True):
        return False


    log_notification("***** Redeploying master cook ignoring patched files...")
    patch_files   = list_sources(vars(context)).frm(context.cis_master_directory)
    patch_files   = ue3_map_patch(patch_files)
    deploy_master = robocopy(context).exclude(*patch_files).files().recursive().frm(context.cis_master_directory)

    if not all(deploy_master()):
        return False

    log_notification("***** Generating toc...")
    if not generate_toc(context, dlc = "Episode01" if context.dlc == context.project else context.dlc):
        return False

    log_notification("***** Copying patched files to output directory...")
    publish_patch = robocopy(context).to(destination)
    return all(ue3_map_patch(publish_patch))


#---------------------------------------------------------------------------
def ue3_commandlet(game, name, args):
    game_directory  = os.path.join('Binaries', 'Win64')
    game_path       = os.path.join(game_directory, game + '.exe')

    if not os.path.exists(game_path):
        log_error('Unable to find game executable at {0}', game_path)
        return False

    cmdline = [ game_path, name ] + args + ['-nopause', '-buildmachine', '-forcelogflush']

    return call_process(game_directory, cmdline) == 0

#---------------------------------------------------------------------------
def ue3_build_script(game):
    return ue3_commandlet(game, 'make', ['-full', '-release']) and ue3_commandlet(game, 'make', [ '-full', '-final_release' ])

#---------------------------------------------------------------------------
def ue3_cook(game, map, languages, dlc, platform, configuration, noexpansion = False, incremental = False):
    commandlet_arguments =  [ map]

    if not incremental:
        commandlet_arguments += ['-full']

    if configuration in [ 'test', 'final' ]:
        commandlet_arguments += [ '-cookforfinal' ]

    commandlet_arguments += ['-multilanguagecook=' + '+'.join(languages), '-platform='+ platform ]

    if dlc is not None:
        commandlet_arguments += ["-dlcname={0}".format(dlc)]

    if noexpansion:
        commandlet_arguments += [ '-noexpansion' ]


    return ue3_commandlet(game, 'cookpackages', commandlet_arguments)

#---------------------------------------------------------------------------
def _ue3_build_project(sln_file, project, configuration, vs_version, target = 'Rebuild'):
    base_dir = 'Development/Src'
    sln_file = os.path.join(base_dir, sln_file)

    return vsbuild(sln_file, 'Mixed platforms', configuration, project, vs_version, target)

#---------------------------------------------------------------------------
def _ue3_build_editor_dlls(sln_file, configuration, vs_version):
    log_notification("Building Editor C# libraries")

    editor_config = 'Debug' if configuration.lower() == "debug" else 'Release'

    if not _ue3_build_project(sln_file, 'Development/Src/UnrealEdCSharp/UnrealEdCSharp.csproj', editor_config, vs_version):
        return False

    if not _ue3_build_project(sln_file, 'Development/Src/DNEEdCSharp/DNEEdCSharp.csproj', editor_config, vs_version):
        return False

    dll_target = os.path.join('Binaries/Win64/Editor', editor_config)
    dll_source = os.path.join('Binaries/Editor', editor_config)

    try:
        if not os.path.exists(dll_target):
            os.makedirs(dll_target)
        shutil.copy(os.path.join(dll_source, 'DNEEdCSharp.dll'), dll_target)
        shutil.copy(os.path.join(dll_source, 'DNEEdCSharp.pdb'), dll_target)
        shutil.copy(os.path.join(dll_source, 'UnrealEdCSharp.dll'), dll_target)
        shutil.copy(os.path.join(dll_source, 'UnrealEdCSharp.pdb'), dll_target)
    except Exception as ex:
        log_error("Error while copying editor dlls {0}".format(ex))
        return False
    return True

#-------------------------------------------------------------------------------
def _ue3_build_game(sln_file, platform, configuration, vs_version):
    dict_vcxproj = {
        'win32'   : 'Development/Src/Windows/ExampleGame Win32.vcxproj',
        'win64'   : 'Development/Src/Windows/ExampleGame Win64.vcxproj',
        'ps3'     : 'Development/Src/PS3/ExampleGame PS3.vcxproj',
        'orbis'   : 'Development/Src/ExampleGame PS4/ExampleGame PS4.vcxproj',
        'ps4'     : 'Development/Src/ExampleGame PS4/ExampleGame PS4.vcxproj',
        'xbox360' : 'ExampleGame Xbox360', # Xbox360 Uses VS 2010
        'dingo'   : 'Development/Src/Dingo/ExampleGame Dingo/ExampleGame Dingo.vcxproj',
        'xboxone' : 'Development/Src/Dingo/ExampleGame Dingo/ExampleGame Dingo.vcxproj',
    }

    platform_project = dict_vcxproj[platform.lower()]
    return _ue3_build_project(sln_file, platform_project, configuration, vs_version, 'Build')

#---------------------------------------------------------------------------
@contextlib.contextmanager
def _ue3_generate_version_file():
    version_file_format    = "#define SEE_ONLINE_SUITE_BUILD_ID \"{0}@%Y-%m-%dT%H:%M:%S.000Z@{1}-v4\"\n#define DNE_FORCE_USE_ONLINE_SUITE 1";
    machine_name           = socket.gethostname()
    random_character       = random.choice(string.ascii_lowercase)
    version_file_content   = version_file_format.format(random_character, machine_name)
    version_file_content   = time.strftime(version_file_content, time.gmtime())

    with p4_transaction("Version File Checkout", ) as transaction:
        transaction.add(VERSION_FILE_PATH)
        transaction.abort()
        with open(VERSION_FILE_PATH, "w") as version_file:
            version_file.write(version_file_content)

        yield
