import requests
import base64
import re

URL = "http://192.168.100.1"
USER = "cgnet"
PASS = "Sp33d@987"

s = requests.Session()

def login():
    print(f"Attempting login to {URL}...")
    
    # 1. Get tokens/cookies
    try:
        r = s.get(URL, timeout=5)
    except Exception as e:
        print(f"Failed to reach device: {e}")
        return False
        
    # 2. Get Random Token
    try:
        r_token = s.post(f"{URL}/asp/GetRandCount.asp", timeout=5)
        # Check if it returned HTML instead of a clean token
        print(f"Token Resp Code: {r_token.status_code}")
        print(f"Token Resp Body (repr): {repr(r_token.text)}")
        token = r_token.text.strip()
        # Sometimes there's a BOM or hidden chars
        token = token.replace('\ufeff', '') 
    except Exception as e:
        print(f"Failed to get token: {e}")
        return False

    # 3. Encrypt Password (Base64)
    # Note: Javascript base64encode(plaintxt) usually maps to standard base64
    b64_pass = base64.b64encode(PASS.encode()).decode()
    
    # 4. Login
    payload = {
        "UserName": USER,
        "PassWord": b64_pass,
        "Language": "english",
        "x.X_HW_Token": token
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": f"{URL}/"
    }
    
    # Manually set the cookie that JS would set
    # var cookie2 = "Cookie=body:" + "Language:" + Language + ":" + "id=-1;path=/";
    # Result: Cookie=body:Language:english:id=-1
    s.cookies.set("Cookie", "body:Language:english:id=-1", domain="192.168.100.1")

    try:
        r_login = s.post(f"{URL}/login.cgi", data=payload, headers=headers, timeout=5)
        print(f"Login Resp Code: {r_login.status_code}")
        print("Login Resp Headers:", r_login.headers)
        print("Cookies after login:", s.cookies.get_dict())
        
        with open("login_response.html", "w", encoding="utf-8") as f:
            f.write(r_login.text)
            
        # Check success
        if "index.asp" in r_login.text or "start.asp" in r_login.text or "frame" in r_login.text:
             print("Login successful (found redirect/index).")
             return True
        else:
             print("Login might have failed (no index/start found).")
             return False
    except Exception as e:
        print(f"Login request failed: {e}")
        return False
        
def try_paths(s):
    # Common Huawei paths
    paths = [
        "/html/content.asp",
        "/asp/content.asp",
        "/html/ssmp/status/deviceinfo.asp",
        "/html/status/deviceinfo.asp",
        "/html/status/optical.asp",
        "/html/status/status_deviceinfo.asp",
        "/html/status/onu_info.asp",
        "/html/index.asp",
        "/index.asp"
    ]
    for p in paths:
        try:
            r = s.get(f"{URL}{p}", timeout=3)
            if r.status_code == 200 and "login.cgi" not in r.url and "login.asp" not in r.url:
                 # Check if it is the login page (has password input)
                 if 'type="password"' in r.text.lower() or 'id="txt_password"' in r.text.lower():
                     print(f"Path {p} seems to be the login page.")
                     continue
                 print(f"FOUND VALID PAGE: {p} (Size: {len(r.text)})")
                 return p
        except Exception as e:
            print(f"Error fetching {p}: {e}")
    return None

if login():
    found = try_paths(s)
    if found:
        print(f"To scrape: {found}")
else:
    print("Trying to access paths anyway (in case session works)...")
    try_paths(s)

