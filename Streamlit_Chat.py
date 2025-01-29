import subprocess
import threading
import streamlit as st
import speech_recognition as sr
import pyttsx3
import time
import pyperclip  # For Copy Output functionality

class DeepSeekChatbot:
    def __init__(self):
        self.latest_response = ""  # Reset before new response
        self.is_muted = False  # Track mute state
        self.speech_thread = None  # Store the speech thread

    def toggle_speaker(self):
        """Toggle between mute and speaker functionality."""
        if self.is_muted:
            self.is_muted = False
            if self.latest_response:
                self.speak_output()  # Speak the latest response
        else:
            self.is_muted = True
            if self.speech_thread and self.speech_thread.is_alive():
                self.stop_speech()  # Stop speaking

    def stop_speech(self):
        """Stop the speech synthesis."""
        if self.speech_thread:
            self.speech_thread.join()  # Wait for the speech thread to finish

    def run_deepseek(self, prompt):
        """Run DeepSeek model and process the output."""
        st.session_state.status = "Generating..."
        try:
            self.process = subprocess.Popen(
                ["ollama", "run", "deepseek-r1:8b"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send user input to DeepSeek
            self.process.stdin.write(prompt + "\n")
            self.process.stdin.flush()
            self.process.stdin.close()

            # Read output in real-time
            response = ""
            for line in iter(self.process.stdout.readline, ""):
                response += line
                st.session_state.chat_history.append(f"🤖 Bot: {line.strip()}")

            self.latest_response = response.strip()  # Store response for speech output
            st.session_state.chat_history.append(f"🤖 Bot: {self.latest_response}")
            st.session_state.status = "Idle"

        except Exception as e:
            st.session_state.chat_history.append(f"❌ Error: {e}")
            st.session_state.status = "Error"

    def speak_output(self):
        """Convert latest response to speech without UI lag"""
        if self.latest_response and not self.is_muted:  # Check if not muted
            def speak_text():
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)  # Adjust speech speed
                engine.say(self.latest_response)
                engine.runAndWait()

            # Run speech synthesis in a separate thread
            self.speech_thread = threading.Thread(target=speak_text, daemon=True)
            self.speech_thread.start()

    def start_voice_input(self):
        """Convert speech to text & update input box"""
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                # Adjust for ambient noise (helps in noisy environments)
                recognizer.adjust_for_ambient_noise(source, duration=1)

                # Capture audio with a timeout
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                # Convert speech to text
                text = recognizer.recognize_google(audio)
                return text

            except sr.UnknownValueError:
                return "❌ Couldn't recognize speech."
            except sr.RequestError:
                return "❌ Speech service unavailable."
            except sr.WaitTimeoutError:
                return "❌ No speech detected. Try again."
            except Exception as e:
                return f"❌ Error: {e}"

# Initialize the chatbot
chatbot = DeepSeekChatbot()

# Streamlit UI
st.title("AI Chatbot")
st.sidebar.title("Options")

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'status' not in st.session_state:
    st.session_state.status = "Idle"

# Display chat history
for message in st.session_state.chat_history:
    st.write(message)

# User input
user_input = st.text_input("You:", "")
if st.button("Send"):
    if user_input:
        st.session_state.chat_history.append(f"🧑‍💻 You: {user_input}")
        chatbot.run_deepseek(user_input)

# Speaker button
if st.button("🔊" if not chatbot.is_muted else "🔇"):
    chatbot.toggle_speaker()

# Voice input button
if st.button("🎙️ Start Voice Input"):
    voice_input = chatbot.start_voice_input()
    if voice_input:
        st.session_state.chat_history.append(f"🧑‍💻 You: {voice_input}")
        chatbot.run_deepseek(voice_input)

# Status display
st.sidebar.write(f"Status: {st.session_state.status}")