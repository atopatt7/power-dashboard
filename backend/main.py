"""Backend server for Power Consumption Monitoring Dashboard.

Uses Python stdlib only (http.server + sqlite3 + threading).
No external dependencies required.
"""
import json
import logging
import threading
import time
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from config import (
    POLL_INTERVAL_SECONDS,
    DEVICE_GROUPS, ALL_DEVICES, HOST, PORT,
)
from database import init_db, insert_readings, query_readings, get_latest_readings, cleanup_old_data
from mock_data import generate_mock_readings
from config_manager import load_config, save_config, validate_powerbi_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Determine frontend path ─────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")


# ─── Background data poller ──────────────────────────────────
class DataPoller(threading.Thread):
    """Background thread that polls data every N seconds."""

    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()

    def run(self):
        cleanup_counter = 0
        while not self._stop_event.is_set():
            try:
                config = load_config()
                use_mock = config.get("use_mock_data", True)

                if use_mock:
                    readings = generate_mock_readings()
                else:
                    try:
                        from powerbi_client import fetch_power_readings
                        readings = fetch_power_readings(config)
                        if not readings:
                            logger.warning("PowerBI returned no readings — skipping insert")
                    except Exception as pbi_err:
                        logger.error(f"PowerBI fetch failed: {pbi_err}")
                        readings = []  # keep existing DB rows; don't overwrite with mock

                insert_readings(readings)
                logger.info(f"Inserted {len(readings)} readings")
            except Exception as e:
                logger.error(f"Polling error: {e}")

            # Cleanup every ~360 iterations (1 hour at 10s interval)
            cleanup_counter += 1
            if cleanup_counter >= 360:
                try:
                    cleanup_old_data()
                    logger.info("Old data cleanup done")
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
                cleanup_counter = 0

            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def stop(self):
        self._stop_event.set()


# ─── HTTP Request Handler ────────────────────────────────────
class APIHandler(BaseHTTPRequestHandler):
    """Handle API requests and serve frontend."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API routes
        if path == "/api/power-history":
            self._handle_power_history(params)
        elif path == "/api/power-latest" or path == "/api/latest":
            self._handle_power_latest()
        elif path == "/api/devices":
            self._handle_devices()
        elif path == "/api/health":
            self._handle_health()
        elif path == "/api/peak-forecast":
            self._handle_peak_forecast(params)
        elif path == "/api/config":
            self._handle_get_config()
        elif path == "/" or path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif path == "/config" or path == "/config.html":
            self._serve_file("config.html", "text/html")
        elif path.startswith("/"):
            # Try to serve static files from frontend dir
            filename = path.lstrip("/")
            ext = os.path.splitext(filename)[1]
            content_types = {
                ".html": "text/html",
                ".js": "application/javascript",
                ".css": "text/css",
                ".json": "application/json",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
            }
            ct = content_types.get(ext, "application/octet-stream")
            self._serve_file(filename, ct)
        else:
            self._send_404()

    def _handle_peak_forecast(self, params):
        try:
            from forecast import get_forecast
            threshold = float(params.get("threshold", [700])[0])
            hours     = int(params.get("hours", [4])[0])
            result    = get_forecast(threshold=threshold, hours=hours)
            self._send_json(result)
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            self._send_json({"error": str(e)}, 500)

    def _handle_power_history(self, params):
        device = params.get("device", [None])[0]
        start = params.get("start", [None])[0]
        end = params.get("end", [None])[0]
        days = params.get("days", [None])[0]
        limit = int(params.get("limit", [10000])[0])

        # If days parameter is provided, calculate start time
        if days:
            try:
                days_int = int(days)
                from datetime import datetime, timedelta
                start = (datetime.utcnow() - timedelta(days=days_int)).isoformat()
            except (ValueError, TypeError):
                pass

        data = query_readings(device=device, start=start, end=end, limit=limit)
        self._send_json({"count": len(data), "data": data})

    def _handle_power_latest(self):
        data = get_latest_readings()
        self._send_json({"count": len(data), "data": data})

    def _handle_devices(self):
        self._send_json({"groups": DEVICE_GROUPS, "all_devices": ALL_DEVICES})

    def _handle_health(self):
        config = load_config()
        self._send_json({
            "status": "ok",
            "mock_mode": config.get("use_mock_data", True),
            "poll_interval": POLL_INTERVAL_SECONDS,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def _handle_get_config(self):
        """Return current configuration (mask password)."""
        config = load_config()
        # Don't expose password in response
        config["powerbi_password"] = "••••••••" if config.get("powerbi_password") else ""
        self._send_json(config)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(FRONTEND_DIR, filename)
        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self._send_404()

    def _send_404(self):
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "not found"}).encode())

    def do_POST(self):
        """Handle POST requests for configuration."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Read body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # Route handlers
        if path == "/api/config":
            self._handle_save_config(data)
        elif path == "/api/config/set-mode":
            self._handle_set_mode(data)
        elif path == "/api/config/test-connection":
            self._handle_test_connection(data)
        elif path == "/api/config/reset-db":
            self._handle_reset_db()
        else:
            self._send_404()

    def _handle_save_config(self, data):
        """Save Power BI configuration."""
        config = {
            "use_mock_data": data.get("use_mock_data", True),
            "powerbi_client_id": data.get("powerbi_client_id", ""),
            "powerbi_tenant_id": data.get("powerbi_tenant_id", ""),
            "powerbi_username": data.get("powerbi_username", ""),
            "powerbi_password": data.get("powerbi_password", ""),
            "powerbi_dataset_id": data.get("powerbi_dataset_id", ""),
            "powerbi_group_id": data.get("powerbi_group_id", ""),
        }

        # Validation
        is_valid, errors = validate_powerbi_config(config)
        if not is_valid and not config["use_mock_data"]:
            self._send_json({"success": False, "errors": errors}, 400)
            return

        if save_config(config):
            self._send_json({"success": True, "message": "配置已保存"})
            logger.info("Power BI configuration saved")
        else:
            self._send_json({"success": False, "error": "保存失敗"}, 500)

    def _handle_set_mode(self, data):
        """Toggle between Mock and Power BI mode."""
        use_mock = data.get("use_mock_data", True)
        config = load_config()
        config["use_mock_data"] = use_mock

        if save_config(config):
            mode = "Mock" if use_mock else "Power BI"
            self._send_json({"success": True, "message": f"已切換至 {mode} 模式"})
            logger.info(f"Mode changed to: {mode}")
        else:
            self._send_json({"success": False, "error": "切換失敗"}, 500)

    def _handle_test_connection(self, data):
        """Test Power BI connection — actually authenticates via MSAL."""
        try:
            config = {
                "powerbi_client_id": data.get("powerbi_client_id", ""),
                "powerbi_tenant_id": data.get("powerbi_tenant_id", ""),
                "powerbi_username":  data.get("powerbi_username", ""),
                "powerbi_password":  data.get("powerbi_password", ""),
                "powerbi_dataset_id": data.get("powerbi_dataset_id", ""),
                "powerbi_group_id":  data.get("powerbi_group_id", ""),
            }

            # First validate fields are not empty
            is_valid, errors = validate_powerbi_config(config)
            if not is_valid:
                self._send_json({"success": False, "error": "; ".join(errors)}, 400)
                return

            # Actually attempt MSAL authentication
            try:
                from powerbi_client import test_connection
                ok, msg = test_connection(config)
                if ok:
                    self._send_json({"success": True, "message": msg})
                else:
                    self._send_json({"success": False, "error": msg}, 400)
            except ImportError:
                self._send_json({
                    "success": False,
                    "error": "msal / httpx 套件未安裝，請先執行 pip install msal httpx"
                }, 500)

        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_reset_db(self):
        """Reset database (delete all records)."""
        try:
            db_path = os.path.join(os.path.dirname(__file__), "power_data.db")
            if os.path.isfile(db_path):
                os.remove(db_path)
            init_db()
            self._send_json({"success": True, "message": "資料庫已清除並重新初始化"})
            logger.info("Database reset")
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress default request logging (too noisy with polling)
        pass


# ─── Main ────────────────────────────────────────────────────
def main():
    # Load configuration
    config = load_config()
    use_mock = config.get("use_mock_data", True)

    # Initialize database
    init_db()
    logger.info(f"Database initialized at {os.path.abspath('power_data.db')}")
    logger.info(f"Mock mode: {use_mock}")
    logger.info("Config file location: powerbi_config.json")

    # Insert initial data
    readings = generate_mock_readings()
    insert_readings(readings)
    logger.info(f"Initial {len(readings)} readings inserted")

    # Start background poller
    poller = DataPoller()
    poller.start()
    logger.info(f"Data poller started (every {POLL_INTERVAL_SECONDS}s)")

    # Start HTTP server
    server = HTTPServer((HOST, PORT), APIHandler)
    logger.info(f"Server running at http://{HOST}:{PORT}")
    logger.info(f"Frontend served from {FRONTEND_DIR}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        poller.stop()
        server.shutdown()


if __name__ == "__main__":
    main()
