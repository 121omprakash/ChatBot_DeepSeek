import gradio as gr
import subprocess
import threading
import time
import speech_recognition as sr
import pyttsx3
import pyperclip
import mistune
from bs4 import BeautifulSoup


# Global Variables and Initialization
 
latest_response = ""       # Stores the latest AI response (plain text)
is_speaking = False         # Flag to indicate if TTS is active
is_muted = False            # Flag to track speaker mute state
process_handle = None       # Subprocess handle for the DeepSeek call
chat_history = []           # List to store conversation messages as dictionaries

# Initialize text-to-speech engine
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 150)

# Initialize Speech Recognizer
recognizer = sr.Recognizer()

# 
# Utility Functions
# 

def debug_log(message: str):
    """Simple debug logger."""
    print(f"[DEBUG] {message}")

def markdown_to_plain(md_text: str) -> str:
    """
    Convert Markdown-formatted text to plain text.
    """
    html = mistune.markdown(md_text)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()

def typewriter_effect(text: str, speed: float = 0.03) -> str:
    """
    Simulate a typewriter effect by gradually building the string.
    (Used to simulate delay during streaming.)
    """
    debug_log("Starting typewriter effect simulation.")
    result = ""
    for char in text:
        result += char
        time.sleep(speed)
    debug_log("Typewriter effect simulation complete.")
    return result

# =============================================================================
# DeepSeek Model Streaming Functions
# =============================================================================

def stream_deepseek(prompt: str):
    """
    Generator that calls the DeepSeek model via Ollama and yields incremental updates
    as a list of message dictionaries (using "role" and "content").
    """
    global latest_response, process_handle
    debug_log(f"Starting DeepSeek for prompt: {prompt}")
    try:
        process_handle = subprocess.Popen(
            ["ollama", "run", "deepseek-r1:8b"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        # Send the prompt
        process_handle.stdin.write(prompt + "\n")
        process_handle.stdin.flush()
        process_handle.stdin.close()
        accumulated = ""
        # Initially yield the user's message only
        yield [{"role": "user", "content": prompt}]
        for line in iter(process_handle.stdout.readline, ""):
            accumulated += line
            partial = markdown_to_plain(accumulated)
            # Yield updated conversation with partial response
            yield [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": partial}
            ]
            time.sleep(0.03)
        latest_response = markdown_to_plain(accumulated.strip())
        debug_log("DeepSeek streaming complete.")
        yield [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": latest_response}
        ]
    except Exception as e:
        debug_log(f"Error streaming response: {e}")
        yield [{"role": "assistant", "content": f"❌ Error: {e}"}]

def stream_chat_with_ai(prompt: str):
    """
    Generator to stream the chat interaction.
    It appends the user's message to the chat history and then yields updates
    from the DeepSeek streaming function.
    """
    global chat_history
    if not prompt.strip():
        yield chat_history
        return
    # Append user's message to global history (in message dictionary format)
    chat_history.append({"role": "user", "content": prompt})
    yield chat_history
    # Stream the AI response and update the chat history dynamically
    for messages in stream_deepseek(prompt):
        # Replace any previous assistant message if exists in the last item.
        if chat_history and chat_history[-1]["role"] == "assistant":
            chat_history[-1] = messages[-1]
        else:
            chat_history.append(messages[-1])
        yield chat_history

# =============================================================================
# Chat Control Functions
# =============================================================================

def stop_chat() -> str:
    """
    Stop the ongoing AI generation (if any).
    """
    global process_handle, chat_history
    debug_log("Stop chat requested.")
    if process_handle:
        try:
            process_handle.terminate()
            chat_history.append({"role": "system", "content": "🛑 Chat stopped."})
            return "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
        except Exception as e:
            debug_log(f"Error stopping chat: {e}")
            return f"❌ Error: {e}"
    return "No active process to stop."

def clear_chat() -> str:
    """
    Clear the chat history.
    """
    global chat_history
    chat_history = []
    debug_log("Chat history cleared.")
    return ""

def copy_response() -> str:
    """
    Copy the latest AI response to the clipboard.
    """
    global latest_response
    if latest_response:
        try:
            pyperclip.copy(latest_response)
            debug_log("Response copied to clipboard.")
            return "✅ Response copied to clipboard!"
        except Exception as e:
            debug_log(f"Error copying response: {e}")
            return f"❌ Error: {e}"
    return "⚠️ No response to copy."

def regenerate_last_response() -> str:
    """
    Regenerate the last AI response.
    (For simplicity, this calls chat_with_ai using latest_response as prompt.)
    """
    global latest_response
    debug_log("Regenerate response requested.")
    if latest_response:
        new_response = chat_with_ai(latest_response)
        return new_response
    return "⚠️ No previous response to regenerate."

# =============================================================================
# Voice and Audio Functions
# =============================================================================

def voice_input() -> str:
    """
    Capture voice input using SpeechRecognition and return the recognized text.
    """
    debug_log("Voice input triggered.")
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            text = recognizer.recognize_google(audio)
            debug_log(f"Voice recognized: {text}")
            return text
    except sr.UnknownValueError:
        debug_log("Speech not recognized.")
        return "❌ Couldn't recognize speech."
    except sr.RequestError:
        debug_log("Speech service unavailable.")
        return "❌ Speech service unavailable."
    except Exception as e:
        debug_log(f"Voice input error: {e}")
        return f"❌ Error: {str(e)}"

def speak_response() -> str:
    """
    Convert the latest AI response to speech using pyttsx3.
    """
    global latest_response, is_muted
    if latest_response and not is_muted:
        def speak_text():
            try:
                local_engine = pyttsx3.init()
                local_engine.setProperty('rate', 150)
                local_engine.say(latest_response)
                local_engine.runAndWait()
                debug_log("TTS finished.")
            except Exception as e:
                debug_log(f"TTS error: {e}")
        threading.Thread(target=speak_text, daemon=True).start()
        return "🔊 Speaking the response..."
    else:
        debug_log("No response to speak or speaker is muted.")
        return "⚠️ No response to speak or speaker is muted."

def toggle_speaker() -> str:
    """
    Toggle the speaker state (mute/unmute) and stop TTS if muting.
    """
    global is_muted, tts_engine
    is_muted = not is_muted
    if is_muted:
        try:
            tts_engine.stop()
        except Exception as e:
            debug_log(f"TTS stop error: {e}")
        debug_log("Speaker muted.")
        return "🔇 Speaker Muted"
    else:
        debug_log("Speaker unmuted.")
        return "🔊 Speaker On"

def start_reading() -> str:
    """
    Start reading the latest response (TTS).
    """
    global latest_response
    if latest_response:
        debug_log("Starting TTS reading.")
        return speak_response()
    return "⚠️ No response available to read."

def stop_reading() -> str:
    """
    Stop TTS reading.
    """
    global tts_engine
    try:
        tts_engine.stop()
        debug_log("TTS reading stopped.")
        return "⏹ TTS stopped."
    except Exception as e:
        debug_log(f"TTS stop error: {e}")
        return f"❌ Error stopping TTS: {e}"

def restart_reading() -> str:
    """
    Restart TTS reading.
    """
    stop_reading()
    time.sleep(0.1)
    return start_reading()


with gr.Blocks(theme=gr.themes.Soft()) as ui:
    gr.Markdown("# 🤖 AI Chatbot with Voice, Copy, and Regenerate Features")
    

    
    # Use Chatbot component with 'messages' type for better UX
    chat_display = gr.Chatbot(label="Conversation", type="messages")
    
    with gr.Row():
        prompt_input = gr.Textbox(placeholder="Type your message...", label="Your Message", lines=2)
        send_btn = gr.Button("Send", variant="primary")


    with gr.Row():
        mic_btn = gr.Button("🎙️ Voice Input")
        tts_btn = gr.Button("🔊 Speak Response")
        toggle_speaker_btn = gr.Button("Toggle Speaker")
        copy_btn = gr.Button("📋 Copy Output")
        regen_btn = gr.Button("🔄 Regenerate")
        clear_btn = gr.Button("🧹 Clear Chat")
        stop_btn = gr.Button("🛑 Stop Chat")
    
    # Button interactions:
    # For sending, we use our streaming function (which yields message lists)
    send_btn.click(fn=stream_chat_with_ai, inputs=prompt_input, outputs=chat_display)
    clear_btn.click(fn=clear_chat, inputs=None, outputs=chat_display)
    regen_btn.click(fn=regenerate_last_response, inputs=None, outputs=chat_display)
    stop_btn.click(fn=stop_chat, inputs=None, outputs=chat_display)
    mic_btn.click(fn=voice_input, inputs=None, outputs=prompt_input)
    tts_btn.click(fn=speak_response, inputs=None, outputs=None)
    toggle_speaker_btn.click(fn=toggle_speaker, inputs=None, outputs=None)
    copy_btn.click(fn=copy_response, inputs=None, outputs=None)
    
    # Load handler to update the chat display when the app loads
    ui.load(fn=lambda: chat_display, inputs=None, outputs=chat_display)

# =============================================================================
# Launch the Application on Localhost
# =============================================================================

if __name__ == "__main__":
    ui.launch(server_name="127.0.0.1", server_port=7860, share=True)
