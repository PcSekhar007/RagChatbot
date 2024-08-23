from openai import OpenAI
from config import OPENAI_API_KEY
import os
import re
client = OpenAI(api_key=OPENAI_API_KEY)

def text_to_speech(text):
    try:
        # Clean the text before processing
        cleaned_text = clean_text_for_tts(text)
        
        # Truncate to 4000 characters as per OpenAI's limit
        cleaned_text = cleaned_text[:4000]
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=cleaned_text
        )
        
        # The response is an audio file, which we'll save temporarily
        audio_file_path = os.path.join('temp', f'response_{hash(cleaned_text)}.mp3')
        response.stream_to_file(audio_file_path)
        
        return audio_file_path
    except Exception as e:
        print(f"Error in text_to_speech: {e}")
        return None
    
def clean_text_for_tts(text):
    # Remove 'text:' from the beginning if present
    text = re.sub(r'^text:\s*', '', text, flags=re.IGNORECASE)
    
    # Remove file path or name from the end
    text = re.sub(r'\s*[\w/\\.-]+\.mp3$', '', text)
    
    # Trim any leading/trailing whitespace
    return text.strip()