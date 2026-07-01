from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URL"))
db = client.latihanbigdata
collection = db.sampledata

distinct_countries = len(collection.distinct("country_id"))
distinct_years = len(collection.distinct("year"))

print(f"Distinct countries: {distinct_countries}")
print(f"Distinct years: {distinct_years}")
print(f"Expected max data: {distinct_countries * distinct_years}")
print(f"Actual total documents: {collection.count_documents({})}")
