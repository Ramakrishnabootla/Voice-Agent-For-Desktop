import subprocess
import time
import msvcrt
from Backend.TTS import print_slow_and_speak, TTS
import psutil
import imaplib
import email
import os
from dotenv import load_dotenv
import wikipedia
import tkinter as tk
from tkinter import scrolledtext, messagebox
import geopy.geocoders
from geopy.distance import great_circle
import geocoder
import requests
import threading

# Load environment variables
load_dotenv()

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

def read_recent_emails():
    """Reads and speaks recent emails from Gmail inbox."""
    try:
        # Get credentials from environment
        email_user = os.getenv('EMAIL')
        email_password = os.getenv('EMAIL_APP_PASSWORD')

        if not email_user or not email_password:
            error_msg = "Email credentials not found in environment variables."
            print_slow_and_speak(error_msg)
            return error_msg

        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_user, email_password)
        mail.select('inbox')

        # Search for recent emails (last 2)
        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()

        if not email_ids:
            message = "No emails found in your inbox."
            print_slow_and_speak(message)
            return message

        # Get the last 2 emails
        recent_ids = email_ids[-2:] if len(email_ids) >= 2 else email_ids

        emails_info = []
        for email_id in reversed(recent_ids):  # Most recent first
            # Fetch the email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            raw_email = msg_data[0][1]

            # Parse the email
            email_message = email.message_from_bytes(raw_email)

            # Extract sender, subject, and body preview
            sender = email_message['From']
            subject = email_message['Subject'] or 'No Subject'

            # Get body preview
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

            # Clean up body (remove newlines, limit length)
            body_preview = body.replace('\n', ' ').replace('\r', ' ').strip()
            if len(body_preview) > 100:
                body_preview = body_preview[:100] + "..."

            email_info = f"From: {sender}\nSubject: {subject}\nPreview: {body_preview}"
            emails_info.append(email_info)

        # Close the connection
        mail.logout()

        # Format and speak the results
        if emails_info:
            full_message = f"I found {len(emails_info)} recent email(s):\n\n"
            for i, info in enumerate(emails_info, 1):
                full_message += f"Email {i}:\n{info}\n\n"

            print_slow_and_speak(full_message)
            return full_message
        else:
            message = "No emails could be read."
            print_slow_and_speak(message)
            return message

    except Exception as e:
        error_msg = f"Error reading emails: {str(e)}"
        print_slow_and_speak(error_msg)
        return error_msg

def create_gui():
    """Create a GUI for Wikipedia search"""
    try:
        # Create main window
        root = tk.Tk()
        root.title("JARVIS - Wikipedia Search")
        root.geometry("600x500")
        root.configure(bg='#2c3e50')

        # Title label
        title_label = tk.Label(root, text="Wikipedia Search", font=("Arial", 16, "bold"), bg='#2c3e50', fg='white')
        title_label.pack(pady=10)

        # Input frame
        input_frame = tk.Frame(root, bg='#2c3e50')
        input_frame.pack(pady=10)

        # Topic input label
        topic_label = tk.Label(input_frame, text="Enter topic to search:", font=("Arial", 12), bg='#2c3e50', fg='white')
        topic_label.pack(side=tk.LEFT, padx=5)

        # Topic input entry
        topic_entry = tk.Entry(input_frame, width=30, font=("Arial", 12))
        topic_entry.pack(side=tk.LEFT, padx=5)

        # Search button
        def search_wikipedia():
            topic = topic_entry.get().strip()
            if not topic:
                messagebox.showwarning("Warning", "Please enter a topic to search.")
                return

            try:
                # Search Wikipedia
                summary = wikipedia.summary(topic, sentences=2)

                # Clean up the summary (remove references)
                import re
                summary = re.sub(r'\[.*?\]', '', summary)

                # Display in text box
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"Topic: {topic}\n\n{summary}")

                # Speak the summary
                threading.Thread(target=lambda: print_slow_and_speak(f"According to Wikipedia, {summary}")).start()

            except wikipedia.exceptions.DisambiguationError as e:
                options = e.options[:5]  # Show first 5 options
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"Multiple results found for '{topic}'. Please be more specific.\n\nSuggestions:\n" + "\n".join(options))
                print_slow_and_speak("Multiple results found. Please be more specific.")
            except wikipedia.exceptions.PageError:
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"Sorry, no Wikipedia page found for '{topic}'.")
                print_slow_and_speak("Sorry, no Wikipedia page found for that topic.")
            except Exception as e:
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"Error searching Wikipedia: {str(e)}")
                print_slow_and_speak("Error occurred while searching.")

        search_button = tk.Button(input_frame, text="Search", command=search_wikipedia, font=("Arial", 12), bg='#3498db', fg='white')
        search_button.pack(side=tk.LEFT, padx=5)

        # Result text area
        result_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15, font=("Arial", 10))
        result_text.pack(pady=10, padx=20)

        # Close button
        close_button = tk.Button(root, text="Close", command=root.destroy, font=("Arial", 12), bg='#e74c3c', fg='white')
        close_button.pack(pady=10)

        # Set focus to entry
        topic_entry.focus()

        # Start the GUI
        root.mainloop()

    except Exception as e:
        print_slow_and_speak(f"Error creating GUI: {str(e)}")

def get_location_info():
    """Get current location and calculate distance to destination"""
    try:
        print_slow_and_speak("Please tell me your destination city or address.")

        # For now, we'll use a simple input. In a full implementation, this would use speech recognition
        destination = input("Enter destination: ").strip()

        if not destination:
            print_slow_and_speak("No destination provided.")
            return

        # Initialize geolocator
        geolocator = geopy.geocoders.Nominatim(user_agent="jarvis_ai")

        # Get current location using IP
        current_location = geocoder.ip('me')
        if not current_location.ok:
            print_slow_and_speak("Unable to determine your current location.")
            return

        current_lat, current_lng = current_location.latlng
        current_address = current_location.address

        # Geocode destination
        destination_location = geolocator.geocode(destination)
        if not destination_location:
            print_slow_and_speak(f"Could not find location for '{destination}'.")
            return

        dest_lat, dest_lng = destination_location.latitude, destination_location.longitude
        dest_address = destination_location.address

        # Calculate distance
        distance = great_circle((current_lat, current_lng), (dest_lat, dest_lng)).kilometers

        # Format result
        result = f"Your current location is {current_address}.\n"
        result += f"Distance to {dest_address} is approximately {distance:.1f} kilometers."

        print_slow_and_speak(result)
        return result

    except Exception as e:
        error_msg = f"Error getting location information: {str(e)}"
        print_slow_and_speak(error_msg)
        return error_msg

def get_weather():
    """Get weather information for current location or specified city"""
    try:
        # Get API key from environment
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if not api_key:
            print_slow_and_speak("Weather API key not found. Please add OPENWEATHER_API_KEY to your .env file.")
            return

        # Get current location
        current_location = geocoder.ip('me')
        if not current_location.ok:
            default_city = "London"  # fallback
        else:
            default_city = current_location.city

        print_slow_and_speak(f"Current location detected as {default_city}. Press Enter to use this location, or type a different city name.")

        # For now, use input. In full implementation, would use speech recognition
        user_input = input("Enter city (or press Enter for current location): ").strip()
        city = user_input if user_input else default_city

        # API call
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            print_slow_and_speak(f"Error getting weather data: {data.get('message', 'Unknown error')}")
            return

        # Extract weather info
        weather_desc = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']

        # Format result
        result = f"Weather in {city}: {weather_desc.capitalize()}.\n"
        result += f"Temperature: {temp}°C (feels like {feels_like}°C).\n"
        result += f"Humidity: {humidity}%, Wind speed: {wind_speed} m/s."

        print_slow_and_speak(result)
        return result

    except Exception as e:
        error_msg = f"Error getting weather information: {str(e)}"
        print_slow_and_speak(error_msg)
        return error_msg