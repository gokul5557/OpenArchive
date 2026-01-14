import meilisearch
import os

MEILI_HOST = "http://localhost:7700"
MEILI_KEY = "masterKey"

try:
    client = meilisearch.Client(MEILI_HOST, MEILI_KEY)
    index = client.index('emails')
    # Use one of the known IDs from the previous log
    doc_id = "a2a83104-39a4-4c95-8d7d-a65a5e109978"
    
    print(f"Fetching {doc_id}...")
    doc = index.get_document(doc_id)
    
    print(f"Type: {type(doc)}")
    print(f"Dir: {dir(doc)}")
    
    if isinstance(doc, dict):
        print("It is a DICT")
        print(doc.get('key'))
    else:
        print("It is NOT a DICT")
        try:
            print(f"doc.key: {doc.key}")
        except:
            pass
        try:
            print(f"doc['key']: {doc['key']}")
        except:
            pass
            
except Exception as e:
    print(f"Error: {e}")
