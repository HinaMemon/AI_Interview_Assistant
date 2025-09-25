import speech_recognition as sr
import pyttsx3

engine = pyttsx3.init()
engine.setProperty("rate", 170)  # Speed
engine.setProperty("volume", 1)  # Volume


def speak(text):
    """Convert text to speech."""
    engine.say(text)
    engine.runAndWait()


def listen():
    """Convert speech to text (user’s answer)."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening...")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I didn’t understand."
    except sr.RequestError:
        return "Speech recognition service error."
