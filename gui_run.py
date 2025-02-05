import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, Toplevel, messagebox
import speech_recognition as sr
import pyttsx3
import time
import pyperclip  # For Copy Output functionality

import mistune
from bs4 import BeautifulSoup

class DeepSeekChatbot:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Chatbot")
        self.root.geometry("750x650")
        self.root.configure(bg="#1e1e1e")  # Dark mode background
        self.root.minsize(650, 600)
        
        # Title
        self.title_label = tk.Label(root, text="AI Chatbot", font=("Arial", 16, "bold"), fg="white", bg="#1e1e1e")
        self.title_label.pack(pady=10)

        # Status Button (Showing status: generating/idle)
        self.status_button = tk.Button(root, text="Idle", font=("Arial", 12), bg="#28a745", fg="white", state=tk.DISABLED)
        self.status_button.pack(pady=5)

        # Chat History (Scrollable)
        self.chat_history = scrolledtext.ScrolledText(root, width=75, height=20, font=("Arial", 12), bg="#34495e", fg="white")
        self.chat_history.pack(pady=10, fill=tk.Y, expand=True)
        self.chat_history.config(state=tk.DISABLED)  # Read-only

        # User Input Frame
        self.user_input_frame = tk.Frame(root, bg="#34495e")
        self.user_input_frame.pack(pady=10, fill=tk.X)

        self.prompt_entry = tk.Entry(self.user_input_frame, width=50, font=("Arial", 12), bg="#34495e", fg="white")
        self.prompt_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.send_btn = tk.Button(self.user_input_frame, text="Send", command=self.start_chat, font=("Arial", 12), bg="#007acc", fg="white")
        self.send_btn.pack(side=tk.LEFT, padx=5)

        # Mic Input Button 🎙️
        self.mic_btn = tk.Button(self.user_input_frame, text="🎙️", command=self.start_voice_input, font=("Arial", 12), bg="#ff9900", fg="white")
        self.mic_btn.pack(side=tk.LEFT, padx=5)

        # Speaker Output Button 🔊
        self.speaker_btn = tk.Button(self.user_input_frame, text="🔊", command=self.toggle_speaker, font=("Arial", 12), bg="#34c759", fg="white")
        self.speaker_btn.pack(side=tk.LEFT, padx=5)

        # Control Buttons Frame
        self.button_frame = tk.Frame(root, bg="#1e1e1e")
        self.button_frame.pack(pady=10, fill=tk.X)

        self.stop_btn = tk.Button(self.button_frame, text="Stop", command=self.stop_chat, font=("Arial", 12), bg="#d9534f", fg="white", state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = tk.Button(self.button_frame, text="Clear Chat", command=self.clear_chat, font=("Arial", 12), bg="#5bc0de", fg="white")
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        self.copy_btn = tk.Button(self.button_frame, text="Copy Output", command=self.copy_output, font=("Arial", 12), bg="#ffc107", fg="white")
        self.copy_btn.pack(side=tk.LEFT, padx=5)

        self.regenerate_btn = tk.Button(self.button_frame, text="Regenerate", command=self.regenerate_response, font=("Arial", 12), bg="#28a745", fg="white")
        self.regenerate_btn.pack(side=tk.LEFT, padx=5)

        self.process = None  # Store the subprocess instance
        self.latest_response = ""  # Reset before new response
        self.is_muted = False  # Track mute state
        self.speech_thread = None  # Store the speech thread

    def toggle_speaker(self):
        """Toggle between mute and speaker functionality."""
        if self.is_muted:
            self.speaker_btn.config(text="🔊")
            self.is_muted = False
            if self.latest_response:
                self.start_reading()  # Start reading
        else:
            self.speaker_btn.config(text="🔇")
            self.is_muted = True
            self.stop_reading()  # Stop reading


    def start_reading(self):
        """Start reading the latest response immediately."""
        if self.latest_response:
            self.is_speaking = True  # Set flag to indicate speech is active
            self.speaker_btn.config(text="🔇")  # Change button icon
            print("paContinue")  # Signal reading start
            self.speech_thread = threading.Thread(target=self.speak_output, daemon=True)
            self.speech_thread.start()

    def stop_reading(self):
        """Immediately stop reading the output."""
        if self.speech_thread and self.speech_thread.is_alive():
            print("paAbort")  # Signal reading stopped
            self.is_speaking = False  # Reset flag
            self.speaker_btn.config(text="🔊")  # Change button icon
            self.speech_thread.join(timeout=0.1)  # Attempt immediate stop

    def restart_reading(self):
        """Restart the reading process."""
        self.stop_reading()  # Stop current reading
        self.start_reading()  # Start again
        print("paComplete")  # Signal completion of restart

    def markdown_to_plain(md_text):
        html = mistune.markdown(md_text)
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()


    def run_deepseek(self, prompt):
        """Run DeepSeek model and process the output."""
        self.status_button.config(text="Generating...", bg="Red")
        self.send_btn.config(state=tk.DISABLED)
        try:
            self.process = subprocess.Popen(
                ["ollama", "run", "deepseek-r1:1.5b"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # Send user input to DeepSeek
            self.process.stdin.write(prompt + "\n")
            self.process.stdin.flush()
            self.process.stdin.close()

            # Enable chat history update
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.insert(tk.END, f"\n🧑‍💻 You: {prompt}\n", "user")
            self.chat_history.tag_config("user", foreground="Pink")

            # Read output in real-time
            response = ""
            for line in iter(self.process.stdout.readline, ""):
                response += line
                self.typewriter_effect((line), "bot")


            self.latest_response = response.strip()  # Store response for speech output
            self.chat_history.insert(tk.END, "\n", "bot")


            self.chat_history.tag_config("bot", foreground="lightgreen")
            self.chat_history.config(state=tk.DISABLED)
            self.status_button.config(text="Idle", bg="#28a745")
            self.send_btn.config(state=tk.NORMAL)

        except Exception as e:
            self.chat_history.insert(tk.END, f"\n❌ Error: {e}\n", "error")
            self.chat_history.tag_config("error", foreground="red")
            self.status_button.config(text="Error", bg="#dc3545")

    def typewriter_effect(self, text, tag):
        """Simulates typewriter effect for bot responses"""
        for char in text:
            self.chat_history.insert(tk.END, char, tag)
            self.chat_history.update()
            time.sleep(0.03)  # Adjust speed for typewriter effect
        self.chat_history.see(tk.END)

    def start_chat(self):
        """Start the chatbot interaction"""
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            return

        self.prompt_entry.delete(0, tk.END)  # Clear input field
        self.send_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Run DeepSeek in a separate thread
        threading.Thread(target=self.run_deepseek, args=(prompt,), daemon=True).start()

    def stop_chat(self):
        """Stop the chat if still generating"""
        if self.process:
            self.process.terminate()
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.insert(tk.END, "\n🛑 Chat stopped.\n", "error")
            self.chat_history.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.send_btn.config(state=tk.NORMAL)

    def clear_chat(self):
        """Clear the chat history"""
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.delete(1.0, tk.END)
        self.chat_history.config(state=tk.DISABLED)

    def copy_output(self):
        """Copy the latest response to clipboard"""
        if self.latest_response:
            pyperclip.copy(self.latest_response)
            messagebox.showinfo("Copied", "Response copied to clipboard.")

    def regenerate_response(self):
        """Regenerate the last response"""
        if self.latest_response:
            threading.Thread(target=self.run_deepseek, args=(self.latest_response,), daemon=True).start()

    def start_voice_input(self):
        """Opens a listening window & converts speech to text"""
        listen_window = Toplevel(self.root)
        listen_window.title("Listening...")
        listen_window.geometry("300x100")
        listen_label = tk.Label(listen_window, text="🎙️ Listening...", font=("Arial", 14), fg="white", bg="black")
        listen_label.pack(expand=True, fill=tk.BOTH)

        threading.Thread(target=self.voice_to_text, args=(listen_window,), daemon=True).start()

    def voice_to_text(self, listen_window):
        """Convert speech to text & update input box"""
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                # Update UI to indicate listening
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, "🎙️ Listening...")
                listen_window.update()

                # Adjust for ambient noise (helps in noisy environments)
                recognizer.adjust_for_ambient_noise(source, duration=1)

                # Capture audio with a timeout
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                # Convert speech to text
                text = recognizer.recognize_google(audio)
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, text)

            except sr.UnknownValueError:
                text = "❌ Couldn't recognize speech."
            except sr.RequestError:
                text = "❌ Speech service unavailable."
            except sr.WaitTimeoutError:
                text = "❌ No speech detected. Try again."
            except Exception as e:
                text = f"❌ Error: {str(e)}"

                self.root.after(0, self.prompt_entry.delete, 0, tk.END)
                self.root.after(0, self.prompt_entry.insert, 0, text)

            except Exception as e:
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, f"❌ Error: {e}")

        # Ensure the listening window is closed after operation
        listen_window.destroy()

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

# Run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    gui = DeepSeekChatbot(root)
    root.mainloop()