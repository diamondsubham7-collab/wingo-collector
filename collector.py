import requests
import json
import pandas as pd
import time
import os
from datetime import datetime
import threading
from flask import Flask

# ---------- FLASK KEEP-ALIVE ----------
app = Flask(__name__)

@app.route('/')
def home():
    return "🔄 Auto-Collector is running!"

# ---------- CONFIG ----------
GAMES = [
    {"name": "WinGo_30S", "url": "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"},
    {"name": "WinGo_1M", "url": "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"},
    {"name": "WinGo_3M", "url": "https://draw.ar-lottery01.com/WinGo/WinGo_3M/GetHistoryIssuePage.json"}
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://draw.ar-lottery01.com/',
    'Origin': 'https://draw.ar-lottery01.com',
    'Connection': 'keep-alive'
}

# ---------- FETCH FUNCTION ----------
def fetch_data(game_url, limit=500):
    params = {
        'ts': int(time.time() * 1000),
        'language': 'en',
        'pageSize': limit
    }
    
    for attempt in range(3):
        try:
            response = requests.get(game_url, params=params, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and isinstance(data['data'], dict):
                    return data['data'].get('list', [])
        except:
            pass
        time.sleep(0.5)
    return []

# ---------- SAVE WITH DUPLICATE CHECK ----------
def save_data(game_name, records):
    if not records:
        return
    
    master_file = f'wingo_{game_name}_master.csv'
    df_new = pd.DataFrame(records)
    df_new['issueNumber'] = df_new['issueNumber'].astype(str)
    
    if os.path.exists(master_file):
        df_existing = pd.read_csv(master_file)
        df_existing['issueNumber'] = df_existing['issueNumber'].astype(str)
        combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=['issueNumber']).reset_index(drop=True)
        combined.to_csv(master_file, index=False)
        print(f"📊 {game_name}: {len(combined)} records (New: {len(df_new)})")
    else:
        df_new.to_csv(master_file, index=False)
        print(f"📊 {game_name}: {len(df_new)} records (New file)")

# ---------- COLLECT ALL ----------
def collect_all():
    print(f"\n🔄 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for game in GAMES:
        records = fetch_data(game['url'])
        if records:
            save_data(game['name'], records)
        time.sleep(1)

# ---------- SCHEDULED LOOP ----------
def scheduled_collect(interval_minutes=30):
    print("🚀 Auto-Collector Started (Render)")
    print(f"⏰ Interval: {interval_minutes} minutes")
    while True:
        try:
            collect_all()
            print(f"⏳ Next in {interval_minutes} min...")
            time.sleep(interval_minutes * 60)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

# ---------- RUN ----------
if __name__ == "__main__":
    # Keep-alive in background
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    scheduled_collect(30)  # Har 30 minute mein collect