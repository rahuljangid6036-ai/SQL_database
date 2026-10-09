import os
from pathlib import Path


class ConfigurationError(ValueError):
    pass


def _load_env_file(path):
    if not path.exists():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigurationError(
                f"Invalid .env entry on line {line_number}: expected KEY=VALUE."
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "").isalnum():
            raise ConfigurationError(f"Invalid environment variable name on line {line_number}.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def get_database_config():
    _load_env_file(Path(__file__).with_name(".env"))
    config = {
        "host": os.getenv("DB_HOST", "localhost").strip(),
        "port": os.getenv("DB_PORT", "5432").strip(),
        "dbname": os.getenv("DB_NAME", "student_management").strip(),
        "user": os.getenv("DB_USER", "postgres").strip(),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    if not config["password"]:
        raise ConfigurationError(
            "DB_PASSWORD is required. Set it in task_8/.env or the environment."
        )
    try:
        config["port"] = int(config["port"])
    except ValueError as error:
        raise ConfigurationError("DB_PORT must be an integer.") from error
    if not 1 <= config["port"] <= 65535:
        raise ConfigurationError("DB_PORT must be between 1 and 65535.")
    for key in ("host", "dbname", "user"):
        if not config[key]:
            raise ConfigurationError(f"{key.upper()} cannot be empty.")
    return config
