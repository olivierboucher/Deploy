import os, json
from utilities import get_string, valid_address, valid_ssh_connection, valid_config, Terminal
from git import Repo, InvalidGitRepositoryError


class DeployError(Exception):
    """ Base exception class for Deploy program.  """

    def __init__(self, message, base=None):
        super(DeployError, self).__init__(message)
        self.base_exception = base


class Deploy(object):
    def __init__(self, command):
        self.cmd = command
        self.commands = {
            'init': self._cmd_init,
            'now': self._cmd_now,
        }
        self.presets = {
            'java:gradle': '',
            'java:maven': '',
            'js:node': ''
        }

    def _cmd_init(self):
        """ Interactively creates a config file

        Raises:
            DeployError: if it is impossible to write the config to disc.

        """
        # Local info
        #   Project name, default to current dir
        directory = os.path.basename(os.getcwd())
        project = get_string(
            'Enter the project\'s name.',
            default=directory,
            validate=lambda x: x is not '',
            error_msg='The project field cannot be empty.\n')

        #   Preset, must choose from available presets
        presets_list = reduce(lambda x, y: x + '\n\t- ' + y, self.presets)
        preset = get_string(
            'Select the apropriate preset.',
            validate=lambda x: x in self.presets,
            error_msg='The selected preset does not exist. Please refer to this list:\n\t- ' + presets_list)

        #   Source dir
        source_dir = get_string(
            'Enter the source directory relative path. (Optional)',
            validate=lambda x: x is '' or os.path.exists(os.getcwd() + '/' + x),
            error_msg='The selected directory does not exist')

        #   Build dir
        build_dir = get_string(
            'Enter the build directory containing the binaries relative path. (Optional)',
            validate=lambda x: x is '' or os.path.exists(os.getcwd() + '/' + x),
            error_msg='The selected directory does not exist')

        # Remote
        #   Server address
        srv_address = get_string(
            'Enter the remote server address.',
            validate=valid_address,
            error_msg='The address must be a valid IP or hostname.')

        #   Server user
        srv_user = get_string(
            'Enter the remote server user.',
            validate=lambda x: x is not '',
            error_msg='The user field cannot be empty.')

        # Test SSH connection
        if not valid_ssh_connection(srv_address, srv_user):
            Terminal.print_warn('Could not validate SSH connection.')

        # Write .deploy file
        config = {
            'server': {
                'address': srv_address,
                'user': srv_user
            },
            'project': {
                'name': project,
                'preset': preset,
                'directories': {
                    'source': source_dir,
                    'build': build_dir
                }
            },
            'scripts': {
                'before': [],
                'after': []
            }
        }

        try:
            with open('.deploy', 'w+') as file_handle:
                json.dump(config, file_handle, sort_keys=True, indent=4, separators=(',', ': '))
        except IOError, e:
            raise DeployError('Could not write config file to disk. > %s' % e, base=e)

    def _read_config(self):
        """ Read the configuration file and parses it.
            It then assigns the config to the current Deploy instance.

        Raises:
            DeployError: if the config is missing or invalid.

        """
        try:
            with open('.deploy', 'r') as file_handle:
                config_json = file_handle.read()
                if valid_config(config_json):
                    self.config = json.loads(config_json)
                else:
                    raise DeployError('Invalid configuration file, please refer to previous errors.')
        except IOError, e:
            raise DeployError('Config file not found nor present.\n\t> %s' % e, base=e)
        except ValueError, e:
            raise DeployError('Invalid configuration file, could not parse JSON.\n\t> %s' % e, base=e)

    def _read_repository(self):
        """ Tries to load the git repository located at current working directory.
            It then assigns the repository to the current Deploy instance.

        Raises:
            DeployError: if there is no git repository.

        """
        try:
            self.repository = Repo(os.getcwd())
        except InvalidGitRepositoryError, e:
            raise DeployError('No git repository was found.\n\t> %s' % e, base=e)

    def _cmd_now(self):
        """ Tries to synchronize the project state with the remote server, then reloads the app remotely.
        """
        # Initial asserts
        #   [ ] Config file is valid.
        self._read_config()
        #   [ ] Is called from root of a git repo.
        #   [ ] SSH connection is working.
        #   [ ] Server has supervisor and git installed.
        #   [ ] ~/.deploy/{project} exists and is a git repo, otherwise initialize one.
        #   [ ] Local repo has the remote server

        # Warnings
        #   [ ] Local repo has uncommitted changes
        #   [ ] Remote repo is already up to date

        # Do the do
        #   [ ] Push to the remote
        #   [ ] Run the before scripts
        #   [ ] Run the preset
        #   [ ] Run the after scripts

    def execute(self):
        try:
            self.commands[self.cmd]()
        except DeployError, e:
            Terminal.print_error(str(e))
