#!/usr/bin/env python3
"""Discover the schema of your PowerBI dataset.

This script connects to your Power BI dataset and prints:
  - All table names and their columns/measures
  - A sample of real data from the most recent rows
  - A suggested DAX query for powerbi_client.py

Usage (run from the  backend/  directory):
    python discover_schema.py YOUR_AZURE_PASSWORD

Example:
    python discover_schema.py MyP@ssw0rd
"""
import sys
import json
import os

try:
    import msal
    import httpx
except ImportError:
    print("Missing dependencies. Run: pip install msal httpx")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    password = sys.argv[1]

    # Load credentials from powerbi_config.json
    config_path = os.path.join(os.path.dirname(__file__), "powerbi_config.json")
    if not os.path.isfile(config_path):
        print(f"ERROR: Config file not found at {config_path}")
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    client_id  = config.get("powerbi_client_id", "")
    tenant_id  = config.get("powerbi_tenant_id", "")
    username   = config.get("powerbi_username", "")
    dataset_id = config.get("powerbi_dataset_id", "")
    group_id   = config.get("powerbi_group_id", "")

    if not all([client_id, tenant_id, username, dataset_id, group_id]):
        print("ERROR: powerbi_config.json is missing required fields.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  PowerBI Schema Discovery")
    print(f"{'='*60}")
    print(f"  Username  : {username}")
    print(f"  Dataset ID: {dataset_id}")
    print(f"  Group ID  : {group_id}")
    print(f"{'='*60}\n")

    # ── Step 1: Authenticate ──────────────────────────────────────
    print("Step 1: Authenticating via MSAL ROPC...")
    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    result = app.acquire_token_by_username_password(
        username=username,
        password=password,
        scopes=["https://analysis.windows.net/powerbi/api/Dataset.Read.All"],
    )

    if "access_token" not in result:
        print(f"\n❌ Authentication FAILED:")
        print(f"   {result.get('error_description', result)}")
        print("\nPossible fixes:")
        print("  - Check that your password is correct")
        print("  - Ensure MFA is not required for this account")
        print("  - Verify the client_id supports ROPC flow")
        sys.exit(1)

    token = result["access_token"]
    print("  ✅ Authentication successful!\n")

    headers = {"Authorization": f"Bearer {token}"}
    base_url = f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}/datasets/{dataset_id}"

    # ── Step 2: List tables via REST API ─────────────────────────
    print("Step 2: Fetching table list via REST API...")
    with httpx.Client(timeout=20) as client:
        resp = client.get(f"{base_url}/tables", headers=headers)

    if resp.status_code == 200:
        tables = resp.json().get("value", [])
        print(f"  Found {len(tables)} table(s):\n")
        for table in tables:
            tname = table["name"]
            cols  = table.get("columns", [])
            meas  = table.get("measures", [])
            print(f"  📋 Table: '{tname}'")
            for col in cols:
                dtype = col.get("dataType", "?")
                print(f"       Column  : '{col['name']}'  ({dtype})")
            for m in meas:
                print(f"       Measure : '{m['name']}'")
            print()
    else:
        print(f"  ⚠️  Tables REST API returned {resp.status_code} — trying DAX fallback...\n")
        tables = []

    # ── Step 3: DAX INFO.TABLES() for comprehensive list ─────────
    print("Step 3: Querying dataset schema via DAX INFO.COLUMNS()...")
    dax_url = f"{base_url}/executeQueries"
    dax_payload = {
        "queries": [{"query": """
            EVALUATE
            SELECTCOLUMNS(
                FILTER(INFO.COLUMNS(), [ExplicitDataType] <> BLANK()),
                "TableName",  [TableID],
                "Table",      RELATED(INFO.TABLES()[Name]),
                "Column",     [ExplicitName],
                "DataType",   [ExplicitDataType]
            )
        """}],
        "serializerSettings": {"includeNulls": True},
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(dax_url, json=dax_payload, headers=headers)

    dax_columns = []
    if resp.status_code == 200:
        rows = resp.json()["results"][0]["tables"][0].get("rows", [])
        if rows:
            print(f"  Found {len(rows)} column(s):\n")
            cur_table = None
            for row in rows:
                tbl = row.get("[Table]") or row.get("Table") or "?"
                col = row.get("[Column]") or row.get("Column") or "?"
                dtype = row.get("[DataType]") or row.get("DataType") or "?"
                dax_columns.append({"table": tbl, "column": col, "dtype": dtype})
                if tbl != cur_table:
                    print(f"  📋 Table: '{tbl}'")
                    cur_table = tbl
                print(f"       '{col}'  ({dtype})")
            print()
        else:
            print("  ⚠️  INFO.COLUMNS() returned no rows (might not be supported)\n")
    else:
        print(f"  ⚠️  DAX INFO.COLUMNS() failed ({resp.status_code}): {resp.text[:200]}\n")

    # ── Step 4: Attempt TOPN sample on each known table ──────────
    all_tables = list({c["table"] for c in dax_columns if c["table"] != "?"})
    if not all_tables and tables:
        all_tables = [t["name"] for t in tables]

    if all_tables:
        print("Step 4: Sampling top 2 rows from each table...\n")
        for tbl in all_tables[:5]:   # limit to 5 tables
            sample_dax = {
                "queries": [{"query": f"EVALUATE TOPN(2, '{tbl}')"}],
                "serializerSettings": {"includeNulls": True},
            }
            with httpx.Client(timeout=20) as client:
                resp = client.post(dax_url, json=sample_dax, headers=headers)
            if resp.status_code == 200:
                sample_rows = resp.json()["results"][0]["tables"][0].get("rows", [])
                print(f"  Table '{tbl}' — sample rows:")
                for row in sample_rows:
                    print(f"    {json.dumps(row, ensure_ascii=False, default=str)}")
                print()
            else:
                print(f"  Table '{tbl}' — TOPN failed ({resp.status_code})\n")
    else:
        print("Step 4: No tables to sample (check Step 2/3 output above)\n")

    # ── Step 5: Print suggested config ───────────────────────────
    print(f"{'='*60}")
    print("  NEXT STEP")
    print(f"{'='*60}")
    print("""
Based on the output above, update the constants at the top of
  backend/powerbi_client.py:

  TABLE_NAME   = "..."   # the table that has power readings
  TIME_COLUMN  = "..."   # the datetime/timestamp column
  VALUE_COLUMN = "..."   # the kW value column
  DEVICE_NAME  = "全廠總用電"  # keep this as-is

Then let the assistant know the table and column names and
it will write the final DAX query for you.
""")


if __name__ == "__main__":
    main()
