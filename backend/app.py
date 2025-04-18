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

def preprocess_text_vietnamese(text):
    """Tiền xử lý văn bản tiếng Việt: tách từ bằng pyvi và chuẩn hóa."""
    # Tách từ bằng pyvi
    text = ViTokenizer.tokenize(text)
    # Có thể thêm các bước chuẩn hóa khác nếu cần (xóa ký tự đặc biệt, chuyển về chữ thường, v.v.)
    return text





def chunk_by_paragraphs(text):
    # Bước 1: Tách thành các câu
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current_chunk = ""
    sentence_count = 0
    max_sentences_per_chunk = 2  # Số câu tối đa trong một đoạn (nhắm đến 3-4 câu)
    
    for sentence in sentences:
        # Thêm câu vào chunk hiện tại
        current_chunk += sentence + " "
        sentence_count += 1
        
        # Kiểm tra điều kiện để cắt chunk
        tokenized = ViTokenizer.tokenize(sentence)
        words = tokenized.split()
        last_word = words[-1].replace("_", " ") if words else ""
        
        # Nếu đủ số câu hoặc gặp dấu chấm (kết thúc ý lớn), cắt chunk
        # or last_word.endswith(".")
        if sentence_count >= max_sentences_per_chunk :
            chunks.append(current_chunk.strip())
            current_chunk = ""
            sentence_count = 0
        
    # Thêm phần còn lại (nếu có)
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Lọc bỏ chunk rỗng
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
        
        txt_files = txt_files[:500]  # Giới hạn 500 file
        
        for txt_file in txt_files:
            file_path = os.path.join(directory_path, txt_file)
            text = extract_text_from_file(file_path)
           
            chunks = chunk_by_paragraphs(text)  
            all_texts.extend(chunks)
        
        if not all_texts:
            raise ValueError("Không có đoạn văn bản nào được tạo")
        
        # Tạo embeddings bằng sentence-transformers
        model = SentenceTransformer('keepitreal/vietnamese-sbert')
        embeddings = model.encode(all_texts, convert_to_numpy=True)
        
        # Tạo FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)  # Sử dụng L2 distance
        index.add(embeddings)
        
        # Lưu trữ văn bản gốc để truy xuất sau
        texts = all_texts
        return index, texts
    except Exception as e:
        raise Exception(f"Lỗi khi xử lý files: {str(e)}")

def query_llama(question, context):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2:1b",
        "prompt": f"""Bạn là một trợ lý AI chuyên trả lời câu hỏi dựa trên tài liệu được cung cấp. Hãy đọc kỹ nội dung sau, tìm kiếm thông tin liên quan đến câu hỏi, và trả lời chính xác bằng tiếng Việt. Nếu thông tin đầy đủ, hãy dựa và những thông tin, nội dung cung cấp để trả lời một cách dầy đủ, rõ ràng, diễn giải logic và tự nhiên nhất.

Nội dung:
{context}

Câu hỏi: {question}""",
        "stream": False,
        "max_tokens": 500,
        "temperature": 0.1
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise Exception(f"Ollama API error: {response.text}")
    return response.json()["response"]

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get("question")
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    if 'index' not in globals() or index is None or not texts:
        return jsonify({"error": "Index not initialized"}), 400
    
    try:
        # Tạo embedding cho câu hỏi
        model = SentenceTransformer('keepitreal/vietnamese-sbert')
        question_embedding = model.encode([preprocess_text_vietnamese(question)], convert_to_numpy=True)
        
        # Tìm kiếm k văn bản gần nhất
        k = 4
        distances, indices = index.search(question_embedding, k)
        relevant_texts = [texts[i] for i in indices[0]]
        context = " ".join(relevant_texts)
        print(f"Context for question '{question}':\n{context}")  # In context để kiểm tra

        # Gửi câu hỏi và context tới LLaMA
        answer = query_llama(question, context)
        print()
        print(f"ANSWER:{markdown.markdown(answer)}")
        return jsonify({"answer": answer}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    DATA_DIRECTORY = "./data"
    
    try:
        print("Đang xử lý các file txt...")
        index, texts = process_files(DATA_DIRECTORY)
        print("Xử lý hoàn tất, khởi động server...")
    except Exception as e:
        print(f"Lỗi khi khởi tạo: {str(e)}")
        exit(1)
    
    app.run(port=5000, debug=True)