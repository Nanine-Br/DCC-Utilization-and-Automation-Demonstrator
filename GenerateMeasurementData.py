import random
from datetime import datetime as dt
import time
import sys
import threading
import multiprocessing
import pygetwindow as gw
from pywinauto import Desktop
from Process_Manager import PM

stop_flag = False

def stdin_listener():
    """Separate thread, waiting for Stop-Signal."""
    global stop_flag
    for line in sys.stdin:
        if line.strip() == "STOP":
            print("Stop-Signal recieved. Subprocess terminated.")
            stop_flag = True
            break  # Terminates the thread

thread = threading.Thread(target=stdin_listener, daemon=True)
thread.start()
print(f"Thread started: {thread.is_alive()}")

zahl = random.uniform(0, 30)
max_abstand = 0.2

while not stop_flag:
    try:
        fenster = gw.getAllWindows()
        # Get the window by its title
        window_title = "DCC Demonstrator"
        windows = gw.getWindowsWithTitle(window_title)

        # Check if the window is still open
        if windows:
            window = windows[0]  # Assuming we want the first window with the title
            timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            zahl = zahl + random.uniform(-max_abstand, max_abstand)
            with open(r"Messdaten.csv", "a") as file:
                file.writelines(f"{timestamp}, {round(zahl, 2)}\n")
            time.sleep(1)

        else:
            # Window is closed
            open(r"Messdaten.csv", "w").close()
            break
    except Exception as e:
        print(f"An error occurred: {e}")
        break 
    



