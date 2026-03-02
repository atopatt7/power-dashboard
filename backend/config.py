"""Configuration for Power Monitoring Dashboard."""
import os

# === Power BI Configuration (fill in when ready to connect) ===
POWERBI_CLIENT_ID = os.getenv("POWERBI_CLIENT_ID", "")
POWERBI_TENANT_ID = os.getenv("POWERBI_TENANT_ID", "")
POWERBI_USERNAME = os.getenv("POWERBI_USERNAME", "")
POWERBI_PASSWORD = os.getenv("POWERBI_PASSWORD", "")
POWERBI_DATASET_ID = os.getenv("POWERBI_DATASET_ID", "")
POWERBI_GROUP_ID = os.getenv("POWERBI_GROUP_ID", "")

# === Database ===
SQLITE_PATH = os.getenv("SQLITE_PATH", "./power_data.db")

# === Server ===
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# === Polling ===
POLL_INTERVAL_SECONDS = 10

# === Data Retention ===
RETENTION_DAYS = 7

# === Mock Mode ===
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

# === Device Groups (詳細設備清單) ===
DEVICE_GROUPS = {
    "全廠": [
        "全廠總用電",
    ],
    "高壓盤": [
        "一號高壓盤總功率",
        "一號高壓盤總功率因數",
        "一號高壓盤總用電度",
        "二號高壓盤總功率",
        "二號高壓盤總功率因數",
        "二號高壓盤總用電度",
    ],
    "洗砂設備": [
        "臥式洗砂機總功率",
        "立式洗砂機總功率",
    ],
    "集塵設備": [
        "P101集塵總功率",
        "P102集塵總功率",
        "P103洗砂集塵總功率",
        "P103震動集塵總功率",
        "P103砂回收集塵總功率",
    ],
    "空壓設備": [
        "漢鐘定頻100HP-加工",
        "向陽100HP變頻-加工",
        "漢鐘50HP變頻B組",
        "凱薩50HP定頻研磨",
    ],
    "電爐設備": [
        "10T電爐總功率",
        "10T水泵與風扇",
        "6T電爐總功率",
        "6T水泵與風扇",
        "3T電爐總功率",
        "3T水泵與風扇",
    ],
    "砂回收設備": [
        "B組砂回收機總功率",
        "CD組砂回收機總功率",
        "EF組砂回收機總功率",
    ],
    "辦公室用電": [
        "一樓辦公室總功率",
        "二樓辦公室總功率",
        "三樓辦公室總功率",
    ],
    "FMS設備": [
        "FMS高位震篩機總功率",
    ],
}

# Flatten all device names
ALL_DEVICES = []
for devices in DEVICE_GROUPS.values():
    ALL_DEVICES.extend(devices)
