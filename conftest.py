import pytest
from dotenv import load_dotenv
from utils.config import load_env_config

load_dotenv()


@pytest.fixture(scope="session")
def env_config():
    return load_env_config()


@pytest.fixture(scope="session")
def base_url(env_config):
    return env_config["base_url"]
