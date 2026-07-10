import requests
import json
import pandas as pd
import time
import os
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home():
    return "🔄 Auto-Collector is running! (Historical Bulk Mode)"

# ---------- CONFIG ----------
GAMES = [
    {"name": "WinGo_30S", "url": "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"},
    {"name": "WinGo_1M", "url": "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"},
    {"name": "WinGo_3M", "url": "https://draw.ar-lottery01.com/WinGo/WinGo_3M/GetHistoryIssuePage.json"}
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://draw.ar-lottery01.com/',
    'Origin': 'https://draw.ar-lottery01.com'
}

# ---------- FETCH WITH PAGE (BULK) ----------
def fetch_page(game_url, page, limit=50):
    params = {
        'ts': int(time.time() * 1000),
        'language': 'en',
        'pageSize': limit,
        'page': page
    }
    try:
        r = requests.get(game_url, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get('data', {}).get('list', [])
    except:
        pass
    return []

def bulk_collect_history(game_name, game_url, target=50000):
    """Parallel threads se 50k records collect karega"""
    print(f"\n🔥 Bulk Collect: {game_name}")
    all_records = []
    batch_size = 50
    max_pages = 2000  # 2000 * 50 = 100k max (safety)
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_page, game_url, p, batch_size): p for p in range(1, max_pages + 1)}
        
        for future in as_completed(futures):
            if len(all_records) >= target:
                break
            try:
                records = future.result()
                if records:
                    all_records.extend(records)
                    print(f"   {game_name}: Page {futures[future]} | +{len(records)} (Total: {len(all_records)})")
            except:
                pass
    
    # Save to master
    if all_records:
        df = pd.DataFrame(all_records)
        df['issueNumber'] = df['issueNumber'].astype(str)
        df.drop_duplicates(subset=['issueNumber'], inplace=True)
        df.to_csv(f'wingo_{game_name}_master.csv', index=False)
        print(f"✅ {game_name}: {len(df)} records saved!")
    return all_records

# ---------- SCHEDULED UPDATE (NEW RECORDS) ----------
def fetch_latest(game_url, limit=100):
    params = {'ts': int(time.time()*1000), 'language': 'en', 'pageSize': limit}
    try:
        r = requests.get(game_url, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get('data', {}).get('list', [])
    except:
        pass
    return []

def update_master(game_name):
    master_file = f'wingo_{game_name}_master.csv'
    if not os.path.exists(master_file):
        return
    
    new_records = fetch_latest(GAMES[[g['name'] for g in GAMES].index(game_name)]['url'])
    if not new_records:
        return
    
    df_new = pd.DataFrame(new_records)
    df_new['issueNumber'] = df_new['issueNumber'].astype(str)
    df_old = pd.read_csv(master_file)
    df_old['issueNumber'] = df_old['issueNumber'].astype(str)
    
    combined = pd.concat([df_old, df_new]).drop_duplicates(subset=['issueNumber']).reset_index(drop=True)
    combined.to_csv(master_file, index=False)
    print(f"📊 {game_name} updated: {len(combined)} records")

def scheduled_updates():
    while True:
        try:
            print(f"\n🔄 Update cycle: {datetime.now().strftime('%H:%M:%S')}")
            for game in GAMES:
                update_master(game['name'])
                time.sleep(2)
            print(f"⏳ Next update in 15 min...")
            time.sleep(900)  # 15 minutes
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

# ---------- MAIN ----------
if __name__ == "__main__":
    # Step 1: Bulk Collect History (Ek baar chalega)
    print("🚀 STARTING HISTORICAL BULK COLLECTION...")
    for game in GAMES:
        bulk_collect_history(game['name'], game['url'], target=50000)
    
    print("\n✅ HISTORY COLLECTION COMPLETE!")
    print("🔄 Now starting scheduled updates (every 15 min)...")
    
    # Step 2: Keep Flask alive & Start scheduler
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    scheduled_updates()
