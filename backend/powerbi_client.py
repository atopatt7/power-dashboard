"""Power BI REST API client (synchronous, MSAL ROPC flow).

Activated when use_mock_data=false in powerbi_config.json.
Called from DataPoller in main.py with the loaded config dict.

─── HOW TO FIND YOUR TABLE / COLUMN NAMES ─────────────────────────────────
Run the schema discovery script once:

    python discover_schema.py YOUR_AZURE_PASSWORD

It will print every table and column in your dataset and show sample rows.
Then update TABLE_NAME, TIME_COLUMN, and VALUE_COLUMN below to match.
────────────────────────────────────────────────────────────────────────────
"""
import logging
from datetime import datetime

try:
    import httpx
    import msal
except ImportError:
    raise ImportError("Required packages missing. Run: pip install msal httpx")

logger = logging.getLogger(__name__)

SCOPES = ["https://analysis.windows.net/powerbi/api/Dataset.Read.All"]

# ── UPDATE THESE to match your actual PowerBI dataset schema ────────────────
# Run  python discover_schema.py YOUR_PASSWORD  to find the right names.
#
# Common patterns:
#   Wide table  → one row per timestamp, separate column for each device
#   Narrow table → device_name column + value column (like the current DAX)
#
TABLE_NAME   = "RealTimeData"  # confirmed by discover_schema.py
TIME_COLUMN  = "時間"           # confirmed by discover_schema.py
VALUE_COLUMN = "全廠總用電"     # ← confirm this via list_columns.py
DEVICE_NAME  = "全廠總用電"     # label stored in DB (keep this)
# ────────────────────────────────────────────────────────────────────────────


def _get_access_token(client_id: str, tenant_id: str,
                      username: str, password: str) -> str:
    """Acquire an OAuth2 token using ROPC (username + password) flow."""
    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    result = app.acquire_token_by_username_password(
        username=username,
        password=password,
        scopes=SCOPES,
    )
    if "access_token" not in result:
        raise RuntimeError(
            f"Failed to acquire token: {result.get('error_description', result)}"
        )
    return result["access_token"]


def fetch_power_readings(config: dict) -> list[dict]:
    """Fetch the most recent power reading from the PowerBI dataset.

    Args:
        config: dict loaded from powerbi_config.json, must contain:
                powerbi_client_id, powerbi_tenant_id, powerbi_username,
                powerbi_password, powerbi_group_id, powerbi_dataset_id

    Returns:
        List of {"timestamp": str, "device_name": str, "value": float}.
        Returns a single entry for 全廠總用電 (the latest row in the dataset).
    """
    token = _get_access_token(
        config["powerbi_client_id"],
        config["powerbi_tenant_id"],
        config["powerbi_username"],
        config["powerbi_password"],
    )

    group_id   = config["powerbi_group_id"]
    dataset_id = config["powerbi_dataset_id"]

    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}"
        f"/datasets/{dataset_id}/executeQueries"
    )

    # Push/Streaming datasets only support simple DAX — no SELECTCOLUMNS.
    # TOPN(n, table, orderCol, 0) → 0 = DESC (most recent first).
    dax_query = {
        "queries": [
            {
                "query": (
                    f"EVALUATE TOPN(1, '{TABLE_NAME}', "
                    f"'{TABLE_NAME}'[{TIME_COLUMN}], 0)"
                )
            }
        ],
        "serializerSettings": {"includeNulls": True},
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            json=dax_query,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    rows = data["results"][0]["tables"][0].get("rows", [])

    if not rows:
        logger.warning("PowerBI returned 0 rows — dataset may be empty")
        return []

    readings = []
    now_iso = datetime.utcnow().isoformat()
    for row in rows:
        # Simple TOPN (no SELECTCOLUMNS) returns keys as "TableName[ColumnName]".
        # e.g. "RealTimeData[時間]", "RealTimeData[全廠總用電]"
        ts  = (row.get(f"{TABLE_NAME}[{TIME_COLUMN}]")
               or row.get(f"[{TIME_COLUMN}]")
               or row.get("timestamp")
               or now_iso)
        val = (row.get(f"{TABLE_NAME}[{VALUE_COLUMN}]")
               or row.get(f"[{VALUE_COLUMN}]")
               or row.get("value")
               or 0)
        readings.append({
            "timestamp":   str(ts),
            "device_name": DEVICE_NAME,
            "value":       float(val),
        })

    logger.info(f"PowerBI: fetched {len(readings)} reading(s), latest value={readings[0]['value']:.1f} kW")
    return readings


def test_connection(config: dict) -> tuple[bool, str]:
    """Test authentication only (no DAX query).

    Returns: (success, message)
    """
    try:
        _get_access_token(
            config["powerbi_client_id"],
            config["powerbi_tenant_id"],
            config["powerbi_username"],
            config["powerbi_password"],
        )
        return True, "連線成功 — 認證通過"
    except Exception as e:
        return False, f"連線失敗: {e}"
