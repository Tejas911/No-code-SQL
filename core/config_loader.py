import yaml
import os

_config = None

def load_config(path: str = "config.yaml") -> dict:
    global _config
    if _config is None:
        with open(path, "r") as f:
            _config = yaml.safe_load(f)
    return _config
