import serial

ser = serial.Serial("COM3", 115200)
while True:
    line = ser.readline().decode().strip()
    e_field, current = map(int, line.split(","))
    print("E-Field:", e_field, "Current:", current)
