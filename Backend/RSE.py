import json
import re
import requests
import logging
from dotenv import load_dotenv
from os import environ
from ddgs import DDGS
from groq import Groq
import google.genai as genai

# Import the AI Client Manager
from .AIClientManager import get_ai_response

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini API (fallback)
GEMINI_API_KEY = environ.get('GeminiAPI', environ.get('CohereAPI', ''))

# Keep legacy client for backward compatibility (but use AI manager primarily)
client = Groq(api_key=environ['GroqAPI'])
default_messages = [{'role': 'user', 'content': f"Hello {environ['AssistantName']}, How are you?"}, 
                    {'role': 'assistant', 'content': f"Welcome Back {environ['NickName']}, I am doing well. How may I assist you?"}]

# Load or create chat log
try:
    with open('ChatLog.json', 'r') as f:
        messages = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    with open('ChatLog.json', 'w') as f:
        json.dump(default_messages, f, indent=4)
    messages = default_messages

def GoogleSearch(query: str) -> str:
    """Performs a search using DuckDuckGo for real-time information."""
    try:
        # Improve search terms for better results
        query_lower = query.lower()

        # Enhance search queries for better results
        if 'gold price' in query_lower or 'gold rate' in query_lower:
            search_query = "gold price today per gram INR live"
        elif 'usd to inr' in query_lower or 'dollar to rupee' in query_lower or 'usd inr' in query_lower:
            search_query = "USD to INR exchange rate today live"
        elif 'bitcoin' in query_lower or 'btc' in query_lower:
            search_query = "bitcoin price today USD live"
        elif 'cryptocurrency' in query_lower or 'crypto' in query_lower:
            search_query = query + " price today USD live"
        elif 'exchange rate' in query_lower:
            search_query = query + " today live"
        elif 'price' in query_lower or 'rate' in query_lower:
            search_query = query + " today live"
        else:
            search_query = query

        # Use DuckDuckGo search
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=5))

        if not results:
            return f"Sorry, I couldn't find information about '{query}'."

        # For price/currency queries, try to extract specific information
        if any(word in query_lower for word in ['price', 'rate', 'exchange', 'cost', 'value', 'gold', 'bitcoin', 'usd', 'inr']):
            return extract_price_info(results, query)
        else:
            # General search results
            answer = f"Search results for '{query}':\n\n"
            for i, result in enumerate(results, 1):
                title = result.get('title', 'No title')
                body = result.get('body', 'No description')

                answer += f"{i}. {title}\n"
                answer += f"   {body[:200]}{'...' if len(body) > 200 else ''}\n\n"

            return answer

    except Exception as e:
        return f"Sorry, I couldn't perform the search. Error: {str(e)}"

def extract_price_info(results, query):
    """Extract and format price information from search results."""
    query_lower = query.lower()
    extracted_info = []

    # Define patterns for different types of prices
    price_patterns = [
        # Gold prices: ₹1,43,383, ₹11,992.86, etc.
        r'₹\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        # Currency exchange rates: 89.577504 INR, ₹89.58
        r'\d{1,3}\.\d{1,6}\s*(?:INR|₹)',
        r'₹\d{1,3}\.\d{1,6}',
        # Bitcoin prices: $63154.37 USD
        r'\$\d{1,6}(?:\.\d{2})?\s*USD',
        # Exchange rate formats: 1 USD equals 89.577504 INR
        r'equals\s*₹?\d{1,3}(?:\.\d{1,6})?\s*(?:INR|₹)?',
        # Large numbers with commas: 1,43,383
        r'\d{1,3}(?:,\d{3})+(?:\.\d{2})?',
        # Decimal numbers: 89.58, 63154.37
        r'\d{2,6}\.\d{1,6}',
        # Gold purity formats: 22K Gold/gram 16, 11,992.86
        r'\d{2}K\s+Gold.*?₹?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
    ]

    for result in results:
        body = result.get('body', '')
        title = result.get('title', '')

        # Search in both title and body
        text_to_search = title + ' ' + body

        for pattern in price_patterns:
            matches = re.findall(pattern, text_to_search, re.IGNORECASE)
            if matches:
                for match in matches:
                    if match not in extracted_info:
                        extracted_info.append(match)

    if extracted_info:
        # Format the response based on query type
        if 'gold' in query_lower:
            response = f"Current gold prices found:\n"
            for info in extracted_info[:3]:  # Limit to top 3 results
                response += f"• {info}\n"
        elif 'usd' in query_lower or 'dollar' in query_lower:
            response = f"Current USD to INR exchange rate:\n"
            for info in extracted_info[:3]:
                response += f"• {info}\n"
        elif 'bitcoin' in query_lower or 'btc' in query_lower:
            response = f"Current Bitcoin price:\n"
            for info in extracted_info[:3]:
                response += f"• {info}\n"
        else:
            response = f"Price information found:\n"
            for info in extracted_info[:3]:
                response += f"• {info}\n"

        return response + "\nPlease verify with official sources for the most accurate current rates."
    else:
        # Fallback to showing general search results
        answer = f"I found some information about '{query}', but couldn't extract specific prices:\n\n"
        for i, result in enumerate(results[:3], 1):
            title = result.get('title', 'No title')
            body = result.get('body', 'No description')
            answer += f"{i}. {title}\n   {body[:150]}{'...' if len(body) > 150 else ''}\n\n"

        return answer

def AnswerModifier(answer: str) -> str:
    """Cleans up the AI's answer, removing unnecessary line breaks and content."""
    lines = answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def RealTimeChatBotAI(prompt: str) -> str:
    """Processes the user query, performs a real-time search, and returns the chatbot's response."""
    global messages
    
    # Load messages (redundancy removed)
    try:
        with open('ChatLog.json', 'r') as f:
            messages = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        messages = default_messages
    
    # Add Google Search results to SystemChat
    search_results = GoogleSearch(prompt)
    system_message = {'role': 'system', 'content': search_results}
    system_chat = [{'role': 'system', 'content': f"Hello, I am {environ['NickName']}, You are a very accurate and advanced AI chatbot named {environ['AssistantName']} which has real-time up-to-date information from the internet.\n*** Just answer the question from the provided data in a professional way. ***"}]
    system_chat.append(system_message)

    # Prepare messages for AI client manager
    all_messages = system_chat + messages

    # Use AI Client Manager with automatic fallback
    try:
        answer = get_ai_response(
            messages=all_messages,
            model='llama-3.3-70b-versatile',
            temperature=0.3,
            max_tokens=2048,
            stream=True
        )

        # Clean up the response
        answer = answer.strip().replace('</s>', '')
        answer = answer[0:answer.find('[')] if '[' in answer else answer

        return AnswerModifier(answer)

    except Exception as e:
        logger.error(f"All AI services failed in RealTimeChatBotAI: {e}")
        return f"I'm sorry, all AI services are currently unavailable. Please try again later."

if __name__ == '__main__':
    while True:
        prompt = input("Enter your query: ")
        print(RealTimeChatBotAI(prompt))
