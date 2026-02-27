import pygame
import serial
import time
import argparse

parser = argparse.ArgumentParser(description="Xbox controller to Arduino serial bridge")
parser.add_argument("--port", type=str, required=True, help="Arduino COM port, e.g., COM4 or /dev/ttyUSB0")
parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default 115200)")
args = parser.parse_args()

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No Xbox controller found!")
    exit()

js = pygame.joystick.Joystick(0)
js.init()

try:
    ser = serial.Serial(args.port, args.baud, timeout=1)
    print(f"Connected to Arduino on {args.port} at {args.baud} baud")
except serial.SerialException:
    print(f"Could not connect to Arduino on {args.port}. Check COM port.")
    exit()

def send_cmd(lx, ly, rx, ry, a, b, x, y, dpx, dpy, lb, rb, lt, rt):
    msg = f"<{lx:.2f},{ly:.2f},{rx:.2f},{ry:.2f},{a},{b},{x},{y},{dpx},{dpy},{lb},{rb},{lt},{rt}>\n"
    ser.write(msg.encode())

    
def main():
    while True:
        pygame.event.pump()

        lx = js.get_axis(0) # allocate drive (fast)
        ly = -1 * js.get_axis(1) # allocate drive (fast)

        rx = js.get_axis(2) # allocate drive (slow, ideally)
        ry = -1 * js.get_axis(3) # alloctae drive (slow, ideally)

        a  = js.get_button(0) # claw end effector close 
        b  = js.get_button(1) # claw end effector open 
        x  = js.get_button(2) # 
        y  = js.get_button(3) # 

        lb = js.get_button(4) # linear actuator base extend
        rb = js.get_button(5) # linear actuator shoulder extend
        lt = int(js.get_axis(4) > 0.0)  # linear actuator base retract
        rt = int(js.get_axis(5) > 0.0) # linear actuator shoulder retract

        dpx, dpy = js.get_hat(0) # wrist

        print(f"L({lx:.2f},{ly:.2f}) R({rx:.2f},{ry:.2f}) A:{a} B:{b} X:{x} Y:{y} DPX:{dpx} DPY:{dpy} LB:{lb} RB:{rb} LT:{lt} RT:{rt}")

        send_cmd(lx, ly, rx, ry, a, b, x, y, dpx, dpy, lb, rb, lt, rt)

        time.sleep(0.05) # 20 Hz

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        ser.close()
        pygame.quit()
