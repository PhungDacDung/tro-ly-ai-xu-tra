import requests
from bs4 import BeautifulSoup
import os
import re
from unidecode import unidecode

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
        paragraphs = soup.find_all("p")
        content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        if not content:
            print(f"Không tìm thấy nội dung trong thẻ <p> tại {url}. Kiểm tra cấu trúc HTML.")
            return None
        
        return {"title": title, "content": content}
    
    except requests.RequestException as e:
        print(f"Đã xảy ra lỗi khi crawl {url}: {e}")
        return None

# Hàm tạo tên file từ tiêu đề
def create_filename_from_title(title, folder="data"):
    """Tạo tên file từ tiêu đề, xử lý trùng lặp bằng cách thêm số thứ tự."""
    # Chuẩn hóa tiêu đề
    clean_title = unidecode(title)  # Bỏ dấu tiếng Việt
    clean_title = re.sub(r'[<>:"/\\|?*]', '', clean_title)  # Loại ký tự không hợp lệ
    clean_title = re.sub(r'\s+', '_', clean_title.strip())  # Thay khoảng trắng bằng '_'
    clean_title = clean_title[:100] if len(clean_title) > 100 else clean_title  # Giới hạn độ dài
    
    # Tạo đường dẫn file
    base_filename = clean_title
    filename = f"{base_filename}.txt"
    file_path = os.path.join(folder, filename)
    
    # Xử lý trùng lặp
    counter = 1
    while os.path.exists(file_path):
        filename = f"{base_filename}_{counter}.txt"
        file_path = os.path.join(folder, filename)
        counter += 1
    
    return file_path

# Hàm lưu dữ liệu vào file
def save_to_file(data, url, folder="data"):
    """Lưu dữ liệu crawl được vào file dựa trên tiêu đề."""
    if not data or "title" not in data or not data["title"] or "content" not in data:
        print(f"Không có dữ liệu hợp lệ để lưu từ {url}.")
        return
    
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Đã tạo thư mục: {folder}")
    
    # Tạo tên file từ tiêu đề
    file_path = create_filename_from_title(data["title"], folder)
    
    # Ghi dữ liệu vào file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Tiêu đề: {data['title']}\n\n")
            f.write(f"Nội dung:\n{data['content']}")
        print(f"Dữ liệu từ {url} đã được lưu vào {file_path}")
    except IOError as e:
        print(f"Lỗi khi lưu file {file_path}: {e}")

# Hàm crawl nhiều trang
def crawl_multiple_pages(urls, folder="data"):
    """Crawl dữ liệu từ danh sách URL và lưu vào file."""
    for url in urls:
        print(f"\nBắt đầu crawl: {url}")
        data = crawl_data(url)
        if data:
            save_to_file(data, url, folder)

# Danh sách URL cần crawl
urls = [
    "https://vov.vn/van-hoa/di-san/net-van-hoa-tra-tai-thai-nguyen-911218.vov",
    "https://tuoitrethudo.vn/ky-3-van-hoa-tra-thai-net-dep-di-san-quoc-gia-251535.html",
    "https://loctancuong.com/lich-su-phat-trien-cua-cay-tra-thai-nguyen/",
    "https://luhanhvietnam.com.vn/du-lich/khong-gian-van-hoa-tra-tan-cuong-thai-nguyen.html",
    "https://thainguyen.gov.vn/van-hoa-tra/-/asset_publisher/L0n17VJXU23O/content/thai-nguyen-phat-trien-du-lich-gan-voi-san-pham-tra-va-van-hoa-tra?inheritRedirect=true",
    "https://trathainguyen.net.vn/bat-mi-ve-nguon-goc-lich-su-cua-tra-thai-nguyen-ngon-nhat-bid4804.html#:~:text=Kh%E1%BB%9Fi%20ngu%E1%BB%93n%20c%E1%BB%A7a%20tr%C3%A0%20Th%C3%A1i%20Nguy%C3%AAn%3A,-Tr%C3%A0%20Th%C3%A1i%20Nguy%C3%AAn&text=Ngu%E1%BB%93n%20g%E1%BB%91c%20c%E1%BB%A7a%20tr%C3%A0%20Th%C3%A1i,bi%E1%BB%87t%20th%C6%A1m%20ngon%2C%20thanh%20tao.",
    "https://thainguyen.gov.vn/vung-tra/-/asset_publisher/L0n17VJXU23O/content/tim-hieu-ve-vung-tra-thai-nguyen?inheritRedirect=true&utm_source=chatgpt.com",
    "https://tancuongxanh.vn/tra-thai-nguyen-la-gi?srsltid=AfmBOooKU4LrUuzaVsAqXxLASystm7sk0f4n3F-71kGDsqWnK3YLqwNN&utm_source=chatgpt.com",
    "https://khuyennongvn.gov.vn/khoa-hoc-cong-nghe/khcn-trong-nuoc/quy-trinh-san-xuat-va-che-bien-che-thai-nguyen-22866.html",
    "https://vietcotra.vn/van-hoa-tra/nguon-goc-tra-thai-nguyen-c8a239.html?srsltid=AfmBOopq7hVfr49XFHtY3MAxrtcw2ADeJucny2_hOFnJijgMdweCb8aI",
    "",
]

# Thực thi crawl nhiều trang
if __name__ == "__main__":
    crawl_multiple_pages(urls, folder="data")