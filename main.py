import asyncio
import threading
import random
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Form

@app.post("/update")
async def update(e_field: int = Form(...), current: int = Form(...)):
    with state.lock:
        state.e_field = e_field
        state.current = current
        state.led_on = e_field > 800 or current > 1000
        state.buzzer_on = state.led_on
    return {"status": "ok"}


app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Simulation State ---
class SensorState:
    def __init__(self):
        self.e_field = 0
        self.current = 0
        self.led_on = False
        self.buzzer_on = False
        self.lock = threading.Lock()

    def update(self):
        # Simulate sensor values (replace with your logic if needed)
        # For demo: random walk for values
        with self.lock:
            self.e_field = max(0, min(4095, self.e_field + random.randint(-100, 100)))
            self.current = max(0, min(4095, self.current + random.randint(-120, 120)))
            # Thresholds (same as your sketch.ino)
            E_FIELD_THRESHOLD = 800
            CURRENT_THRESHOLD = 1000
            self.led_on = self.e_field > E_FIELD_THRESHOLD or self.current > CURRENT_THRESHOLD
            self.buzzer_on = self.led_on

    def get_state(self):
        with self.lock:
            return {
                "e_field": self.e_field,
                "current": self.current,
                "led_on": self.led_on,
                "buzzer_on": self.buzzer_on,
            }

state = SensorState()

# --- Background Simulation Task ---
def sensor_simulation_loop():
    while True:
        state.update()
        asyncio.run_coroutine_threadsafe(manager.broadcast_state(), manager.loop)
        # 200ms delay as in Arduino sketch
        threading.Event().wait(0.2)

# --- WebSocket Connection Manager ---
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

# --- FastAPI Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # Keep connection open; data sent by simulator
    except Exception:
        manager.disconnect(websocket)

# --- Start simulation in background thread ---
t = threading.Thread(target=sensor_simulation_loop, daemon=True)
t.start()
