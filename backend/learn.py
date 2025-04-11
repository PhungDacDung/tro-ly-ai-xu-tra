import os
import re
from pyvi import ViTokenizer
import requests
from bs4 import BeautifulSoup

texts = []

def preprocess_text_vietnamese(text):
    """Tiền xử lý văn bản tiếng Việt: tách từ bằng pyvi và chuẩn hóa."""
    # Tách từ bằng pyvi
    text = ViTokenizer.tokenize(text)
    # Có thể thêm các bước chuẩn hóa khác nếu cần (xóa ký tự đặc biệt, chuyển về chữ thường, v.v.)
    return text

def chunk_text(text):
    # Chia văn bản thành các chunk
    # step = chunk_size - overlap  # Bước nhảy = độ dài chunk - overlap
    # chunks = [text[i:i+chunk_size] for i in range(0, len(text), step)]
    # return chunks
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def chunk_by_semantics(text):
    # Bước 1: Tách câu thủ công dựa trên dấu câu
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    
    for sentence in sentences:
        # Nếu câu quá ngắn, thêm trực tiếp vào chunks
        if len(sentence) < 50:  # Ngưỡng độ dài tối thiểu (tùy chỉnh)
            chunks.append(sentence)
            continue
        
        # Bước 2: Tách từ bằng pyvi
        tokenized = ViTokenizer.tokenize(sentence)
        words = tokenized.split()  # Tách thành danh sách từ
        current_chunk = ""
        separators = [",", "và", "nhưng", "vì", ".", ";"]  # Từ nối hoặc dấu câu
        
        for word in words:
            # Chuyển từ ghép về dạng có khoảng trắng (loại bỏ "_")
            word_display = word.replace("_", " ")
            current_chunk += word_display + " "
            
            # Nếu gặp từ nối hoặc dấu câu, cắt chunk
            if any(sep in word for sep in separators):
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        # Thêm phần còn lại (nếu có)
        if current_chunk:
            chunks.append(current_chunk.strip())
    
    # Lọc bỏ chunk rỗng
    chunks = [chunk for chunk in chunks if chunk]
    return chunks

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

def chunk_by_topic(text):
    # Tách câu
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current_chunk = ""
    current_topic = None

    # Từ khóa và tiêu chí phân loại chủ đề
    topic_keywords = {
        "mo_ta_tra": ["trà Thái Nguyên", "thưởng thức", "tiền vị", "hậu vị", "dư vị", "ngọt hậu", "hương cốm"],
        "quy_trinh": ["Bước", "phơi héo", "diệt men", "vò chè", "sao khô", "quay hương", "đóng gói"],

    }

    for sentence in sentences:
        tokenized = ViTokenizer.tokenize(sentence)
        words = tokenized.split()

        # Xác định chủ đề dựa trên từ khóa
        new_topic = None
        for topic, keywords in topic_keywords.items():
            if any(keyword in sentence for keyword in keywords):
                new_topic = topic
                break

        # Nếu chuyển sang chủ đề mới và đã có nội dung trong chunk hiện tại
        if new_topic and new_topic != current_topic and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
            current_topic = new_topic
        else:
            # Thêm câu vào chunk hiện tại
            current_chunk += sentence + " "
            if new_topic:
                current_topic = new_topic

    # Thêm chunk cuối cùng (nếu có)
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def chunk_by_semantics(text):
    # Tách thành các câu
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current_chunk = ""
    sentence_count = 0
    target_sentences=2
    max_sentences=4
    
    # Từ khóa chuyển ý (có thể tùy chỉnh theo tài liệu)
    transition_keywords = ["và", "nhưng", "vì", "sau đó", "tiếp theo", "cuối cùng"]
    
    for i, sentence in enumerate(sentences):
        current_chunk += sentence + " "
        sentence_count += 1
        
        # Tách từ để kiểm tra từ khóa
        tokenized = ViTokenizer.tokenize(sentence)
        words = tokenized.split()
        last_word = words[-1].replace("_", " ") if words else ""
        
        # Kiểm tra ranh giới ý nghĩa
        is_transition = any(kw in sentence.lower() for kw in transition_keywords)
        is_end_of_thought = last_word.endswith(".") and not sentences[i].strip().startswith(("(", "+"))
        
        # Cắt chunk nếu:
        # - Đủ 3-4 câu và không phải giữa ý quan trọng
        # - Gặp dấu chấm kết thúc ý lớn và đã có ít nhất 2 câu
        if (sentence_count >= target_sentences and not is_transition) or \
           (sentence_count >= max_sentences) or \
           (is_end_of_thought and sentence_count >= 2):
            chunks.append(current_chunk.strip())
            current_chunk = ""
            sentence_count = 0
    
    # Thêm phần còn lại (nếu có)
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Lọc bỏ chunk rỗng
    return [chunk for chunk in chunks if chunk]

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


            
            # Chia thành chunks
            # chunks = chunk_text(preprocess_text_vietnamese(text))
            # chunks = chunk_by_semantics(text)
            chunks = chunk_by_paragraphs(text)
            
            # In kết quả chunking
            print(f"Tổng số chunks: {len(chunks)}")
            for i, chunk in enumerate(chunks):
                print(f"CHUNK {i+1}: '{chunk}' (ĐỘ DÀI: {len(chunk)} ký tự)")
                print()

    except Exception as e:
        print(f"Lỗi: {str(e)}")

# Thư mục data
folder_path = "data_test"
process_files_in_folder(folder_path)

# Hàm crawl dữ liệu từ một URL
def crawl_data(url):
    """Crawl tiêu đề và nội dung từ một URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Không thể truy cập {url}. Mã trạng thái: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, "html.parser")
        # Lấy tiêu đề, nếu không có thì dùng giá trị mặc định
        title = soup.find("title").get_text(strip=True) if soup.find("title") else "Khong_tim_thay_tieu_de"
        print(f"Tiêu đề của {url}: {title}")
        
        # Lấy nội dung từ các thẻ <p>
        # paragraphs = soup.find_all("p")

            # Lấy nội dung chính (có thể cần tinh chỉnh)
        content_div = soup.find("div", class_="entry-content")  # Lớp chứa nội dung bài viết
        paragraphs = content_div.find_all("p") if content_div else []
        content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        if not content:
            print(f"Không tìm thấy nội dung trong thẻ <p> tại {url}. Kiểm tra cấu trúc HTML.")
            return None
        
        return {"title": title, "content": content}
    
    except requests.RequestException as e:
        print(f"Đã xảy ra lỗi khi crawl {url}: {e}")
        return None
url = "https://thainguyen.gov.vn/vung-tra/-/asset_publisher/L0n17VJXU23O/content/cac-vung-tra-thai-nguyen-ngon-noi-tieng"

# print(crawl_data(url))