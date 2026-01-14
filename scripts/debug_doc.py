from meilisearch import Client
import os
client = Client('http://localhost:7700', 'masterKey')
hits = client.index('emails').search('', {'limit': 1})['hits']
print(hits[0] if hits else "No hits")
