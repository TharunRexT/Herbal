import os
import speech_recognition as sr
from gtts import gTTS
from playsound3 import playsound
import pandas as pd
import sounddevice as sd
from scipy.io.wavfile import write
import difflib
import requests
import configparser
import logging



logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

config = configparser.ConfigParser()
config.read("config.ini")
OPENROUTER_API_KEY = config.get("OpenRouter", "API_KEY", fallback=None)
OPENROUTER_URL = "https://openrouter.ai/api/v1/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"  # ✅ Updated valid model



def speak(text):
    # ...existing code...
    try:
        tts = gTTS(text=text, lang='en')
        filename = "voice.mp3"
        tts.save(filename)
        playsound(filename)
        os.remove(filename)
    except Exception as e:
        logging.error(f"Error in speak(): {e}")



recognizer = sr.Recognizer()
def recognize_speech():
    fs = 44100
    duration = 5
    logging.info("🎤 Recording... Speak now!")
    try:
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        write("input.wav", fs, audio)
        logging.info("Processing audio...")
        with sr.AudioFile("input.wav") as source:
            recorded_audio = recognizer.record(source)
        query = recognizer.recognize_google(recorded_audio)
        query = query.lower().strip()
        logging.info(f"🗣 You said: {query}")
        return query
    except Exception as e:
        logging.error(f"Error recognizing speech: {e}")
        return ""



def lookup_csv(disease):
    try:
    # ...existing code...
        df = pd.read_csv("herbs.csv")
        matches = difflib.get_close_matches(disease, df["Disease"].dropna().str.lower().tolist(), n=1, cutoff=0.4)
    # ...existing code...
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
        logging.error(f"CSV lookup error: {e}")
        return None



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
    }
}



def ai_herbal_remedy(disease):
    if not OPENROUTER_API_KEY:
        logging.warning("OpenRouter API key not set. Skipping AI fetch.")
        return None

    prompt = f"Provide 2-3 herbal remedies for {disease} in structured format: HerbName, Ingredients, Preparation, Dosage."
    # ...existing code...
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
            json={
                'model': OPENROUTER_MODEL,
                'prompt': prompt,
                'temperature': 0.7,
                'max_tokens': 400
            },
            timeout=20
        )
    # ...existing code...
        if response.status_code == 200:
            result = response.json()
            # ...existing code...
            return result['choices'][0]['text']
        else:
            logging.error(f"OpenRouter API error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logging.error(f"AI fetch error: {e}")
        return None



if __name__ == "__main__":
    logging.info("Program started.")
    speak("Hello! Please tell me which disease you want herbal remedies for.")
    disease = recognize_speech()

    # ...existing code...
    if disease:
        logging.info("Searching for herbal remedies...")
        info = lookup_csv(disease)
    # ...existing code...

        if not info and disease in herbal_fallback:
            r = herbal_fallback[disease]
            info = (
                f"Disease: {disease.capitalize()}\n"
                f"Herbal Remedy: {r['HerbName']}\n"
                f"Ingredients: {r['Ingredients']}\n"
                f"Preparation: {r['Preparation']}\n"
                f"Dosage: {r['Dosage']}"
            )
            # ...existing code...

        if not info:
            ai_info = ai_herbal_remedy(disease)
            # ...existing code...
            if ai_info:
                info = ai_info

        if not info:
            info = f"Sorry, I could not find herbal remedies for {disease}."
            logging.warning(info)

        print(info)
        speak(info)
    else:
        logging.warning("No disease recognized from speech.")
        speak("Sorry, I could not hear you properly. Please try again.")