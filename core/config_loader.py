import yaml
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_dir="configs"):
        self.config_dir = Path(config_dir)

    def load(self, config_name):
        # Ensure config_name is treated as a full path
        config_path = Path(config_name)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
