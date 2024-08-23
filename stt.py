import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def speech_to_text(audio_file_path):
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error in speech_to_text: {e}")
        return None