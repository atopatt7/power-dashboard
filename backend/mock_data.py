"""Mock data generator for development and testing."""
import random
import math
from datetime import datetime
from config import ALL_DEVICES, DEVICE_GROUPS

# Base power values per device (in kW)
# Note: Some devices have special handling for power factor and usage
BASE_POWER_BY_DEVICE = {
    # 全廠
    "全廠總用電": (800, 1500),

    # 高壓盤 (總功率為主，功率因數0.8-0.95，用電度為能量消耗)
    "一號高壓盤總功率": (200, 400),
    "一號高壓盤總功率因數": (80, 95),           # 百分比
    "一號高壓盤總用電度": (500, 1000),         # kWh
    "二號高壓盤總功率": (200, 400),
    "二號高壓盤總功率因數": (80, 95),
    "二號高壓盤總用電度": (500, 1000),

    # 洗砂設備
    "臥式洗砂機總功率": (50, 100),
    "立式洗砂機總功率": (40, 80),

    # 集塵設備
    "P101集塵總功率": (20, 50),
    "P102集塵總功率": (20, 50),
    "P103洗砂集塵總功率": (15, 40),
    "P103震動集塵總功率": (10, 30),
    "P103砂回收集塵總功率": (15, 35),

    # 空壓設備
    "漢鐘定頻100HP-加工": (70, 120),
    "向陽100HP變頻-加工": (60, 110),
    "漢鐘50HP變頻B組": (35, 70),
    "凱薩50HP定頻研磨": (35, 65),

    # 電爐設備
    "10T電爐總功率": (150, 400),
    "10T水泵與風扇": (20, 50),
    "6T電爐總功率": (100, 300),
    "6T水泵與風扇": (15, 40),
    "3T電爐總功率": (60, 200),
    "3T水泵與風扇": (10, 30),

    # 砂回收設備
    "B組砂回收機總功率": (30, 80),
    "CD組砂回收機總功率": (40, 100),
    "EF組砂回收機總功率": (40, 100),

    # 辦公室用電
    "一樓辦公室總功率": (8, 25),
    "二樓辦公室總功率": (8, 25),
    "三樓辦公室總功率": (5, 20),

    # FMS設備
    "FMS高位震篩機總功率": (100, 250),
}

# Group-based base power for reference
BASE_POWER = {
    "全廠": (800, 1500),
    "高壓盤": (400, 600),
    "洗砂設備": (90, 180),
    "集塵設備": (60, 155),
    "空壓設備": (200, 365),
    "電爐設備": (360, 1020),
    "砂回收設備": (110, 280),
    "辦公室用電": (21, 70),
    "FMS設備": (100, 250),
}


def _get_group_for_device(device_name: str) -> str:
    for group, devices in DEVICE_GROUPS.items():
        if device_name in devices:
            return group
    return "辦公室"


def generate_mock_readings() -> list[dict]:
    """Generate one set of mock readings for all devices."""
    now = datetime.utcnow().isoformat()
    readings = []

    # Add time-of-day variation (simulate higher load during working hours)
    hour = datetime.utcnow().hour
    time_factor = 1.0
    if 8 <= hour <= 17:
        time_factor = 1.2
    elif 0 <= hour <= 5:
        time_factor = 0.6

    for device in ALL_DEVICES:
        # Get base power for this specific device
        if device in BASE_POWER_BY_DEVICE:
            low, high = BASE_POWER_BY_DEVICE[device]
        else:
            # Fallback to group-based power
            group = _get_group_for_device(device)
            low, high = BASE_POWER.get(group, (10, 100))

        base = random.uniform(low, high)

        # Add some noise and time-based variation
        noise = random.gauss(0, (high - low) * 0.05)
        # Sinusoidal variation to simulate realistic fluctuation
        sin_component = math.sin(datetime.utcnow().timestamp() / 60) * (high - low) * 0.1

        value = max(0, (base + noise + sin_component) * time_factor)
        readings.append({
            "timestamp": now,
            "device_name": device,
            "value": round(value, 2),
        })

    return readings
