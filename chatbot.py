from tts import text_to_speech
from stt import speech_to_text
from rag import generate_response

class Chatbot:
    def process_input(self, user_input):
        # For text input
        if isinstance(user_input, str):
            response_text = generate_response(user_input)
            audio_response = text_to_speech(response_text)
            return {'text': response_text, 'audio': audio_response}
        
        # For voice input (assuming user_input is a path to an audio file)
        elif isinstance(user_input, str) and user_input.endswith(('.mp3', '.wav', '.ogg')):
            transcribed_text = speech_to_text(user_input)
            if transcribed_text:
                response_text = generate_response(transcribed_text)
                audio_response = text_to_speech(response_text)
                return {'text': response_text, 'audio': audio_response, 'transcribed': transcribed_text}
            else:
                return {'error': 'Failed to transcribe audio'}
        
        else:
            return {'error': 'Invalid input format'}