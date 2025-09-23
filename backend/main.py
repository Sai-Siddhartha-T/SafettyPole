import asyncio
import threading
import random
import serial
import math
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# ---------------- CONFIG ----------------
USE_SERIAL = False           # Change to True when ESP32 is connected
SERIAL_PORT = "COM3"
BAUD_RATE = 115200
# ----------------------------------------

# create FastAPI app
app = FastAPI()

# locate project root & frontend folders
BASE_DIR = Path(__file__).resolve().parent.parent   # goes up to SafettyPole/
FRONTEND_DIR = BASE_DIR / "frontend"

# mount static and templates
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

# --- Sensor State ---
class SensorState:
    def __init__(self):
        self.e_field = 0
        self.current = 0
        self.voltage = 230
        self.gps = {"lat": 0, "lon": 0, "accuracy": 0, "satellites": 0}
        self.led_on = False
        self.buzzer_on = False
        self.status = "SYSTEM SAFE"
        self.alerts = []
        self.lock = threading.Lock()

    def update_random(self):
        with self.lock:
            t = time.time()
            self.e_field = max(0, 200 + math.sin(t) * 100 + (random.random() - 0.5) * 50)
            self.current = max(0, 20 + math.sin(t/2) * 50 + (random.random() - 0.5) * 10)
            self.voltage = 230 + (random.random() - 0.5) * 5
            self.gps = {
                "lat": 10.0 + (random.random() - 0.5) * 0.001,
                "lon": 76.0 + (random.random() - 0.5) * 0.001,
                "accuracy": random.randint(5, 15),
                "satellites": random.randint(7, 12),
            }
            self._ai_classify()

    def update_values(self, e_field, current):
        with self.lock:
            self.e_field = e_field
            self.current = current
            self._ai_classify()

    def _ai_classify(self):
        # Simple AI logic (edge intelligence)
        if self.e_field > 800 or self.current > 1000:
            if self.e_field > 1200 or self.current > 1500:
                self.status = "DANGER - ALERT ACTIVE"
                self.led_on = True
                self.buzzer_on = True
                self._add_alert("danger", "Threshold exceeded! Possible snapped conductor")
            else:
                self.status = "WARNING DETECTED"
                self.led_on = True
                self.buzzer_on = False
                self._add_alert("warning", "Approaching unsafe threshold")
        else:
            self.status = "SYSTEM SAFE"
            self.led_on = False
            self.buzzer_on = False

    def _add_alert(self, level, message):
        alert = {"type": level, "message": message, "time": time.strftime("%H:%M:%S")}
        self.alerts.insert(0, alert)
        if len(self.alerts) > 10:
            self.alerts.pop()

    def get_state(self):
        with self.lock:
            return {
                "e_field": round(self.e_field, 1),
                "current": round(self.current, 1),
                "voltage": round(self.voltage, 1),
                "gps": self.gps,
                "led_on": self.led_on,
                "buzzer_on": self.buzzer_on,
                "status": self.status,
                "alerts": self.alerts,
            }

state = SensorState()

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.loop = asyncio.get_event_loop()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast_state(self):
        data = state.get_state()
        for conn in list(self.active_connections):
            try:
                await conn.send_json(data)
            except Exception:
                self.disconnect(conn)

manager = ConnectionManager()

# --- Background Loop ---
def sensor_loop():
    if USE_SERIAL:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
        while True:
            try:
                line = ser.readline().decode().strip()
                if "E-Field" in line and "Current" in line:
                    parts = line.replace("E-Field:", "").replace("Current:", "").replace("|", "").split()
                    if len(parts) >= 2:
                        e_field = int(parts[0])
                        current = int(parts[1])
                        state.update_values(e_field, current)
                        asyncio.run_coroutine_threadsafe(manager.broadcast_state(), manager.loop)
            except Exception as e:
                print("Serial read error:", e)
    else:
        while True:
            state.update_random()
            asyncio.run_coroutine_threadsafe(manager.broadcast_state(), manager.loop)
            threading.Event().wait(0.5)

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        manager.disconnect(websocket)

# Start background thread
t = threading.Thread(target=sensor_loop, daemon=True)
t.start()
