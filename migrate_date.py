import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Use Supabase's built-in SQL endpoint with service_role key
url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# First, create the exec_sql function (one-time setup)
# We'll use a different approach - directly call the pg endpoint
print("Attempting to change 'date' column from timestamp -> date...")
print()

# Use Supabase's pg-meta API to modify the column
pg_meta_url = f"{SUPABASE_URL}/pg/query"
headers_pg = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

sql = "ALTER TABLE complaints_detail ALTER COLUMN date TYPE date USING date::date;"

response = requests.post(
    pg_meta_url,
    headers=headers_pg,
    json={"query": sql}
)

if response.status_code == 200:
    print("SUCCESS! Column 'date' changed from timestamp -> date")
    print("Now it will store only YYYY-MM-DD (no time, no 00:00:00)")
else:
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    print("If this failed, please run this SQL manually in the Supabase SQL Editor:")
    print("  ALTER TABLE complaints_detail ALTER COLUMN date TYPE date USING date::date;")
