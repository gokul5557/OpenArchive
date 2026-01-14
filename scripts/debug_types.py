from meilisearch import Client
client = Client('http://localhost:7700', 'masterKey')
# Sort by newest
hits = client.index('emails').search('', {'limit': 200, 'sort': ['date_timestamp:desc']})['hits']

org_counts = {}
for h in hits:
    oid = h.get('org_id')
    key = f"{oid} ({type(oid)})"
    org_counts[key] = org_counts.get(key, 0) + 1

print("Org ID Distribution (Newest 200):")
for k, v in org_counts.items():
    print(f"{k}: {v}")

print("Sample domains:")
if hits:
    print(hits[0].get('domains'))
