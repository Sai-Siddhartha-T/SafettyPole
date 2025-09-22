window.addEventListener("DOMContentLoaded", () => {
    const ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        document.getElementById("e_field").textContent = data.e_field;
        document.getElementById("current").textContent = data.current;
        const led = document.getElementById("led_status");
        const buzzer = document.getElementById("buzzer_status");
        if (data.led_on) {
            led.textContent = "ON";
            led.className = "status-on";
        } else {
            led.textContent = "OFF";
            led.className = "status-off";
        }
        if (data.buzzer_on) {
            buzzer.textContent = "ON";
            buzzer.className = "status-on";
        } else {
            buzzer.textContent = "OFF";
            buzzer.className = "status-off";
        }
    };
    ws.onclose = () => {
        document.getElementById("e_field").textContent = "-";
        document.getElementById("current").textContent = "-";
        document.getElementById("led_status").textContent = "OFF";
        document.getElementById("led_status").className = "status-off";
        document.getElementById("buzzer_status").textContent = "OFF";
        document.getElementById("buzzer_status").className = "status-off";
        alert("WebSocket connection closed. Please refresh the page.");
    };
});
