import os
from builtins import Exception
from builtins import int
import speech_recognition as sr
from gtts import gTTS
from playsound3 import playsound
import pandas as pd
import sounddevice as sd
from scipy.io.wavfile import write
import difflib
import requests
import configparser
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time


# Configuration
config = configparser.ConfigParser()
config.read("config.ini")
OPENROUTER_API_KEY = config.get("OpenRouter", "API_KEY", fallback=None)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"


class HerbalRemedyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Herbal Remedy Voice Assistant")
        self.root.geometry("700x500")
        self.root.configure(bg="#f0f8f0")
        
        # Create GUI elements
        self.create_widgets()
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        
        # Welcome message
        self.update_display("Welcome to Herbal Remedy Voice Assistant!", "system")
        self.update_display("Say 'help' for instructions or tell me a disease name.", "system")
        
        # Start listening in a separate thread
        threading.Thread(target=self.start_listening, daemon=True).start()
    
    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="🌿 Herbal Remedy Voice Assistant", 
                              font=("Arial", 16, "bold"), bg="#f0f8f0", fg="#2e7d32")
        title_label.pack(pady=10)
        
        # Display area
        self.display_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=80, height=20,
                                                     font=("Arial", 10), bg="#ffffff", fg="#333333")
        self.display_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.display_area.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = tk.Frame(self.root, bg="#f0f8f0")
        button_frame.pack(pady=10)
        
        # Help button
        help_btn = tk.Button(button_frame, text="Help", command=self.show_help,
                            bg="#4caf50", fg="white", font=("Arial", 10, "bold"))
        help_btn.pack(side=tk.LEFT, padx=5)
        
        # Listen button
        listen_btn = tk.Button(button_frame, text="Listen", command=self.manual_listen,
                              bg="#2196f3", fg="white", font=("Arial", 10, "bold"))
        listen_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        clear_btn = tk.Button(button_frame, text="Clear", command=self.clear_display,
                             bg="#ff9800", fg="white", font=("Arial", 10, "bold"))
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Exit button
        exit_btn = tk.Button(button_frame, text="Exit", command=self.root.quit,
                            bg="#f44336", fg="white", font=("Arial", 10, "bold"))
        exit_btn.pack(side=tk.LEFT, padx=5)
    
    def update_display(self, text, sender="user"):
        self.display_area.config(state=tk.NORMAL)
        if sender == "system":
            self.display_area.insert(tk.END, f"System: {text}\n", "system")
        elif sender == "assistant":
            self.display_area.insert(tk.END, f"Assistant: {text}\n", "assistant")
        else:
            self.display_area.insert(tk.END, f"You: {text}\n", "user")
        
        self.display_area.see(tk.END)
        self.display_area.config(state=tk.DISABLED)
    
    def clear_display(self):
        self.display_area.config(state=tk.NORMAL)
        self.display_area.delete(1.0, tk.END)
        self.display_area.config(state=tk.DISABLED)
        self.update_display("Display cleared. How can I help you?", "system")
    
    def show_help(self):
        help_text = """
HERBAL REMEDY VOICE ASSISTANT - HELP

How to use:
1. Click the 'Listen' button or say 'help' to begin
2. When prompted, speak clearly and name a disease or condition
3. The system will search for herbal remedies

Available commands:
- 'help': Show these instructions
- 'clear': Clear the conversation
- Name any disease or health condition

Examples of what to say:
- "I have a cold"
- "What helps with headaches?"
- "Herbal remedy for insomnia"

The system will search:
1. Local database of herbal remedies
2. Built-in common remedies
3. AI-powered suggestions (if API key is configured)
"""
        self.update_display(help_text, "system")
        self.speak("Here are instructions on how to use the herbal remedy assistant.")
    
    def manual_listen(self):
        threading.Thread(target=self.listen_and_process, daemon=True).start()
    
    def start_listening(self):
        time.sleep(2)  # Give the GUI time to initialize
        self.speak("Hello! Please tell me which disease you want herbal remedies for, or say help for instructions.")
    
    def listen_and_process(self):
        disease = self.recognize_speech()
        if disease:
            self.update_display(disease)
            self.process_disease(disease)
    
    def process_disease(self, disease):
        if "help" in disease.lower():
            self.show_help()
            return
        
        self.update_display("Searching for herbal remedies...", "system")
        
        # Search for remedies
        info = self.lookup_csv(disease)
        
        # Check fallback dictionary
        if not info and disease in herbal_fallback:
            r = herbal_fallback[disease]
            info = (
                f"Disease: {disease.capitalize()}\n"
                f"Herbal Remedy: {r['HerbName']}\n"
                f"Ingredients: {r['Ingredients']}\n"
                f"Preparation: {r['Preparation']}\n"
                f"Dosage: {r['Dosage']}"
            )
        
        # Try AI if still not found
        if not info:
            ai_info = self.ai_herbal_remedy(disease)
            if ai_info:
                info = ai_info
        
        # Final response
        if not info:
            info = f"Sorry, I could not find herbal remedies for {disease}."
        
        self.update_display(info, "assistant")
        self.speak(info)
    
    def speak(self, text):
        def _speak():
            try:
                tts = gTTS(text=text, lang='en')
                filename = "voice.mp3"
                tts.save(filename)
                playsound(filename)
                os.remove(filename)
            except Exception as e:
                self.root.after(0, lambda: self.update_display(f"Error in speech synthesis: {e}", "system"))
        
        threading.Thread(target=_speak, daemon=True).start()
    
    def recognize_speech(self):
        fs = 44100
        duration = 5
        
        # Show recording indicator in GUI
        self.root.after(0, lambda: self.update_display("🎤 Recording... Speak now!", "system"))
        
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        write("input.wav", fs, audio)
        
        self.root.after(0, lambda: self.update_display("Processing...", "system"))
        
        try:
            with sr.AudioFile("input.wav") as source:
                recorded_audio = self.recognizer.record(source)
            query = self.recognizer.recognize_google(recorded_audio)
            query = query.lower().strip()
            return query
        except Exception as e:
            self.root.after(0, lambda: self.update_display(f"Error recognizing speech: {e}", "system"))
            self.root.after(0, lambda: self.update_display("Sorry, I didn't catch that. Please try again.", "system"))
            return ""
    
    def lookup_csv(self, disease):
        try:
            df = pd.read_csv("herbs.csv")
            matches = difflib.get_close_matches(disease, df["Disease"].dropna().str.lower().tolist(), n=1, cutoff=0.4)
            if matches:
                record = df[df["Disease"].str.lower() == matches[0]].iloc[0]
                return (
                    f"Disease: {disease.capitalize()}\n"
                    f"Herbal Remedy: {record['HerbName']}\n"
                    f"Ingredients: {record['Ingredients']}\n"
                    f"Preparation: {record['Preparation']}\n"
                    f"Dosage: {record['Dosage']}"
                )
            return None
        except Exception as e:
            self.root.after(0, lambda: self.update_display(f"CSV lookup error: {e}", "system"))
            return None
    
    def ai_herbal_remedy(self, disease):
        if not OPENROUTER_API_KEY:
            self.root.after(0, lambda: self.update_display("OpenRouter API key not set. Skipping AI fetch.", "system"))
            return None

        prompt = f"Provide 2-3 herbal remedies for {disease} in structured format: HerbName, Ingredients, Preparation, Dosage."

        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                json={
                    'model': OPENROUTER_MODEL,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7,
                    'max_tokens': 400
                },
                timeout=20
            )
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                self.root.after(0, lambda: self.update_display(f"OpenRouter API error {response.status_code}: {response.text}", "system"))
                return None
        except Exception as e:
            self.root.after(0, lambda: self.update_display(f"AI fetch error: {e}", "system"))
            return None


# Fallback dictionary
herbal_fallback = {
    "cold": {
        "HerbName": "Ginger, Turmeric",
        "Ingredients": "Ginger, turmeric powder, milk",
        "Preparation": "Mix turmeric in warm milk or prepare ginger tea",
        "Dosage": "Once at night"
    },
    "cough": {
        "HerbName": "Tulsi, Licorice",
        "Ingredients": "Tulsi leaves, licorice root, honey",
        "Preparation": "Make herbal tea with ingredients",
        "Dosage": "2-3 times daily"
    },
    "headache": {
        "HerbName": "Peppermint, Lavender",
        "Ingredients": "Peppermint oil, lavender oil",
        "Preparation": "Apply diluted oil to temples or inhale aroma",
        "Dosage": "As needed"
    },
    "insomnia": {
        "HerbName": "Chamomile, Valerian",
        "Ingredients": "Chamomile flowers, valerian root",
        "Preparation": "Brew as tea before bedtime",
        "Dosage": "30 minutes before sleep"
    }
}


if __name__ == "__main__":
    root = tk.Tk()
    app = HerbalRemedyApp(root)
    
    # Configure tags for different message types
    app.display_area.tag_config("system", foreground="blue")
    app.display_area.tag_config("assistant", foreground="green")
    app.display_area.tag_config("user", foreground="purple")
    
    root.mainloop()