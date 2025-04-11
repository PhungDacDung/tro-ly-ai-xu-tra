from sentence_transformers import SentenceTransformer
from pyvi import ViTokenizer  # Thay underthesea bằng pyvi
import numpy as np
from langchain_core.documents import Document
import os

# Hàm tính khoảng cách cosine
def cosine_distance(vec1, vec2):
    return 1 - np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# Hàm Semantic Splitting với pyvi
def semantic_splitting_vietnamese(text):
    threshold=0.2 
    chunk_size_limit=500
    # Tách câu và tách từ tiếng Việt bằng pyvi
    sentences = [ViTokenizer.tokenize(s.strip()) for s in text.split('.') if s.strip()]
    
    # Tải mô hình vietnamese-sbert
    model = SentenceTransformer('keepitreal/vietnamese-sbert')
    
    # Tạo embedding
    embeddings = model.encode(sentences, show_progress_bar=False, batch_size=16)
    
    # Tính khoảng cách giữa các embedding liên tiếp
    distances = [cosine_distance(embeddings[i], embeddings[i+1]) 
                 for i in range(len(embeddings)-1)]
    
    # Xác định điểm ngắt dựa trên ngưỡng
    breakpoints = [i for i, dist in enumerate(distances) if dist > threshold]
    
    # Chia thành các chunk
    chunks = []
    start_idx = 0
    for bp in breakpoints:
        chunk_sentences = sentences[start_idx:bp+1]
        chunk_text = " ".join(chunk_sentences)
        if len(chunk_text) <= chunk_size_limit:
            chunks.append(chunk_text)
        start_idx = bp + 1
    
    # Thêm chunk cuối cùng
    if start_idx < len(sentences):
        chunk_text = " ".join(sentences[start_idx:])
        if len(chunk_text) <= chunk_size_limit:
            chunks.append(chunk_text)
    
    # Trả về định dạng Document của LangChain
    return [Document(page_content=chunk) for chunk in chunks]


def process_files_in_folder(folder_path):
    try:
        # Lấy danh sách file .txt trong thư mục
        txt_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.txt')]
        if not txt_files:
            print("Không tìm thấy file .txt nào trong thư mục 'data'")
            return
        
        # Xử lý từng file
        for txt_file in txt_files:
            file_path = os.path.join(folder_path, txt_file)
            print(f"\nĐang xử lý file: {txt_file}")
            
            # Đọc nội dung file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            if not text:
                print(f"File {txt_file} rỗng, bỏ qua.")
                continue

            chunks = semantic_splitting_vietnamese(text)
            
            # In kết quả chunking
            print(f"Tổng số chunks: {len(chunks)}")
            for i, chunk in enumerate(chunks):
                print(f"CHUNK {i+1}: '{chunk.page_content}' (ĐỘ DÀI: {len(chunk.page_content)} ký tự)")
            print()

    except Exception as e:
        print(f"Lỗi: {str(e)}")

folder_path = "data_test"  # Thay bằng đường dẫn thư mục chứa file .txt của bạn
process_files_in_folder(folder_path)