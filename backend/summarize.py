import requests
import os

# Đường dẫn thư mục
input_folder = "./data"
output_folder = "./output"

# Tạo thư mục đầu ra nếu chưa tồn tại
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# URL API Ollama
api_url = "http://localhost:11434/api/generate"

# Hàm gửi yêu cầu viết lại tới Ollama
def rewrite_text(text, model="llama3.2:1b"):
    prompt = (
        "Viết lại nội dung sau đây về trà Thái Nguyên, giữ lại toàn bộ thông tin chính liên quan đến đặc điểm, "
        "quy trình sản xuất, và giá trị văn hóa của trà. Loại bỏ hoàn toàn các thông tin thừa như số điện thoại, "
        "email, địa chỉ, lượt truy cập, quảng cáo, thông tin cơ quan, và các chi tiết không liên quan đến trà. "
        "Nội dung cần rõ ràng, tự nhiên, và đầy đủ chi tiết:\n\n" + text
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        return response.json()["response"]
    else:
        raise Exception(f"API request failed with status code {response.status_code}")

# Xử lý từng file .txt
for filename in os.listdir(input_folder):
    if filename.endswith(".txt"):
        input_path = os.path.join(input_folder, filename)
        
        # Đọc nội dung file
        with open(input_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Gửi yêu cầu viết lại
        try:
            rewritten_content = rewrite_text(content)
            print(f"Nội dung viết lại của {filename}:\n{rewritten_content}")
            
            # Lưu nội dung viết lại
            output_filename = f"rewritten_{filename}"
            output_path = os.path.join(output_folder, output_filename)
            with open(output_path, "w", encoding="utf-8") as output_file:
                output_file.write(rewritten_content)
            print(f"Đã lưu nội dung vào {output_path}")
        
        except Exception as e:
            print(f"Lỗi khi xử lý {filename}: {e}")

print("Hoàn tất quá trình viết lại!")