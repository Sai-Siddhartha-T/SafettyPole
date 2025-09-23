let ws;

window.addEventListener("DOMContentLoaded", () => {
  ws = new WebSocket(`ws://${location.host}/ws`);

  const ctx = document.getElementById("sensorChart").getContext("2d");
  const chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "E-Field (V/m)", borderColor: "cyan", data: [], fill: false },
        { label: "Current (mA)", borderColor: "lime", data: [], fill: false }
      ]
    },
    options: { responsive: true, animation: false }
  });

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Sensor values
    document.getElementById("e_field").textContent = data.e_field;
    document.getElementById("current").textContent = data.current;
    document.getElementById("voltage").textContent = data.voltage;
    document.getElementById("latitude").textContent = data.gps.lat.toFixed(6);
    document.getElementById("longitude").textContent = data.gps.lon.toFixed(6);
    document.getElementById("accuracy").textContent = data.gps.accuracy;

    updateStatus(data.status, data.led_on, data.buzzer_on);

    // Chart update
    chart.data.labels.push(new Date().toLocaleTimeString());
    chart.data.datasets[0].data.push(data.e_field);
    chart.data.datasets[1].data.push(data.current);
    if (chart.data.labels.length > 20) {
      chart.data.labels.shift();
      chart.data.datasets.forEach(d => d.data.shift());
    }
    chart.update();

    // Alerts
    const alertsEl = document.getElementById("alerts");
    alertsEl.innerHTML = "";
    data.alerts.forEach(a => {
      const li = document.createElement("li");
      li.textContent = `[${a.time}] ${a.message}`;
      li.className = a.type;
      alertsEl.appendChild(li);
    });
  };
});

function updateStatus(status, led, buzzer) {
  const statusBadge = document.getElementById("status");
  statusBadge.textContent = status;
  statusBadge.className =
    "status-badge " +
    (status.includes("DANGER") ? "danger" :
     status.includes("WARNING") ? "warning" : "safe");

  const ledEl = document.getElementById("led_status");
  ledEl.textContent = led ? "ON" : "OFF";
  ledEl.className = led ? "status-on" : "status-off";

  const buzzerEl = document.getElementById("buzzer_status");
  buzzerEl.textContent = buzzer ? "ON" : "OFF";
  buzzerEl.className = buzzer ? "status-on" : "status-off";
}

function sendControl(action) {
  fetch("/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action })
  });
}

function updateConfig() {
  const efieldThreshold = document.getElementById("efieldThreshold").value;
  const currentThreshold = document.getElementById("currentThreshold").value;
  fetch("/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ efieldThreshold, groundThreshold: currentThreshold })
  });
}
