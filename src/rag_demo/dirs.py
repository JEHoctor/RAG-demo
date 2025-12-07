from pathlib import Path

from platformdirs import PlatformDirs

_appdirs = PlatformDirs(appname="jehoctor-rag-demo", ensure_exists=True)


def _ensure(dir_: Path) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    return dir_


DATA_DIR = _appdirs.user_data_path
CONFIG_DIR = _appdirs.user_config_path
