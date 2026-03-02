"""Power BI REST API client using MSAL delegated permission.

This module will be activated when USE_MOCK_DATA=false.
Requires proper Power BI credentials in config/env vars.
"""
import httpx
import msal
from config import (
    POWERBI_CLIENT_ID,
    POWERBI_TENANT_ID,
    POWERBI_USERNAME,
    POWERBI_PASSWORD,
    POWERBI_DATASET_ID,
    POWERBI_GROUP_ID,
)

AUTHORITY = f"https://login.microsoftonline.com/{POWERBI_TENANT_ID}"
SCOPES = ["https://analysis.windows.net/powerbi/api/Dataset.Read.All"]


def _get_access_token() -> str:
    """Acquire token using ROPC (Resource Owner Password Credentials) flow."""
    app = msal.PublicClientApplication(POWERBI_CLIENT_ID, authority=AUTHORITY)
    result = app.acquire_token_by_username_password(
        username=POWERBI_USERNAME,
        password=POWERBI_PASSWORD,
        scopes=SCOPES,
    )
    if "access_token" not in result:
        raise RuntimeError(f"Failed to acquire token: {result.get('error_description', result)}")
    return result["access_token"]


async def fetch_power_readings() -> list[dict]:
    """Execute DAX query against Power BI dataset and return readings.

    Returns list of {"timestamp": str, "device_name": str, "value": float}
    """
    token = _get_access_token()

    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{POWERBI_GROUP_ID}"
        f"/datasets/{POWERBI_DATASET_ID}/executeQueries"
    )

    # TODO: Adjust DAX query to match your actual Power BI dataset schema
    dax_query = {
        "queries": [
            {
                "query": """
                    EVALUATE
                    SELECTCOLUMNS(
                        'PowerReadings',
                        "timestamp", 'PowerReadings'[Timestamp],
                        "device_name", 'PowerReadings'[DeviceName],
                        "value", 'PowerReadings'[Value]
                    )
                """
            }
        ],
        "serializerSettings": {"includeNulls": True},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=dax_query,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    # Parse Power BI response
    rows = data["results"][0]["tables"][0]["rows"]
    from datetime import datetime

    readings = []
    for row in rows:
        readings.append({
            "timestamp": row.get("timestamp", datetime.utcnow().isoformat()),
            "device_name": row.get("device_name", "unknown"),
            "value": float(row.get("value", 0)),
        })

    return readings
