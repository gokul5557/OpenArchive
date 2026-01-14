from meilisearch import Client
client = Client('http://localhost:7700', 'masterKey')
# Search for sagasoft
hits = client.index('emails').search('sagasoft', {'limit': 200})['hits']

print(f"Found {len(hits)} hits for 'sagasoft'")
if hits:
    sample = hits[0]
    print(f"Sample Org ID: {sample.get('org_id')}")
    print(f"Sample Domains: {sample.get('domains')}")
