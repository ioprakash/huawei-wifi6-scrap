import requests
import base64
import re
import csv
import time
import datetime
import os

URL = "http://192.168.100.1"
USER = "cgnet"
PASS = "Sp33d@987"
CSV_FILE = "ont_status.csv"

s = requests.Session()
s.cookies.set("Cookie", "body:Language:english:id=-1", domain="192.168.100.1")

def login():
    try:
        r_token = s.post(f"{URL}/asp/GetRandCount.asp", timeout=5)
        # Handle BOM and whitespace
        token = r_token.text.strip().replace('\ufeff', '')
        
        b64_pass = base64.b64encode(PASS.encode()).decode()
        
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
        
        r_login = s.post(f"{URL}/login.cgi", data=payload, headers=headers, timeout=10)
        
        # Check for success
        if "index.asp" in r_login.text or "frame" in r_login.text or "start.asp" in r_login.text:
            return True
        # If redirected to login page content, fail
        if 'type="password"' in r_login.text.lower():
            print("Login failed (returned login page)")
            return False
            
        return True
    except Exception as e:
        print(f"Login Error: {e}")
        return False

def fetch_device_info():
    data = {}
    try:
        r = s.get(f"{URL}/html/ssmp/deviceinfo/deviceinfo.asp", timeout=5)
        text = r.text
        # stDeviceInfo(domain,SerialNumber,HardwareVersion,SoftwareVersion,ModelName,VendorID,ReleaseTime,Mac,Description,ManufactureInfo,DeviceAlias)
        # Regex to find arguments:
        # new stDeviceInfo("...", "SN", "HW", "SW", "Model", "Vendor", "Release", "MAC", ...)
        match = re.search(r'new stDeviceInfo\((.*?)\)', text)
        if match:
            args = [x.strip().strip('"').replace(r'\x2d', '-').replace(r'\x3a', ':').replace(r'\x2e', '.').replace(r'\x20', ' ').replace(r'\x28', '(').replace(r'\x29', ')') for x in match.group(1).split(',')]
            # Note: args[0] is domain
            if len(args) > 8:
                data['SerialNumber'] = args[1]
                data['HardwareVersion'] = args[2]
                data['SoftwareVersion'] = args[3]
                data['ModelName'] = args[4]
                data['VendorID'] = args[5]
                data['ReleaseTime'] = args[6]
                data['MAC'] = args[7]
        
        # CPU/Mem
        # var cpuUsed = '14%';
        cpu = re.search(r"var cpuUsed = '(.*?)'", text)
        mem = re.search(r"var memUsed = '(.*?)'", text)
        if cpu: data['CPU'] = cpu.group(1)
        if mem: data['Memory'] = mem.group(1)
        
    except Exception as e:
        print(f"Error fetching Device Info: {e}")
        
    return data

def fetch_optical_info():
    data = {}
    try:
        r = s.get(f"{URL}/html/amp/opticinfo/opticinfo.asp", timeout=5)
        text = r.text
        # stOpticInfo(domain,LinkStatus,transOpticPower,revOpticPower,voltage,temperature,bias,rfRxPower,rfOutputPower, VendorName, VendorSN, DateCode, TxWaveLength, RxWaveLength, MaxTxDistance, LosStatus)
        # Note: arg count varies by CfgMode (see lines 58-97 in opticinfo.asp).
        # We just grab what we can.
        match = re.search(r'new stOpticInfo\((.*?)\)', text)
        if match:
            # Handle hex escapes like \x2d
            raw_args = match.group(1)
            # Simple split by comma might fail if strings contain commas, but usually these don't.
            # safe parsing:
            args = []
            for arg in raw_args.split(','):
                arg = arg.strip().strip('"')
                # Decode basic hex
                arg = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), arg)
                args.append(arg)
                
            if len(args) > 5:
                data['OpticLinkStatus'] = args[1]
                data['TxPower'] = args[2]
                data['RxPower'] = args[3]
                data['Voltage'] = args[4] # likely mV
                data['Temperature'] = args[5] # Celsius
                data['Bias'] = args[6] # mA?
    except Exception as e:
        print(f"Error fetching Optical Info: {e}")
    return data

def fetch_user_devices():
    devices = []
    try:
        # It's a POST request
        r = s.post(f"{URL}/html/bbsp/common/GetLanUserDevInfo.asp", timeout=5)
        text = r.text
        # The content usually contains UserDevices list
        # UserDevinfo = new Array(new USERDeviceNew(...), ...)
        matches = re.findall(r'new USERDevice(?:New)?\((.*?)\)', text)
        for m in matches:
             args = []
             for arg in m.split(','):
                arg = arg.strip().strip('"')
                arg = re.sub(r'\\x([0-9a-fA-F]{2})', lambda x: chr(int(x.group(1), 16)), arg)
                args.append(arg)
             
             # Both have at least 10 args we care about
             if len(args) >= 10:
                 # domain, ip, mac, port, iptype, devtype, status, porttype, time, hostname
                 devices.append({
                     "HostName": args[9],
                     "IP": args[1],
                     "MAC": args[2],
                     "Status": args[6],
                     "Port": args[3]
                 })
        if not devices:
             print("No devices found in GetLanUserDevInfo response.")
             with open("debug_user_dev.txt", "w", encoding="utf-8") as f:
                 f.write(text)
        
        # Dedup by MAC
        unique_devices = {}
        for d in devices:
            if d['MAC'] and d['MAC'] != '--':
                unique_devices[d['MAC']] = d
        
        return list(unique_devices.values())
             
    except Exception as e:
        print(f"Error fetching User Devices: {e}")
    return devices

def run_scraping_cycle():
    if not login():
        print("Login failed.")
        return

    print("Login successful. Scraping data...")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    dev_info = fetch_device_info()
    opt_info = fetch_optical_info()
    user_devs = fetch_user_devices()
    
    # Flatten data for CSV
    # Base fields
    row = {
        "Timestamp": timestamp,
        "Model": dev_info.get("ModelName", ""),
        "SN": dev_info.get("SerialNumber", ""),
        "MAC": dev_info.get("MAC", ""),
        "CPU": dev_info.get("CPU", ""),
        "Memory": dev_info.get("Memory", ""),
        "RxPower": opt_info.get("RxPower", ""),
        "TxPower": opt_info.get("TxPower", ""),
        "Temp": opt_info.get("Temperature", ""),
        "Voltage": opt_info.get("Voltage", ""),
        "DeviceCount": len(user_devs),
        "ConnectedDevices": "; ".join([f"{d['HostName']}({d['IP']})" for d in user_devs])
    }
    
    # Headers
    headers = ["Timestamp", "Model", "SN", "MAC", "CPU", "Memory", "RxPower", "TxPower", "Temp", "Voltage", "DeviceCount", "ConnectedDevices"]
    
    file_exists = os.path.isfile(CSV_FILE)
    
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
            
        print(f"Data saved to {CSV_FILE}")
        print("Row snippet:", {k: row[k] for k in row if k != 'ConnectedDevices'}) # print short summary
    except Exception as e:
        print(f"Error writing CSV: {e}")

def main():
    while True:
        try:
            print(f"\nStarting cycle at {datetime.datetime.now().strftime('%H:%M:%S')}")
            run_scraping_cycle()
        except Exception as e:
            print(f"Critical Error in loop: {e}")
        
        print("Waiting 1 minutes...")
        time.sleep(60)


if __name__ == "__main__":
    main()
