import argparse

import os
import sys
import shutil

import git
import pip
from infrared.core.plugins import PluginsInspector
from infrared import api


class SpecManager(object):
    """
    Manages all the available specifications (specs).
    """

    def __init__(self):
        # create entry point
        self.parser = argparse.ArgumentParser(prog="Infrared 2.0v")
        if len(sys.argv) == 1:
            self.parser.print_help()
            sys.exit(1)
        self.root_subparsers = self.parser.add_subparsers(dest="subcommand")
        self.spec_objects = {}

    def register_spec(self, spec_object):
        spec_object.extend_cli(self.root_subparsers)
        self.spec_objects[spec_object.get_name()] = spec_object

    def run_specs(self):
        args = vars(self.parser.parse_args())
        subcommand = args.get('subcommand', '')

        if subcommand in self.spec_objects:
            self.spec_objects[subcommand].spec_handler(self.parser, args)


class PluginManagerSpec(api.SpecObject):
    def extend_cli(self, root_subparsers):
        parser_plugin = root_subparsers.add_parser(self.name, **self.kwargs)
        plugins_subparsers = parser_plugin.add_subparsers(dest="command0",
                                                          help="List of actions for plugin manager.")
        # list command
        plugins_subparsers.add_parser(
            'list', help='List all the available plugins')
        # install plugin
        init_parser = plugins_subparsers.add_parser(
            'install', help='Install a core plugin')
        init_parser.add_argument("name", help="Plugin name")
        # install all core plugins
        plugins_subparsers.add_parser(
            'install-all', help='Install all the core plugin')
        # remove plugin
        deinit_parser = plugins_subparsers.add_parser(
            'remove', help='Removes / Uninstalls a core plugin')
        deinit_parser.add_argument("name", help="Plugin name")

    def spec_handler(self, parser, args):
        """
        Handles all the plugin manager commands
        :param parser: the infrared parser object.
        :param args: the list of arguments received from cli.
        """
        command0 = args.get('command0', '')

        if command0 == 'list':
            self._list_plugins()
        elif command0 == 'install':
            self._init_plugin(args['name'])
        elif command0 == 'install-all':
            self._init_all_plugins()
        elif command0 == 'remove':
            self._deinit_plugin(args['name'])

    @staticmethod
    def _list_plugins():
        """
        Actually this will list all the modules and check if we have repo cloned.
        :return:
        """
        root_repo = git.Repo(os.getcwd())
        print("Available plugins:")
        for submodule in root_repo.submodules:
            #  trying to get repo
            status = 'installed' if submodule.module_exists() else 'available'
            print('\t [{status}] {name}'.format(name=submodule.name, status=status))

    def _init_all_plugins(self):
        root_repo = git.Repo(os.getcwd())
        for submodule in root_repo.submodules:
            print("Installing plugin: '{}'...".format(submodule.name))
            submodule.update(init=True, force=True)
            self._install_requirements(submodule)

    @staticmethod
    def _install_requirements(submodule):
        # iter_plugins will go through all the plugins subfolders and check what we have there.
        for plugin in PluginsInspector.iter_plugins():
            if os.path.abspath(plugin.root_dir) == os.path.abspath(submodule.path):
                requirement_file = os.path.join(plugin.root_dir, "plugin_requirements.txt")
                if os.path.isfile(requirement_file):
                    print("Installing requirements from: {}".format(requirement_file))
                    pip_args = ['install', '-r', requirement_file]
                    pip.main(args=pip_args)
                break

    @staticmethod
    def _deinit_plugin(name):
        root_repo = git.Repo(os.getcwd())
        for submodule in root_repo.submodules:
            if submodule.name == name:
                git.Git(os.getcwd()).execute(['git', 'submodule', 'deinit', '-f', submodule.path])
                # need also remove .git/modules/<module_path> folder..
                git_mod_path = os.path.join(os.getcwd(), '.git', 'modules', submodule.name)
                if os.path.exists(git_mod_path):
                    shutil.rmtree(git_mod_path)
                print("Submodule '{}' has been removed.".format(submodule.name))
                break

    def _init_plugin(self, name):
        root_repo = git.Repo(os.getcwd())
        for submodule in root_repo.submodules:
            if submodule.name == name:
                print("Installing plugin: '{}'...".format(submodule.name))
                submodule.update(init=True, force=True)
                self._install_requirements(submodule)
                break
        else:
            print("Plugin '{}' was not found in submodules.".format(name))


def main():
    specs_manager = SpecManager()
    if sys.argv[0] == 1:
        specs_manager.parser.print_help()
    specs_manager.register_spec(PluginManagerSpec("plugin-manager",
                                                  help="Plugin manager is responsible for a"
                                                       "host of actions."))
    # add all the plugins
    for plugin in PluginsInspector.iter_plugins():
        specs_manager.register_spec(api.DefaultInfraredPluginSpec(plugin))

    specs_manager.run_specs()


if __name__ == '__main__':
    sys.exit(int(main() or 0))
