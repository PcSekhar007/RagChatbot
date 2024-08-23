import os
from openai import OpenAI
from config import OPENAI_API_KEY
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import uuid
import tiktoken

client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize sentence transformer model for encoding
model = SentenceTransformer('all-MiniLM-L6-v2')

# Constants
DIMENSION = 384  # Dimension of the sentence embeddings
INDEX_FILE = 'faiss_index.pkl'
DOCUMENTS_FILE = 'documents.pkl'
MAX_CONTEXT_LENGTH = 4000  # Adjust this based on your needs

tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")

# Load or create FAISS index
if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, 'rb') as f:
        index = pickle.load(f)
else:
    index = faiss.IndexFlatL2(DIMENSION)


# Load or create documents dictionary
if os.path.exists(DOCUMENTS_FILE):
    with open(DOCUMENTS_FILE, 'rb') as f:
        documents = pickle.load(f)
else:
    documents = {}

def save_index():
    with open(INDEX_FILE, 'wb') as f:
        pickle.dump(index, f)

def save_documents():
    with open(DOCUMENTS_FILE, 'wb') as f:
        pickle.dump(documents, f)

def count_tokens(text):
    return len(tokenizer.encode(text))

def add_to_knowledge_base(content, metadata=None):
    global index, documents
    
    doc_id = str(uuid.uuid4())
    vec = model.encode([content])[0]
    
    index.add(np.array([vec]).astype('float32'))
    
    documents[doc_id] = {
        'content': content,
        'metadata': metadata or {}
    }
    
    save_index()
    save_documents()
    
    return doc_id

def retrieve_relevant_docs(query, k=5):
    query_vec = model.encode([query])[0]
    _, I = index.search(np.array([query_vec]).astype('float32'), k)
    relevant_docs = []
    total_tokens = 0
    for i in I[0]:
        if i < len(documents):
            doc_id = list(documents.keys())[i]
            doc_content = documents[doc_id]['content']
            doc_tokens = count_tokens(doc_content)
            if total_tokens + doc_tokens > MAX_CONTEXT_LENGTH:
                break
            relevant_docs.append({
                'content': doc_content,
                'metadata': documents[doc_id]['metadata']
            })
            total_tokens += doc_tokens
    return relevant_docs

def generate_response(input_text, verbose=False):
    try:
        # Retrieve relevant documents
        relevant_docs = retrieve_relevant_docs(input_text)
        
        # Combine retrieved information with the input
        context = "\n".join([f"Document {i+1}: {doc['content']}" for i, doc in enumerate(relevant_docs)])
        
        # Count tokens in the context and input
        context_tokens = count_tokens(context)
        input_tokens = count_tokens(input_text)
        
        # If the total tokens exceed the limit, truncate the context
        if context_tokens + input_tokens > MAX_CONTEXT_LENGTH:
            max_context_tokens = MAX_CONTEXT_LENGTH - input_tokens - 100  # Leave some room for the prompt
            context = tokenizer.decode(tokenizer.encode(context)[:max_context_tokens])
        
        prompt = f"Context information:\n{context}\n\nBased on the above context and the user's input: '{input_text}', provide a helpful response. For any information used from the context, specify the document number in square brackets like this: [Document 1]."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with extensive knowledge. Use the provided context to inform your responses, but also draw on your general knowledge when appropriate. Always cite your sources using [Document X] notation when using information from the provided context."},
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = response.choices[0].message.content
        
        if verbose:
            return {
                'response': response_text,
                'sources': [{'content': doc['content'], 'metadata': doc['metadata']} for doc in relevant_docs]
            }
        else:
            return response_text
    except Exception as e:
        print(f"Error in generate_response: {e}")
        return "I'm sorry, I couldn't generate a response at this time."

def list_documents():
    if not documents:
        return []
    return [{'id': id, 'filename': doc['metadata'].get('filename', 'Unnamed document')} for id, doc in documents.items()]

def delete_document(doc_id):
    global index, documents
    if doc_id in documents:
        # Get the index of the document
        doc_index = list(documents.keys()).index(doc_id)
        
        # Remove from FAISS index
        index.remove_ids(np.array([doc_index]))
        
        # Remove from documents dictionary
        del documents[doc_id]
        
        # Save updated index and documents
        save_index()
        save_documents()
        return True
    return False

print(f"Knowledge base initialized with {index.ntotal} documents.")