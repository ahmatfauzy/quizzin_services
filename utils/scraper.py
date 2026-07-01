import requests
import time
from pymongo import MongoClient
from config.settings import settings

def scrape_world_bank_literacy():
    print("[SCRAPER] Starting World Bank Literacy scraping...")
    indicator = 'SE.ADT.LITR.ZS' # Indikator Literasi Dunia
    date_range = '1970:2025'     # Rentang waktu historis
    per_page = 5000              # Jumlah data per request (max)
    
    all_records = []
    page = 1
    
    while True:
        url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&date={date_range}&per_page={per_page}&page={page}"
        try:
            response = requests.get(url)
            json_data = response.json()
            
            # Validasi jika data kosong atau habis
            if len(json_data) < 2 or not json_data[1]:
                break
                
            records = json_data[1]
            for rec in records:
                all_records.append({
                    'indicator_id': rec['indicator']['id'],
                    'indicator_value': rec['indicator']['value'],
                    'country_id': rec['country']['id'],
                    'country_name': rec['country']['value'],
                    'countryiso3code': rec['countryiso3code'],
                    'year': rec['date'],
                    'value': rec['value'],
                    'unit': rec['unit'],
                    'obs_status': rec['obs_status'],
                    'decimal': rec['decimal']
                })
            print(f"[SCRAPER] Berhasil mengambil halaman {page}...")
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"[SCRAPER] Terjadi kesalahan pada halaman {page}: {e}")
            break

    if not all_records:
        print("[SCRAPER] No records fetched. Aborting database operation.")
        return

    print(f"[SCRAPER] Fetched {len(all_records)} records. Saving to MongoDB...")
    
    if not settings.MONGODB_URL:
        print("[SCRAPER] MONGODB_URL is not set. Cannot save data.")
        return
        
    try:
        from pymongo import UpdateOne
        client = MongoClient(settings.MONGODB_URL)
        db = client.latihanbigdata
        collection = db.sampledata
        
        # Menggunakan bulk_write dengan opsi upsert agar tidak ada duplikasi data
        operations = []
        for record in all_records:
            # Data dianggap unik berdasarkan kombinasi indicator_id, country_id, dan year
            filter_query = {
                'indicator_id': record['indicator_id'],
                'country_id': record['country_id'],
                'year': record['year']
            }
            operations.append(
                UpdateOne(filter_query, {'$set': record}, upsert=True)
            )
            
        if operations:
            result = collection.bulk_write(operations)
            print(f"[SCRAPER] Data berhasil di-upsert ke MongoDB! (Inserted: {result.upserted_count}, Modified: {result.modified_count})")
    except Exception as e:
        print(f"[SCRAPER] Error connecting or saving to MongoDB: {e}")
