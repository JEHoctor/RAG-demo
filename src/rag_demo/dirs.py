from platformdirs import PlatformDirs

_appdirs = PlatformDirs(appname="jehoctor-rag-demo", ensure_exists=True)

DATA_DIR = _appdirs.user_data_path
CONFIG_DIR = _appdirs.user_config_path
