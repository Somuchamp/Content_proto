import os
import shutil
import sys
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from functools import lru_cache

# Centralised Local AppData configuration directory to resolve Windows Program Files permission blocks
appdata_base = os.getenv("LOCALAPPDATA")
if not appdata_base:
    appdata_base = os.path.expanduser("~")

APP_DATA_DIR = os.path.join(appdata_base, "ContentStudioAI", "data")
ENV_DIR = os.path.join(appdata_base, "ContentStudioAI")
ENV_PATH = os.path.join(ENV_DIR, ".env")
APP_LOG_PATH = os.path.join(APP_DATA_DIR, "app.log")

# Proactively setup logging directory and root logger handlers
os.makedirs(APP_DATA_DIR, exist_ok=True)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()

try:
    file_handler = logging.FileHandler(APP_LOG_PATH, encoding="utf-8")
    file_formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
except Exception:
    pass

if sys.stdout is not None:
    try:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    except Exception:
        pass

logging.info("Centralized application logging initialized successfully.")

# Proactive first-launch sync: copy local template .env to AppData if missing
os.makedirs(ENV_DIR, exist_ok=True)
if not os.path.exists(ENV_PATH):
    # Check if a template .env exists in current working directory or executable's directory
    local_env = ".env"
    if os.path.exists(local_env):
        try:
            shutil.copy(local_env, ENV_PATH)
        except Exception:
            pass
    else:
        # Also check relative to sys.executable (useful when running inside PyInstaller .exe)
        import sys
        exe_dir_env = os.path.join(os.path.dirname(sys.executable), ".env")
        if os.path.exists(exe_dir_env):
            try:
                shutil.copy(exe_dir_env, ENV_PATH)
            except Exception:
                pass

# Load environment configuration from AppData folder into os.environ
load_dotenv(dotenv_path=ENV_PATH, override=True)


class Settings(BaseSettings):
    YOUTUBE_API_KEY: str = ""
    SERP_API_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "ecom-content-tool/1.0"
    OPENAI_API_KEY: str = ""

    CSV_DIR: str = os.path.join(APP_DATA_DIR, "csv")
    JSON_DIR: str = os.path.join(APP_DATA_DIR, "json")

    class Config:
        env_file = ENV_PATH
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()