from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from pyvi import ViTokenizer
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
import re
import markdown

app = Flask(__name__)
CORS(app)

# Khai báo index và texts toàn cục
index = None
texts = []

# Cấu hình API keys và model
GOOGLE_API_KEY = "AIzaSyDTzg7ehK4XB_-nOJuq2lKsXBLDm5JACTE"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Model configurations
MODEL_CONFIGS = {
    "llama3.2:1b": {
        "type": "ollama",
        "url": OLLAMA_API_URL,
        "max_tokens": 500,
        "temperature": 0.1
    },
    "gemini-2.0-flash": {
        "type": "google",
        "url": GEMINI_API_URL,
        "api_key": GOOGLE_API_KEY,
        "max_tokens": 500,
        "temperature": 0.1
    }
}

# Model mặc định
CURRENT_MODEL = "gemini-2.0-flash"  # Có thể thay đổi thành "llama3.2:1b" để chuyển model

def preprocess_text_vietnamese(text):
    """Tiền xử lý văn bản tiếng Việt: tách từ bằng pyvi và chuẩn hóa."""
    text = ViTokenizer.tokenize(text)
    return text

def chunk_by_paragraphs(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current_chunk = ""
    sentence_count = 0
    max_sentences_per_chunk = 2
    
    for sentence in sentences:
        current_chunk += sentence + " "
        sentence_count += 1
        
        tokenized = ViTokenizer.tokenize(sentence)
        words = tokenized.split()
        last_word = words[-1].replace("_", " ") if words else ""
        
        if sentence_count >= max_sentences_per_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = ""
            sentence_count = 0
        
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    chunks = [chunk for chunk in chunks if chunk]
    return chunks

def extract_text_from_file(file_path):
    try:
        if file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise ValueError("Chỉ hỗ trợ file .txt")
        
        if not text.strip():
            raise ValueError("Không thể trích xuất nội dung từ file")
        return preprocess_text_vietnamese(text)
    except Exception as e:
        raise Exception(f"Lỗi khi đọc file: {str(e)}")

def process_files(directory_path):
    global index, texts
    try:
        all_texts = []
        txt_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.txt')]
        if not txt_files:
            raise ValueError("Không tìm thấy file .txt nào trong thư mục")
        
        txt_files = txt_files[:500]
        
        for txt_file in txt_files:
            file_path = os.path.join(directory_path, txt_file)
            text = extract_text_from_file(file_path)
            chunks = chunk_by_paragraphs(text)  
            all_texts.extend(chunks)
        
        if not all_texts:
            raise ValueError("Không có đoạn văn bản nào được tạo")
        
        model = SentenceTransformer('keepitreal/vietnamese-sbert')
        embeddings = model.encode(all_texts, convert_to_numpy=True)
        
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        
        texts = all_texts
        return index, texts
    except Exception as e:
        raise Exception(f"Lỗi khi xử lý files: {str(e)}")

def query_model(question, context, model_name=CURRENT_MODEL):
    config = MODEL_CONFIGS.get(model_name)
    if not config:
        raise Exception(f"Model {model_name} không được hỗ trợ")
    
    prompt = f"""Bạn là một trợ lý AI chuyên trả lời câu hỏi dựa trên tài liệu được cung cấp. Hãy đọc kỹ nội dung sau, tìm kiếm thông tin liên quan đến câu hỏi, và trả lời chính xác bằng tiếng Việt. Nếu thông tin đầy đủ, hãy dựa vào những thông tin, nội dung cung cấp để trả lời một cách đầy đủ, rõ ràng, diễn giải logic và tự nhiên nhất.

Nội dung:
{context}

Câu hỏi: {question}"""

    if config["type"] == "ollama":
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"]
        }
        response = requests.post(config["url"], json=payload)
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.text}")
        return response.json()["response"]
    
    elif config["type"] == "google":
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": config["max_tokens"],
                "temperature": config["temperature"]
            }
        }
        response = requests.post(
            f"{config['url']}?key={config['api_key']}",
            headers=headers,
            json=payload
        )
        if response.status_code != 200:
            raise Exception(f"Google API error: {response.text}")
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get("question")
    model_name = data.get("model", CURRENT_MODEL)  # Lấy model từ request, mặc định là CURRENT_MODEL
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    if 'index' not in globals() or index is None or not texts:
        return jsonify({"error": "Index not initialized"}), 400
    
    try:
        model = SentenceTransformer('keepitreal/vietnamese-sbert')
        question_embedding = model.encode([preprocess_text_vietnamese(question)], convert_to_numpy=True)
        
        k = 4
        distances, indices = index.search(question_embedding, k)
        relevant_texts = [texts[i] for i in indices[0]]
        context = " ".join(relevant_texts)
        print(f"Context for question '{question}':\n{context}")

        answer = query_model(question, context, model_name)
        print(f"ANSWER:{markdown.markdown(answer)}")
        return jsonify({"answer": answer, "model_used": model_name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    DATA_DIRECTORY = "./data"
    
    try:
        print("Đang xử lý các file txt...")
        index, texts = process_files(DATA_DIRECTORY)
        print(f"Xử lý hoàn tất, khởi động server với model mặc định: {CURRENT_MODEL}...")
    except Exception as e:
        print(f"Lỗi khi khởi tạo: {str(e)}")
        exit(1)
    
    app.run(port=5000, debug=True)