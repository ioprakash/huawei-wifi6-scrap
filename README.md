# ONT Stress Test & Monitor Project

This project contains tools to stress test network connections and monitor a Huawei ONT device's status.

## Scripts

### 1. `cont-goo.py` - Stress Tester
- **Purpose**: Generates high concurrency traffic to stress test the network/NAT table.
- **Mechanism**: Uses `asyncio` to open ~15,000 concurrent connections to public endpoints (Google, Cloudflare, etc.) and downloads data chunks.
- **Usage**:
  ```bash
  python cont-goo.py
  ```

### 2. `ont_monitor.py` - status Monitor
- **Purpose**: Logs into the ONT at `192.168.100.1` and scrapes device health and connected client data.
- **Features**:
  - Auto-login with `cgnet` credentials.
  - Extracts Device Info (CPU, Mem, Temp), Optical Signal (Rx/Tx), and User Devices.
  - Continually runs every 2 minutes.
  - Saves data to `ont_status.csv`.
- **Usage**:
  ```bash
  python ont_monitor.py
  ```

## Output
- `ont_status.csv`: Log of ONT status snapshots.

## Requirements
- Python 3.8+
- `requests`
- `asyncio` (standard lib)
# huawei-wifi6-scrap
