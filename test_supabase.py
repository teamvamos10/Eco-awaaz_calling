import os
from datetime import date
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("URL:", SUPABASE_URL)
print("KEY starts with:", SUPABASE_KEY[:10] if SUPABASE_KEY else None)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    response = supabase.table('complaints_detail').insert({
        "postal_code": "123456",
        "address": "test address",
        "resource_type": "water",
        "complaint_type": "TEST_ISSUE",
        "status": "PENDING",
        "date": date.today().isoformat()  # Only date, no time (YYYY-MM-DD)
    }).execute()
    print("SUCCESS! Data inserted:")
    print(response.data)
except Exception as e:
    print("FAILED with error:")
    print(e)
