#!/usr/bin/env python3
"""List all column names in the PowerBI push dataset.

Usage:
    python list_columns.py YOUR_AZURE_PASSWORD [API_KEY]

    API_KEY is the key= value from the push URL (optional — for reading via API key)

Examples:
    python list_columns.py MyP@ssw0rd
    python list_columns.py MyP@ssw0rd AbCdEfGhIj...
"""
import sys
import json
import os

try:
    import msal
    import httpx
except ImportError:
    print("Run: pip install msal httpx")
    sys.exit(1)


def get_token(cfg, password):
    app = msal.PublicClientApplication(
        cfg["powerbi_client_id"],
        authority=f"https://login.microsoftonline.com/{cfg['powerbi_tenant_id']}",
    )
    result = app.acquire_token_by_username_password(
        username=cfg["powerbi_username"],
        password=password,
        scopes=["https://analysis.windows.net/powerbi/api/Dataset.Read.All"],
    )
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", str(result)))
    return result["access_token"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    password = sys.argv[1]
    api_key  = sys.argv[2] if len(sys.argv) > 2 else None

    config_path = os.path.join(os.path.dirname(__file__), "powerbi_config.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    dataset_id = cfg["powerbi_dataset_id"]
    group_id   = cfg["powerbi_group_id"]
    tenant_id  = cfg["powerbi_tenant_id"]

    print(f"\nDataset ID : {dataset_id}")
    print(f"Group ID   : {group_id}\n")

    # ── Step 1: Authenticate ──────────────────────────────────────
    print("Authenticating...")
    try:
        token = get_token(cfg, password)
        print("  ✅ OK\n")
    except Exception as e:
        print(f"  ❌ Auth failed: {e}")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # ── Step 2: List tables via REST API ─────────────────────────
    print("=== Method 1: List tables via REST API (/tables) ===")
    tables_url = f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}/datasets/{dataset_id}/tables"
    with httpx.Client(timeout=20) as c:
        r = c.get(tables_url, headers=headers)
    if r.status_code == 200:
        tables = r.json().get("value", [])
        table_names = []
        for t in tables:
            tname = t["name"]
            table_names.append(tname)
            cols  = t.get("columns", [])
            print(f"\n  📋 Table: '{tname}'  ({len(cols)} column(s) in schema)")
            for col in cols:
                print(f"       '{col['name']}'  ({col.get('dataType', '?')})")
    else:
        print(f"  ⚠️  {r.status_code}: {r.text[:300]}")
        table_names = ["RealTimeData"]   # fallback guess
    print()

    # ── Step 3: GET /rows from each table (Push Dataset approach) ─
    print("=== Method 2: Read rows via GET /rows (Push Dataset) ===")
    for tname in table_names:
        rows_url = (
            f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}"
            f"/datasets/{dataset_id}/tables/{tname}/rows"
        )
        with httpx.Client(timeout=30) as c:
            r = c.get(rows_url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            rows = data.get("value", data.get("rows", []))
            print(f"\n  Table '{tname}': {len(rows)} row(s) returned")
            if rows:
                print(f"  All columns:")
                for k in sorted(rows[0].keys()):
                    sample = rows[0][k]
                    print(f"    {k:50s} = {sample}")
                print(f"\n  Last row (most recent):")
                print(f"    {json.dumps(rows[-1], ensure_ascii=False, default=str)}")
        else:
            print(f"  Table '{tname}': {r.status_code} — {r.text[:300]}")

    # ── Step 4: Try executeQueries (DAX) ─────────────────────────
    print("\n=== Method 3: DAX executeQueries ===")
    dax_url = f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}/datasets/{dataset_id}/executeQueries"
    for tname in table_names:
        payload = {
            "queries": [{"query": f"EVALUATE TOPN(2, '{tname}')"}],
            "serializerSettings": {"includeNulls": True},
        }
        with httpx.Client(timeout=30) as c:
            r = c.post(dax_url, json=payload, headers=headers)
        if r.status_code == 200:
            rows = r.json()["results"][0]["tables"][0].get("rows", [])
            print(f"\n  Table '{tname}': {len(rows)} row(s) from DAX")
            if rows:
                for k in sorted(rows[0].keys()):
                    print(f"    {k:50s} = {rows[0][k]}")
        else:
            print(f"  Table '{tname}': DAX failed {r.status_code} — {r.text[:200]}")

    print("\n\n=== SUMMARY ===")
    print("Tell the assistant:")
    print("  1. Which table has the power readings?")
    print("  2. Which column is the timestamp?")
    print("  3. Which column is the total power (kW)?")
    print("  4. Which method worked (1 / 2 / 3)?")


if __name__ == "__main__":
    main()
