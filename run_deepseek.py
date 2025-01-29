import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, Toplevel
import pyttsx3
import speech_recognition as sr
import time
import pyperclip
import markdown

class PersonalizedAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("Personalized AI Assistant")
        self.root.geometry("800x700")
        self.root.configure(bg="#2c3e50")
        
        # Header
        self.header = tk.Label(root, text="Personalized AI Assistant", font=("Arial", 16, "bold"), fg="white", bg="#2c3e50")
        self.header.pack(pady=10)

        # Status
        self.status_button = tk.Button(root, text="Idle", font=("Arial", 12), bg="#28a745", fg="white", state=tk.DISABLED)
        self.status_button.pack(pady=5)

        # Chat History
        self.chat_history = scrolledtext.ScrolledText(root, width=90, height=25, font=("Arial", 12), bg="#34495e", fg="white")
        self.chat_history.pack(padx=10, pady=5)
        self.chat_history.config(state=tk.DISABLED)

        # User Input Frame
        self.user_input_frame = tk.Frame(root, bg="#34495e")
        self.user_input_frame.pack(pady=10, fill=tk.X)

        self.prompt_entry = tk.Entry(self.user_input_frame, width=60, font=("Arial", 12), bg="#34495e", fg="white")
        self.prompt_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.send_btn = tk.Button(self.user_input_frame, text="Send", command=self.start_chat, font=("Arial", 12), bg="#007acc", fg="white")
        self.send_btn.pack(side=tk.LEFT, padx=5)

        # Mic Input Button 🎙️
        self.mic_btn = tk.Button(self.user_input_frame, text="🎙️", command=self.start_voice_input, font=("Arial", 12), bg="#ff9900", fg="white")
        self.mic_btn.pack(side=tk.LEFT, padx=5)

        # Copy Button
        self.copy_btn = tk.Button(self.user_input_frame, text="Copy Output", command=self.copy_output, font=("Arial", 12), bg="#ffc107", fg="white")
        self.copy_btn.pack(side=tk.LEFT, padx=5)

        self.process = None
        self.latest_response = ""

    def run_deepseek(self, prompt):
        """Run DeepSeek model and process the output."""
        self.status_button.config(text="Generating...", bg="#ffc107")
        self.send_btn.config(state=tk.DISABLED)
        try:
            self.process = subprocess.Popen(
                ["ollama", "run", "deepseek-r1:8b"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.process.stdin.write(prompt + "\n")
            self.process.stdin.flush()
            self.process.stdin.close()

            # Update chat history
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.insert(tk.END, f"\n🧑‍💻 You: {prompt}\n", "user")
            self.chat_history.tag_config("user", foreground="lightblue")

            response = ""
            for line in iter(self.process.stdout.readline, ""):
                response += line
                self.typewriter_effect(line, "bot")

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
        """Simulate typewriter effect for bot responses"""
        for char in text:
            self.chat_history.insert(tk.END, char, tag)
            self.chat_history.update()
            time.sleep(0.03)
        self.chat_history.see(tk.END)

    def start_chat(self):
        """Start the chat interaction"""
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            return

        self.prompt_entry.delete(0, tk.END)
        self.send_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.run_deepseek, args=(prompt,), daemon=True).start()

    def copy_output(self):
        """Copy the latest response to clipboard"""
        if self.latest_response:
            pyperclip.copy(self.latest_response)
            messagebox.showinfo("Copied", "Response copied to clipboard.")

    def start_voice_input(self):
        """Start voice input for converting speech to text"""
        listen_window = Toplevel(self.root)
        listen_window.title("Listening...")
        listen_window.geometry("300x100")
        listen_label = tk.Label(listen_window, text="🎙️ Listening...", font=("Arial", 14), fg="white", bg="black")
        listen_label.pack(expand=True, fill=tk.BOTH)
        threading.Thread(target=self.voice_to_text, args=(listen_window,), daemon=True).start()

    def voice_to_text(self, listen_window):
        """Convert speech to text and update the input field"""
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, "🎙️ Listening...")
                listen_window.update()

                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                text = recognizer.recognize_google(audio)
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, text)

            except sr.UnknownValueError:
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, "❌ Couldn't recognize speech.")
            except sr.RequestError:
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, "❌ Speech service unavailable.")
            except sr.WaitTimeoutError:
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, "❌ No speech detected. Try again.")
            except Exception as e:
                self.prompt_entry.delete(0, tk.END)
                self.prompt_entry.insert(0, f"❌ Error: {e}")

        listen_window.destroy()

# Run the assistant
if __name__ == "__main__":
    root = tk.Tk()
    assistant = PersonalizedAssistant(root)
    root.mainloop()
