import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"Connecting to: {url}")

# 1. Ask the API for a list of all definitions (tables)
api_root = f"{url}/rest/v1/"
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

try:
    response = requests.get(api_root, headers=headers)
    
    if response.status_code == 200:
        definitions = response.json()
        print("\n[SUCCESS] CONNECTION ESTABLISHED")
        print("List of tables found by API:")
        print("-----------------------------------")
        
        found_designers = False
        
        # Check definitions
        if 'definitions' in definitions:
            for table_name in definitions['definitions'].keys():
                print(f" - {table_name}")
                if table_name == 'designers':
                    found_designers = True
        else:
            print("Raw response keys:")
            print(definitions.keys())

        print("-----------------------------------")
        if found_designers:
            print("[OK] 'designers' table FOUND.")
        else:
            print("[MISSING] 'designers' table NOT FOUND.")
            
    else:
        print(f"\n[ERROR] Status Code: {response.status_code}")
        print("Check your URL and API Key.")

except Exception as e:
    print(f"\n[CRITICAL ERROR]: {e}")