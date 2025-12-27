# Import required libraries and modules
from groq import Groq
from json import load, dump
import datetime
import logging
from dotenv import load_dotenv
from os import environ

# Import the AI Client Manager
from .AIClientManager import get_ai_response

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize the Groq API client
client = Groq(api_key=environ['GroqAPI'])

# Define system message and system chat history
System = (
    f"Hello, I am {environ['NickName']}, you are a very accurate and advanced AI chatbot named {environ['AssistantName']} "
    f"which also has real-time up-to-date information from the internet.\n"
    "*** Do not tell time unless I ask, do not talk too much, just answer the question. ***\n"
    "*** Provide answers in a professional way. Make sure to use proper grammar with full stops, commas, and question marks. ***\n"
    "*** Reply in the same language as the question: Hindi in Hindi, English in English. ***\n"
    "*** Do not mention your training data or provide notes in the output. Just answer the question. ***\n"
    "*** Always base your responses on accurate knowledge. Do not hallucinate or make up information. ***"
)

SystemChatBot = [
    {'role': 'system', 'content': System},
    {'role': 'user', 'content': 'Hi'},
    {'role': 'assistant', 'content': 'Hello, how can I help you?'}
]

# Default message when there is no existing chat log
DefaultMessage = [
    {'role': 'user', 'content': f"Hello {environ['AssistantName']}, how are you?"},
    {'role': 'assistant', 'content': f"Welcome back {environ['NickName']}, I am doing well. How may I assist you?"}
]

# Load chat history from ChatLog.json or initialize it with a default message if not available
try:
    with open('ChatLog.json', 'r') as f:
        messages = load(f)
except FileNotFoundError:
    with open('ChatLog.json', 'w') as f:
        dump(DefaultMessage, f)

def Information():
    """
    Provides real-time information including the current day, date, and time.
    """
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime('%A')
    date = current_date_time.strftime('%d')
    month = current_date_time.strftime('%B')
    year = current_date_time.strftime('%Y')
    hour = current_date_time.strftime('%H')
    minute = current_date_time.strftime('%M')
    second = current_date_time.strftime('%S')

    data = (
        f"Use this real-time information if needed:\n"
        f"Day: {day}\n"
        f"Date: {date}\n"
        f"Month: {month}\n"
        f"Year: {year}\n"
        f"Time: {hour} hours :{minute} minutes :{second} seconds.\n"
    )
    return data

def AnswerModifier(answer):
    """
    Modifies the answer by removing any empty lines.
    """
    lines = answer.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)

def ChatBotAI(prompt):
    """
    Handles the chatbot's logic using AI Client Manager with automatic fallback.
    """
    try:
        # Load existing chat log
        with open('ChatLog.json', 'r') as f:
            messages = load(f)

        # Prepare messages for AI client manager
        system_info = {'role': 'system', 'content': Information()}
        all_messages = SystemChatBot + [system_info] + messages

        # Use AI Client Manager with automatic fallback
        answer = get_ai_response(
            messages=all_messages,
            model='llama-3.3-70b-versatile',
            temperature=0.3,
            max_tokens=2048,
            stream=True
        )

        # Return the modified answer
        return AnswerModifier(answer)

    except Exception as e:
        # Log the error and provide fallback response
        logger.error(f"All AI services failed in ChatBotAI: {e}")
        return "I'm sorry, all AI services are currently unavailable. Please try again later."

if __name__ == '__main__':
    while True:
        user_input = input('Enter Your Question: ')
        print(ChatBotAI(user_input))
