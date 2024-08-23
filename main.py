from flask import Flask, request, jsonify, render_template_string, send_file
from chatbot import Chatbot
from werkzeug.utils import secure_filename
from tts import text_to_speech
from rag import generate_response, add_to_knowledge_base, list_documents as rag_list_documents, delete_document
import os
import logging


logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
chatbot = Chatbot()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Voice Chatbot</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .chat-container {
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .chat-header {
            background-color: #4a90e2;
            color: #fff;
            padding: 15px 20px;
            font-size: 18px;
            font-weight: bold;
        }
        #chatHistory {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background-color: #f9f9f9;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 18px;
            max-width: 80%;
        }
        .user-message {
            background-color: #e1f0fe;
            color: #2c3e50;
            margin-left: auto;
        }
        .bot-message {
            background-color: #f0f0f0;
            color: #34495e;
        }
        #chatForm {
            display: flex;
            padding: 20px;
            background-color: #fff;
            border-top: 1px solid #eee;
        }
        #userInput {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            background-color: #4a90e2;
            color: #fff;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
            margin-left: 10px;
        }
        button:hover {
            background-color: #357abd;
        }
        #startSpeech {
            background-color: #27ae60;
        }
        #startSpeech:hover {
            background-color: #219a52;
        }
        #recordingStatus {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        #audioPlayer {
            width: 100%;
            margin-top: 20px;
        }
        .message-audio {
            margin-top: 10px;
            width: 100%;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 10px;
            font-style: italic;
            color: #666;
        }

        .loading::after {
            content: '';
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-left: 10px;
            border: 3px solid #4a90e2;
            border-radius: 50%;
            border-top: 3px solid #f3f3f3;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .source-info {
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }
        .source-link {
            color: #4a90e2;
            cursor: pointer;
        }
        .source-content {
            display: none;
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            margin-top: 5px;
        }
        .document-management {
            margin-top: 20px;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 8px;
        }

        .document-list ul {
            list-style-type: none;
            padding: 0;
        }

        .document-list li {
            margin-bottom: 10px;
            padding: 10px;
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .document-list button {
            background-color: #e74c3c;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
        }

        .document-list button:hover {
            background-color: #c0392b;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">Professional Voice Chatbot</div>
        <div id="chatHistory"></div>
         <div id="loadingIndicator" class="loading">Bot is thinking...</div>
        <form id="chatForm">
            <input type="text" id="userInput" placeholder="Type your message here...">
            <button type="submit">Send</button>
            <button type="button" id="startSpeech">🎤</button>
        </form>
    </div>
    <p id="recordingStatus"></p>
    <audio id="audioPlayer" controls style="display: none;"></audio>

    <script>
        const chatHistory = document.getElementById('chatHistory');
        const chatForm = document.getElementById('chatForm');
        const userInput = document.getElementById('userInput');
        const startSpeechBtn = document.getElementById('startSpeech');
        const recordingStatus = document.getElementById('recordingStatus');
        const loadingIndicator = document.getElementById('loadingIndicator');
        let mediaRecorder;
        let audioChunks = [];

        chatForm.onsubmit = function(e) {
            e.preventDefault();
            sendMessage(userInput.value);
        };

        function sendMessage(message) {
            if (!message.trim()) return;
            appendMessage(message, 'user-message');
            userInput.value = '';
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({input: message})
            })
            .then(response => response.json())
            .then(data => {
                console.log("Received data from server:", data);
                loadingIndicator.style.display = 'none';
                if (data.response && data.response.text) {
                    appendMessage(data.response.text, 'bot-message', data.response.audio_url);
                } else {
                    appendMessage('Error: Invalid response from server', 'bot-message');
                }
                })
            .catch(error => {
                console.error("Error sending message:", error);
                loadingIndicator.style.display = 'none'; 
                appendMessage('Error: Unable to get response from the bot.', 'bot-message');
            });
        }

        function appendMessage(message, className, audioUrl = null, sources = null) {
            const messageElement = document.createElement('div');
            messageElement.className = `message ${className}`;
            
            const textElement = document.createElement('div');
            textElement.innerHTML = message;  // Using innerHTML to render the citation links
            messageElement.appendChild(textElement);
            
            if (sources) {
                const sourceElement = document.createElement('div');
                sourceElement.className = 'source-info';
                sourceElement.innerHTML = 'Sources: ' + sources.map((source, index) => 
                    `<span class="source-link" onclick="toggleSource(${index})">[${index + 1}]</span>`
                ).join(', ');
                messageElement.appendChild(sourceElement);
                
                sources.forEach((source, index) => {
                    const sourceContent = document.createElement('div');
                    sourceContent.className = 'source-content';
                    sourceContent.id = `source-${index}`;
                    sourceContent.textContent = `Source ${index + 1}: ${source.content}`;
                    if (source.metadata && source.metadata.filename) {
                        sourceContent.textContent += ` (File: ${source.metadata.filename})`;
                    }
                    messageElement.appendChild(sourceContent);
                });
            }
            
            if (audioUrl) {
                const audioElement = document.createElement('audio');
                audioElement.controls = true;
                audioElement.src = audioUrl;
                audioElement.className = 'message-audio';
                messageElement.appendChild(audioElement);
            }
            
            chatHistory.appendChild(messageElement);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
        
        function toggleSource(index) {
            const sourceContent = document.getElementById(`source-${index}`);
            if (sourceContent.style.display === 'none' || sourceContent.style.display === '') {
                sourceContent.style.display = 'block';
            } else {
                sourceContent.style.display = 'none';
            }
        }

        audioPlayer.onError = function(e) {
            console.error("Audio player error:", e);
        };

        startSpeechBtn.onclick = async function() {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                mediaRecorder.stop();
                startSpeechBtn.textContent = "🎤";
                recordingStatus.textContent = "Processing...";
            } else {

                try{
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                
                    mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    audioChunks = [];
                    
                    const formData = new FormData();
                    formData.append('audio', audioBlob, 'recording.wav');
                    
                    fetch('/transcribe', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.transcription) {
                            userInput.value = data.transcription;
                            recordingStatus.textContent = "Transcription complete. You can edit the text before sending.";
                        } else {
                            recordingStatus.textContent = "Transcription failed. Please try again.";
                        }
                    });
                };
                
                mediaRecorder.start();
                startSpeechBtn.textContent = "⏹️";
                recordingStatus.textContent = "Recording...";

                }catch (err) {
                    console.error("Error accessing microphone:", err);
                    recordingStatus.textContent = "Error accessing microphone. Please check your settings.";
                }

                
            }
        };
    </script>


<script>
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const uploadStatus = document.getElementById('uploadStatus');
    const documentList = document.getElementById('documentList');

    function loadDocuments() {
        fetch('/list_documents')
            .then(response => response.json())
            .then(data => {
                documentList.innerHTML = '';
                data.forEach(doc => {
                    const li = document.createElement('li');
                    li.textContent = `${doc.filename} (ID: ${doc.id})`;
                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.onclick = () => deleteDocument(doc.id);
                    li.appendChild(deleteButton);
                    documentList.appendChild(li);
                });
            })
            .catch(error => {
                console.error('Error loading documents:', error);
            });
    }

    function deleteDocument(id) {
        fetch('/delete_document', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({id: id})
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                loadDocuments();  // Refresh the list
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error deleting document:', error);
        });
    }

    if (uploadForm) {
        uploadForm.onsubmit = function(e) {
            e.preventDefault();
            var formData = new FormData(this);
            fetch('/upload_document', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                uploadStatus.textContent = data.message;
                loadDocuments();  // Refresh the list after upload
            })
            .catch(error => {
                console.error('Error:', error);
                uploadStatus.textContent = 'Upload failed. Please try again.';
            });
        };
    }

    // Load documents when the page loads
    loadDocuments();
});
</script>

<div class="document-management">
    <h3>Document Management</h3>
    <div class="upload-container">
        <h4>Upload Document to Knowledge Base</h4>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="fileInput" name="file" accept=".txt,.pdf,.doc,.docx">
            <button type="submit">Upload</button>
        </form>
        <p id="uploadStatus"></p>
    </div>
    <div class="document-list">
        <h4>Uploaded Documents</h4>
        <ul id="documentList"></ul>
    </div>
</div>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json['input']
    
    if user_input.lower() in ["what documents do you have in your knowledge base?", "list documents", "show documents"]:
        docs = rag_list_documents()
        if not docs:
            response_text = "The knowledge base is currently empty. No documents have been uploaded yet."
        else:
            response_text = "Here are the documents in the knowledge base:\n"
            for doc in docs:
                response_text += f"- {doc['filename']} (ID: {doc['id']})\n"
        response = {'response': response_text, 'sources': []}
    else:
        response = generate_response(user_input, verbose=True)

    print(f"User input: {user_input}")
    print(f"Bot response: {response}")
    
    audio_response = text_to_speech(response['response'])
    
    response_data = {
        'response': {
            'text': response['response'],
            'sources': response.get('sources', [])
        }
    }    
    if audio_response:
        audio_filename = os.path.basename(audio_response)
        audio_url = f'/audio/{audio_filename}'
        response_data['response']['audio_url'] = audio_url
        print(f"Audio file generated: {audio_response}")
        print(f"Audio URL: {audio_url}")
    else:
        response_data['response']['audio_url'] = None
        print("No audio file generated")
    
    print(f"Response data: {response_data}")

    return jsonify(response_data)

@app.route('/audio/<filename>')
def serve_audio(filename):
    file_path = os.path.join('temp', filename)
    if os.path.exists(file_path):
        print(f"Serving audio file: {file_path}")
        return send_file(file_path, mimetype='audio/mpeg')
    else:
        print(f"Audio file not found: {file_path}")
        return "Audio file not found", 404


@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    # Make sure to create a 'temp' directory in your project folder
    if not os.path.exists('temp'):
        os.makedirs('temp')

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if audio_file:
        filename = secure_filename(audio_file.filename)
        audio_path = os.path.join('temp', filename)
        audio_file.save(audio_path)
        
        # Use the speech_to_text function from your stt.py file
        from stt import speech_to_text
        transcribed_text = speech_to_text(audio_path)
        
        # Clean up the temporary file
        os.remove(audio_path)
        
        return jsonify({'transcription': transcribed_text})

@app.route('/add_knowledge', methods=['POST'])
def add_knowledge():
    new_info = request.json['information']
    add_to_knowledge_base(new_info)
    return jsonify({'status': 'success', 'message': 'Information added to knowledge base'})

@app.route('/list_documents', methods=['GET'])
def list_docs():
    return jsonify(rag_list_documents())

@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('temp', filename)
        file.save(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        doc_id = add_to_knowledge_base(content, {'filename': filename})
        
        os.remove(file_path)  # Clean up the temporary file
        
        return jsonify({'status': 'success', 'message': f'Document {filename} added to knowledge base with ID: {doc_id}'})

@app.route('/delete_document', methods=['POST'])
def delete_doc():
    doc_id = request.json['id']
    if delete_document(doc_id):
        return jsonify({'status': 'success', 'message': f'Document with ID {doc_id} deleted successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Document not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)