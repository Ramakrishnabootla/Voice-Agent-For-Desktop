import os
import json
import threading
import asyncio
import base64
from time import sleep
from random import choice
import pyautogui
import mtranslate as mt
import eel
from dotenv import load_dotenv, set_key
from threading import Lock

# Import backend modules
from Backend.Extra import AnswerModifier, QueryModifier, LoadMessages, GuiMessagesConverter
from Backend.Automation import run_automation as Automation
from Backend.RSE import RealTimeChatBotAI, GoogleSearch
from Backend.Chatbot import ChatBotAI
from Backend.AutoModel import Model
from Backend.ChatGpt import ChatBotAI as ChatGptAI
from Backend.TTS import TTS

# Load environment variables
load_dotenv()

print("Environment loaded, initializing...")

# Global variables
state = 'Available...'
messages = LoadMessages()
WEBCAM = False
js_messageslist = []
working: list[threading.Thread] = []
InputLanguage = os.environ['InputLanguage']
Assistantname = os.environ['AssistantName']
Username = os.environ['NickName']
lock = Lock()

def UniversalTranslator(Text: str) -> str:
    """Translates text to English."""
    return mt.translate(Text, 'en', 'auto').capitalize()

def MainExecution(Query: str):
    """Main execution function for handling user queries."""
    global WEBCAM, state
    print(f"Processing query: {Query}")
    Query = UniversalTranslator(Query) if 'en' not in InputLanguage.lower() else Query.capitalize()
    Query = QueryModifier(Query)
    print(f"Modified query: {Query}")

    if state != 'Available...':
        print("State not available, returning")
        return
    state = 'Thinking...'
    print("Calling Model...")
    Decision = Model(Query)
    print(f"Decision: {Decision}")

    try:
        if 'general' in Decision or 'realtime' in Decision:
            print("General or realtime query")
            if Decision[0] == 'general':
                print("General query")
                if WEBCAM:
                    python_call_to_capture()
                    sleep(0.5)
                    Answer = AnswerModifier(ChatBotAI(Query))  # Changed to use Groq instead of Tune Studio
                else:
                    Answer = AnswerModifier(ChatBotAI(Query))
                print(f"Answer: {Answer}")
                state = 'Answering...'
                TTS(Answer)
                print("TTS called")
                messages.append({'role': 'assistant', 'content': Answer})
                with open('ChatLog.json', 'w') as f:
                    json.dump(messages, f, indent=4)
            else:
                print("Realtime query")
                state = 'Searching...'
                Answer = AnswerModifier(RealTimeChatBotAI(Query))
                print(f"Realtime Answer: {Answer}")
                state = 'Answering...'
                TTS(Answer)
                print("Realtime TTS called")
                messages.append({'role': 'assistant', 'content': Answer})
                with open('ChatLog.json', 'w') as f:
                    json.dump(messages, f, indent=4)
        elif 'open webcam' in Decision:
            print("Opening webcam")
            python_call_to_start_video()
            print('Video Started')
            WEBCAM = True
        elif 'close webcam' in Decision:
            print("Closing webcam")
            print('Video Stopped')
            python_call_to_stop_video()
            WEBCAM = False
        elif 'google search' in Decision:
            print("Google search query")
            # Extract the search topic from the decision
            if 'google search (' in Decision and ')' in Decision:
                topic = Decision.split('google search (')[1].split(')')[0]
            else:
                topic = Query  # fallback to original query
            print(f"Searching for: {topic}")
            state = 'Searching...'
            search_results = GoogleSearch(topic)
            Answer = AnswerModifier(search_results)
            print(f"Search Answer: {Answer}")
            state = 'Answering...'
            TTS(Answer)
            print("Search TTS called")
            messages.append({'role': 'assistant', 'content': Answer})
            with open('ChatLog.json', 'w') as f:
                json.dump(messages, f, indent=4)
        else:
            print("Automation query")
            state = 'Automation...'
            response = asyncio.run(Automation(Decision))
            print(f"Automation response: {response}")
            state = 'Answering...'
            messages.append({'role': 'assistant', 'content': response})
            with open('ChatLog.json', 'w') as f:
                json.dump(messages, f, indent=4)
            TTS(response)
            print("Automation TTS called")
    finally:
        state = 'Listening...'
        print("State set to Listening")

@eel.expose
def js_messages():
    """Fetches new messages to update the GUI."""
    global messages, js_messageslist
    with lock:
        messages = LoadMessages()
    if js_messageslist != messages:
        new_messages = GuiMessagesConverter(messages[len(js_messageslist):])
        js_messageslist = messages
        return new_messages
    return []

@eel.expose
def js_state(stat=None):
    """Updates or retrieves the current state."""
    global state
    if stat:
        state = stat
    return state

@eel.expose
def js_mic(transcription):
    """Handles microphone input."""
    print(transcription)
    global state
    state = 'Available...'  # Reset state to allow processing
    if not working or not working[0].is_alive():
        work = threading.Thread(target=MainExecution, args=(transcription,), daemon=True)
        work.start()
        working.append(work)

@eel.expose
def python_call_to_start_video():
    """Starts the video capture."""
    eel.startVideo()

@eel.expose
def python_call_to_stop_video():
    """Stops the video capture."""
    eel.stopVideo()

@eel.expose
def python_call_to_capture():
    """Captures an image from the video."""
    eel.capture()

@eel.expose
def js_page(cpage=None):
    """Navigates to the specified page."""
    if cpage == 'home':
        eel.openHome()
    elif cpage == 'settings':
        eel.openSettings()

@eel.expose
def js_setvalues(GeminiApi, HuggingFaceApi, GroqApi, AssistantName, Username):
    """Sets API keys and user preferences."""
    print(f'GeminiApi = {GeminiApi!r} HuggingFaceApi = {HuggingFaceApi!r} GroqApi = {GroqApi!r} AssistantName = {AssistantName!r} Username = {Username!r}')
    if GeminiApi:
        set_key('.env', 'CohereAPI', GeminiApi)
    if HuggingFaceApi:
        set_key('.env', 'HuggingFaceAPI', HuggingFaceApi)
    if GroqApi:
        set_key('.env', 'GroqAPI', GroqApi)
    if AssistantName:
        set_key('.env', 'AssistantName', AssistantName)
    if Username:
        set_key('.env', 'NickName', Username)

@eel.expose
def setup():
    """Sets up the GUI window."""
    pyautogui.hotkey('win', 'up')
    # Welcome message
    TTS("Welcome to JARVIS. How can I help you?")

@eel.expose
def js_language():
    """Returns the input language."""
    return InputLanguage

@eel.expose
def js_assistantname():
    """Returns the assistant's name."""
    return Assistantname

@eel.expose
def js_capture(image_data):
    """Saves the captured image."""
    image_bytes = base64.b64decode(image_data.split(',')[1])
    with open('capture.png', 'wb') as f:
        f.write(image_bytes)

# Initialize Eel and start the application
eel.init('web')
print("Eel initialized, starting server...")
print("Starting Eel server...")
eel.start('spider.html', port=44449)
