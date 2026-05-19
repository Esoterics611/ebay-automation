import json
import os
from pathlib import Path


def load_env_config() -> dict:
    profile = os.getenv("PROFILE", "dev")
    db_path = Path(__file__).parent.parent / "db" / "environments.json"
    data: dict = json.loads(db_path.read_text())
    if profile not in data:
        raise KeyError(f"Unknown PROFILE '{profile}'. Valid: {list(data)}")
    return data[profile]
