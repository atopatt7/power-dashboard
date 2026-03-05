"""Configuration file manager for Power Monitoring Dashboard.

Priority order:
  1. powerbi_config.json  (local / dev)
  2. Environment variables (Railway / production)

Railway environment variable names:
  POWERBI_USE_MOCK       → "false" to enable real data (default: "true")
  POWERBI_CLIENT_ID      → Azure app client ID
  POWERBI_TENANT_ID      → Azure tenant ID
  POWERBI_USERNAME       → Azure username
  POWERBI_PASSWORD       → Azure password
  POWERBI_DATASET_ID     → PowerBI dataset ID
  POWERBI_GROUP_ID       → PowerBI workspace (group) ID
"""
import json
import os
from pathlib import Path

CONFIG_FILE = "powerbi_config.json"


def get_config_path():
    """Get the full path to config file."""
    return os.path.join(os.path.dirname(__file__), CONFIG_FILE)


def _config_from_env() -> dict:
    """Build config dict from environment variables."""
    use_mock_str = os.environ.get("POWERBI_USE_MOCK", "true").strip().lower()
    use_mock = use_mock_str not in ("false", "0", "no")
    return {
        "use_mock_data":      use_mock,
        "powerbi_client_id":  os.environ.get("POWERBI_CLIENT_ID", ""),
        "powerbi_tenant_id":  os.environ.get("POWERBI_TENANT_ID", ""),
        "powerbi_username":   os.environ.get("POWERBI_USERNAME", ""),
        "powerbi_password":   os.environ.get("POWERBI_PASSWORD", ""),
        "powerbi_dataset_id": os.environ.get("POWERBI_DATASET_ID", ""),
        "powerbi_group_id":   os.environ.get("POWERBI_GROUP_ID", ""),
    }


def load_config():
    """Load configuration — JSON file first, env vars as fallback."""
    config_path = get_config_path()
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")

    # Fallback: read from environment variables (Railway / production)
    env_cfg = _config_from_env()
    if any(env_cfg[k] for k in ("powerbi_client_id", "powerbi_tenant_id",
                                 "powerbi_username", "powerbi_password")):
        print("Info: Using configuration from environment variables")
        return env_cfg

    # Default (mock mode)
    return {
        "use_mock_data": True,
        "powerbi_client_id": "",
        "powerbi_tenant_id": "",
        "powerbi_username": "",
        "powerbi_password": "",
        "powerbi_dataset_id": "",
        "powerbi_group_id": "",
    }


def save_config(config_data: dict):
    """Save configuration to JSON file."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def get_config_value(key, default=None):
    """Get a single config value."""
    config = load_config()
    return config.get(key, default)


def update_config(updates: dict):
    """Update specific config values."""
    config = load_config()
    config.update(updates)
    return save_config(config)


def validate_powerbi_config(config: dict) -> tuple:
    """Validate Power BI configuration.

    Returns: (is_valid, error_messages)
    """
    errors = []

    if not config.get("powerbi_client_id", "").strip():
        errors.append("Power BI Client ID 不能為空")

    if not config.get("powerbi_tenant_id", "").strip():
        errors.append("Tenant ID 不能為空")

    if not config.get("powerbi_username", "").strip():
        errors.append("使用者名稱不能為空")

    if not config.get("powerbi_password", "").strip():
        errors.append("密碼不能為空")

    if not config.get("powerbi_dataset_id", "").strip():
        errors.append("Dataset ID 不能為空")

    if not config.get("powerbi_group_id", "").strip():
        errors.append("Group ID 不能為空")

    return len(errors) == 0, errors
