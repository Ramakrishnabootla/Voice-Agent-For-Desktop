import subprocess
import time
import msvcrt
from Backend.TTS import print_slow_and_speak, TTS
import psutil

def check_battery_status():
    """Reports the current battery percentage and charging status of the laptop."""
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            message = "Battery information is not available. This might be a desktop computer."
        else:
            percent = battery.percent
            charging = battery.power_plugged
            status = "charging" if charging else "not charging"
            message = f"Battery is at {percent} percent and is currently {status}."
        print_slow_and_speak(message)
        return message
    except Exception as e:
        error_msg = f"Error checking battery status: {str(e)}"
        print_slow_and_speak(error_msg)
        return error_msg

def shutdown_laptop():
    """Safely shuts down the user's laptop after prompting for confirmation."""
    message = "Are you sure you want to shutdown? Make sure you have saved your work. Press Enter to proceed, Esc to cancel, or wait 5 seconds for auto-shutdown."
    print_slow_and_speak(message)

    start_time = time.time()
    while time.time() - start_time < 5:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\r':  # Enter key
                TTS("Shutting down now.")
                subprocess.run(["shutdown", "/s", "/t", "0"])
                return "Shutting down the laptop."
            elif key == b'\x1b':  # Esc key
                TTS("Shutdown cancelled.")
                return "Shutdown cancelled."
        time.sleep(0.1)

    # Auto-shutdown after 5 seconds
    TTS("No input received. Shutting down automatically.")
    subprocess.run(["shutdown", "/s", "/t", "0"])
    return "Auto-shutting down the laptop."

def restart_laptop():
    """Restarts the user's laptop after confirmation."""
    message = "Are you sure you want to restart? Make sure you have saved your work. Press Enter to proceed, Esc to cancel, or wait 5 seconds for auto-restart."
    print_slow_and_speak(message)

    start_time = time.time()
    while time.time() - start_time < 5:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\r':  # Enter key
                TTS("Restarting now.")
                subprocess.run(["shutdown", "/r", "/t", "0"])
                return "Restarting the laptop."
            elif key == b'\x1b':  # Esc key
                TTS("Restart cancelled.")
                return "Restart cancelled."
        time.sleep(0.1)

    # Auto-restart after 5 seconds
    TTS("No input received. Restarting automatically.")
    subprocess.run(["shutdown", "/r", "/t", "0"])
    return "Auto-restarting the laptop."