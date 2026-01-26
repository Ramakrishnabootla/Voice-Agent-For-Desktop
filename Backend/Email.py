#!/usr/bin/env python3
"""
Email Module for JARVIS
Handles email composition and sending with voice and text input
"""

import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import eel
from Backend.TTS import TTS

# Load environment variables
load_dotenv()

# Global variables for email composition
email_composition_state = {
    'active': False,
    'receiver_email': None,
    'subject': None,
    'body': None,
    'step': 0  # 0: waiting for receiver, 1: waiting for subject, 2: waiting for body, 3: sending
}

# Voice input buffer for email composition
voice_input_buffer = None

def print_slow_and_speak(text: str) -> None:
    """Provides audio feedback using existing TTS system."""
    print(text)
    TTS(text)

def get_voice_input(prompt: str) -> str:
    """
    Gets voice input using existing voice recognition system.
    Waits for input from the web interface.
    """
    global voice_input_buffer
    
    print_slow_and_speak(prompt)
    voice_input_buffer = None
    
    # Wait for voice input (with timeout)
    start_time = time.time()
    while voice_input_buffer is None and time.time() - start_time < 10:
        eel.sleep(0.1)  # Small delay to prevent busy waiting
    
    return voice_input_buffer if voice_input_buffer else "No voice input received"

def set_receiver_email(email: str) -> str:
    """Sets the receiver email from web interface."""
    global email_composition_state

    if email_composition_state['active'] and email_composition_state['step'] == 0:
        email_composition_state['receiver_email'] = email
        email_composition_state['step'] = 1
        return "Email address received. Please say the subject."
    return "Not waiting for email address."

def set_email_subject(subject: str) -> str:
    """Sets the email subject from voice input."""
    global email_composition_state

    if email_composition_state['active'] and email_composition_state['step'] == 1:
        email_composition_state['subject'] = subject
        email_composition_state['step'] = 2
        return "Subject received. Please say the email body."
    return "Not waiting for subject."

def set_email_body(body: str) -> str:
    """Sets the email body from voice input."""
    global email_composition_state

    if email_composition_state['active'] and email_composition_state['step'] == 2:
        email_composition_state['body'] = body
        email_composition_state['step'] = 3
        return "Body received. Sending email..."
    return "Not waiting for body."

def send_email() -> str:
    """
    Main email sending function with voice and text input integration.
    """
    global email_composition_state

    try:
        # Get credentials
        EMAIL = os.getenv("EMAIL")
        PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

        if not EMAIL or not PASSWORD:
            error_msg = "Email credentials not found in environment variables."
            print_slow_and_speak(error_msg)
            return error_msg

        # Initialize email composition state
        email_composition_state = {
            'active': True,
            'receiver_email': None,
            'subject': None,
            'body': None,
            'step': 0
        }

        # Step 1: Get receiver email via web interface
        print_slow_and_speak("Please enter the receiver's email in the text box on the web interface")
        
        # Show email input section on web interface
        eel.showEmailInput()
        
        # Wait for receiver email (with timeout)
        start_time = time.time()
        while email_composition_state['step'] == 0 and time.time() - start_time < 30:
            eel.sleep(0.1)  # Small delay to prevent busy waiting

        if email_composition_state['step'] == 0:
            error_msg = "Timeout waiting for receiver email."
            print_slow_and_speak(error_msg)
            email_composition_state['active'] = False
            return error_msg

        # Step 2: Get subject via voice input
        subject = get_voice_input("Please say the subject")
        if subject:
            set_email_subject(subject)
        else:
            set_email_subject("No Subject")

        # Step 3: Get body via voice input
        body = get_voice_input("Please say the body")
        if body:
            set_email_body(body)
        else:
            set_email_body("No Body")

        # Step 4: Send the email
        receiver_email = email_composition_state['receiver_email']
        subject = email_composition_state['subject']
        body = email_composition_state['body']

        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL, receiver_email, text)
        server.quit()

        success_msg = f"Email sent successfully to {receiver_email}"
        print_slow_and_speak(success_msg)

        # Reset state
        email_composition_state['active'] = False
        return success_msg

    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print_slow_and_speak(error_msg)
        email_composition_state['active'] = False
        return error_msg

def process_email_voice_input(transcription):
    """Processes voice input during email composition."""
    global email_composition_state, voice_input_buffer
    
    if not email_composition_state['active']:
        return False
    
    # Clean the transcription
    transcription = transcription.strip().lower()
    voice_input_buffer = transcription
    
    # Process based on current step
    if email_composition_state['step'] == 1:  # Waiting for subject
        set_email_subject(transcription)
        return True
    elif email_composition_state['step'] == 2:  # Waiting for body
        set_email_body(transcription)
        return True
    
    return False

if __name__ == '__main__':
    # Test the email functionality
    print("Email module loaded successfully")