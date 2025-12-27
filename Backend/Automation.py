import requests
import random
import asyncio
import platform
import subprocess
import keyboard
from pywhatkit import search, playonyt
from AppOpener import close, open as appopen
from webbrowser import open as webopen
from bs4 import BeautifulSoup
from PIL import Image
import os
from dotenv import load_dotenv
from random import randint
from pyautogui import hotkey

# Import backend modules
from .RSE import GoogleSearch
from .AIClientManager import get_ai_response

load_dotenv()

# Constants
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
PROFESSIONAL_RESPONSES = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need—don't hesitate to ask.",
    # Add more responses as needed...
]

# App aliases for better matching
app_aliases = {
    "excel": "excel",
    "word": "winword",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "notepad": "notepad",
    "calculator": "calc",
    "paint": "mspaint",
    "cmd": "cmd",
    "powershell": "powershell",
    "chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "vlc": "vlc",
    "spotify": "spotify",
    "vs code": "code",
    "v s code": "code",
    "wordpad": "wordpad",
    "snippingtool": "snippingtool",
    "magnifier": "magnifier",
    "onenote": "onenote",
    "skype": "skype",
    "zoom": "zoom",
    "photoshop": "photoshop",
    "illustrator": "illustrator",
    "discord": "discord",
    "steam": "steam",
    # Add more as needed
}

# Track opened websites
opened_websites = []

# Load API keys from environment
HUGGINGFACE_API_KEY = os.getenv('HuggingFaceAPI')
GROQ_API_KEY = os.getenv('GroqAPI')

def open_notepad(file):
    editor = 'notepad.exe' if os.name == 'nt' else 'open'
    subprocess.Popen([editor, file])

# Function for AI-powered content generation
def content_writer_ai(prompt):
    messages = [{'role': 'user', 'content': prompt}]
    system_chat_bot = [{'role': 'system', 'content': "You're a content writer. You create letters, codes, essays, etc."}]

    # Use AI Client Manager with automatic fallback
    answer = get_ai_response(
        messages=system_chat_bot + messages,
        model='mixtral-8x7b-32768',
        max_tokens=2048,
        temperature=0.7,
        top_p=1,
        stream=True
    )

    return answer.replace('</s>', '')

# Function for generating images using Hugging Face API
async def query_image_generation(payload):
    api_url = 'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1'
    headers = {'Authorization': f"Bearer {HUGGINGFACE_API_KEY}"}
    response = await asyncio.to_thread(requests.post, api_url, headers=headers, json=payload)
    return response.content

async def generate_images(prompt):
    tasks = [
        asyncio.create_task(query_image_generation({'inputs': f'{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution, seed={randint(0, 1000000)}'}))
        for _ in range(4)
    ]
    image_bytes_list = await asyncio.gather(*tasks)
    for i, image_bytes in enumerate(image_bytes_list):
        with open(f'Images/image{i + 1}.jpg', 'wb') as f:
            f.write(image_bytes)

# Function to open and display images
class ShowImage:
    def __init__(self, image_list):
        self.image_list = image_list

    def open_image(self, index):
        try:
            img = Image.open(f'Images/{self.image_list[index]}')
            img.show()
        except Exception:
            print(f'Error: Unable to open image at {index}')

# Unified function for system commands
def system_command(command):
    def run_powershell(cmd):
        try:
            print(f"Running PowerShell command: {cmd}")
            result = subprocess.run(['powershell', '-Command', cmd], capture_output=True, text=True, check=True, shell=True)
            print(f"PowerShell command succeeded: {cmd}")
            print(f"Output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"PowerShell command failed: {cmd}")
            print(f"Error: {e}")
            print(f"Return code: {e.returncode}")
            print(f"Output: {e.stdout}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error running PowerShell: {e}")
            return False

    commands = {
        'mute': lambda: keyboard.press_and_release('volume mute'),
        'unmute': lambda: keyboard.press_and_release('volume mute'),
        'volume up': lambda: keyboard.press_and_release('volume up'),
        'volume down': lambda: keyboard.press_and_release('volume down'),
        'volume increase': lambda: keyboard.press_and_release('volume up'),
        'volume decrease': lambda: keyboard.press_and_release('volume down'),
        'minimise all': lambda: hotkey('win', 'd'),
        'show desktop': lambda: hotkey('win', 'd'),
        'lock screen': lambda: os.system('rundll32.exe user32.dll,LockWorkStation'),
        'task manager': lambda: hotkey('ctrl', 'shift', 'esc'),
        'file explorer': lambda: hotkey('win', 'e'),
        'run': lambda: hotkey('win', 'r'),
        'shutdown': lambda: os.system('shutdown /s /t 1' if platform.system() == 'Windows' else 'poweroff'),
        'restart': lambda: os.system('shutdown /r /t 1' if platform.system() == 'Windows' else 'reboot'),
        'sleep': lambda: os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0' if platform.system() == 'Windows' else 'systemctl suspend'),
        'hibernate': lambda: os.system('shutdown /h' if platform.system() == 'Windows' else 'systemctl hibernate'),
        'wifi on': lambda: run_powershell("Set-NetAdapter -Name (Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*' -or $_.Name -like '*Wireless*'} | Select-Object -First 1).Name -Enabled $true"),
        'wifi off': lambda: run_powershell("Set-NetAdapter -Name (Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*' -or $_.Name -like '*Wireless*'} | Select-Object -First 1).Name -Enabled $false"),
        'wi-fi on': lambda: run_powershell("Set-NetAdapter -Name (Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*' -or $_.Name -like '*Wireless*'} | Select-Object -First 1).Name -Enabled $true"),
        'wi-fi off': lambda: run_powershell("Set-NetAdapter -Name (Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*' -or $_.Name -like '*Wireless*'} | Select-Object -First 1).Name -Enabled $false"),
        'bluetooth on': lambda: run_powershell("Get-PnpDevice | Where-Object {$_.Class -eq 'Bluetooth'} | Enable-PnpDevice -Confirm:$false"),
        'bluetooth off': lambda: run_powershell("Get-PnpDevice | Where-Object {$_.Class -eq 'Bluetooth'} | Disable-PnpDevice -Confirm:$false"),
        'toggle bluetooth': lambda: run_powershell("Get-PnpDevice | Where-Object {$_.Class -eq 'Bluetooth'} | ForEach-Object { if ($_.Status -eq 'OK') { Disable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false } else { Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false } }"),
        'toggle wifi': lambda: run_powershell("$adapter = Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*' -or $_.Name -like '*Wireless*'} | Select-Object -First 1; if ($adapter.Status -eq 'Up') { Set-NetAdapter -Name $adapter.Name -Enabled $false } else { Set-NetAdapter -Name $adapter.Name -Enabled $true }"),
        'toggle wi-fi': lambda: run_powershell("$adapter = Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*' -or $_.Name -like '*Wireless*'} | Select-Object -First 1; if ($adapter.Status -eq 'Up') { Set-NetAdapter -Name $adapter.Name -Enabled $false } else { Set-NetAdapter -Name $adapter.Name -Enabled $true }"),
    }

    # Case-insensitive command matching with variations
    command_lower = command.lower().strip()
    
    # Handle common variations
    command_variations = {
        'turn off wi-fi': 'wi-fi off',
        'turn on wi-fi': 'wi-fi on',
        'turn off wifi': 'wifi off',
        'turn on wifi': 'wifi on',
        'turn off bluetooth': 'bluetooth off',
        'turn on bluetooth': 'bluetooth on',
    }
    
    if command_lower in command_variations:
        command_lower = command_variations[command_lower]
    
    for cmd_key in commands:
        if cmd_key.lower() == command_lower:
            print(f"Executing system command: {cmd_key}")
            return commands[cmd_key]()
    
    print(f"Command '{command}' not found in system commands")
    return False

# Function to handle app opening
def open_app(app_name):
    # Use alias if available
    actual_name = app_aliases.get(app_name.lower(), app_name)
    print(f"Attempting to open app: {actual_name}")
    try:
        # Try AppOpener first
        print("Trying AppOpener...")
        subprocess.run(['python', '-c', f'from AppOpener import open as appopen; appopen("{actual_name}", match_closest=True, output=False, throw_error=True)'], capture_output=True, check=True)
        print("AppOpener succeeded")
        return True
    except Exception as e:
        print(f"AppOpener failed: {e}")
        try:
            # Fallback to Windows start command
            print(f"Trying start command for {actual_name}")
            subprocess.run(['powershell', '-Command', f'Start-Process {actual_name}'], check=True)
            print("Start command succeeded")
            return True
        except Exception as e2:
            print(f"Start command failed: {e2}")
            return False

# Function to handle app closing
def close_app(app_name):
    # Use alias if available
    actual_name = app_aliases.get(app_name.lower(), app_name)
    print(f"Attempting to close app: {actual_name}")
    try:
        # Try AppOpener first
        print("Trying AppOpener close...")
        subprocess.run(['python', '-c', f'from AppOpener import close; close("{actual_name}", match_closest=True, output=False, throw_error=True)'], capture_output=True, check=True)
        print("AppOpener close succeeded")
        return True
    except Exception as e:
        print(f"AppOpener close failed: {e}")
        try:
            # Fallback to taskkill
            print(f"Trying taskkill for {actual_name}.exe")
            subprocess.run(['taskkill', '/im', f'{actual_name}.exe', '/f'], check=True)
            print("Taskkill succeeded")
            return True
        except Exception as e2:
            print(f"Taskkill failed: {e2}")
            return False

# Function to play YouTube video
def play_youtube(query):
    playonyt(query)
    return True

# Asynchronous task executor
async def execute_commands(commands):
    results = []
    for command in commands:
        if command.startswith('open '):
            app_name = command.removeprefix('open ')
            print(f"Trying to open app: {app_name}")
            if open_app(app_name):
                results.append(f"Opened {app_name}")
            else:
                print(f"App '{app_name}' not found, trying as website: https://{app_name}.com")
                # If not an app, try opening as website
                webopen(f'https://{app_name}.com')
                opened_websites.append(app_name.lower())
                results.append(f"Opened {app_name} website")
        elif command.startswith('close '):
            app_name = command.removeprefix('close ')
            print(f"Trying to close app: {app_name}")
            if app_name.lower() in opened_websites:
                opened_websites.remove(app_name.lower())
                results.append(f"Closed {app_name} website (please close the browser tab manually)")
            elif close_app(app_name):
                results.append(f"Closed {app_name}")
            else:
                results.append(f"Could not close {app_name}")
        elif command.startswith('play '):
            query = command.removeprefix('play ')
            play_youtube(query)
            results.append(f"Playing {query} on YouTube")
        elif command.startswith('system '):
            cmd = command.removeprefix('system ').strip('() ').strip()
            if system_command(cmd):
                results.append(f"Executed system command: {cmd}")
            else:
                results.append(f"Failed to execute: {cmd}")
        elif command.startswith('google search '):
            query = command.removeprefix('google search ')
            print(f"Performing Google search for: {query}")
            search_results = GoogleSearch(query)
            print(f"Search completed, results length: {len(search_results)}")
            results.append(f"Searched for: {query}")
            # The search results will be handled by the main execution flow
        else:
            print(f'No function found for {command}')
            results.append(f"Unknown command: {command}")

    return results

# Function to run automation commands
async def run_automation(commands):
    results = await execute_commands(commands)

    # Create a concise response based on the actions performed
    if not results:
        return "No actions were performed."

    if len(results) == 1:
        response = f"{results[0]}. Anything else I can help you with?"
    else:
        # Multiple actions
        action_list = ", ".join(results[:-1]) + f" and {results[-1]}" if len(results) > 1 else results[0]
        response = f"Completed: {action_list}. Anything else I can help you with?"

    return response
