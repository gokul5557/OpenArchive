import meilisearch
import os

MEILI_HOST = os.getenv("MEILI_HOST", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

client = meilisearch.Client(MEILI_HOST, MEILI_KEY)

def ensure_index():
    index = client.index('emails')
    try:
        client.get_index('emails')
    except:
        client.create_index('emails', {'primaryKey': 'id'})
    
    # Always update settings to ensure they are current
    index.update_filterable_attributes(['id', 'to', 'from', 'date', 'date_timestamp', 'org_id', 'tenant_id', 'domains', 'has_attachments', 'is_spam', 'sender_domain', 'recipient_domains', 'message_id', 'in_reply_to', 'references', 'attachment_content', 'sha256', 'signature', 'envelope_from', 'envelope_rcpt', 'sender_email', 'recipient_emails'])
    index.update_searchable_attributes(['subject', 'from', 'to', 'attachment_content', 'id', 'sha256'])
    index.update_sortable_attributes(['date', 'date_timestamp'])
    index.update_pagination_settings({'maxTotalHits': 1000000})

def index_documents(documents):
    ensure_index()
    try:
        index = client.index('emails')
        task = index.add_documents(documents)
        return task
    except Exception as e:
        print(f"Error indexing documents: {e}")
        return None

def search_documents(query: str, limit: int = 20, filter_query: str = None, offset: int = 0):
    ensure_index()
    try:
        index = client.index('emails')
        search_params = {
            'limit': limit,
            'offset': offset,
            'sort': ['date_timestamp:desc'], # Default sort by newest
            'attributesToHighlight': ['subject', 'from', 'to', 'attachment_content'],
            'highlightPreTag': '<mark>',
            'highlightPostTag': '</mark>'
        }
        
        if filter_query:
            search_params['filter'] = filter_query
            
        return index.search(query, search_params)
    except Exception as e:
        print(f"Error searching documents: {e}")
        return {'hits': []}

def get_stats(filter_query: str = None):
    ensure_index()
    try:
        index = client.index('emails')
        if filter_query:
            # Perform a search with limit=0 to get count
            res = index.search('', {'filter': filter_query, 'limit': 0})
            return {'total_emails': res.get('estimatedTotalHits', 0)}
        else:
            stats = index.get_stats()
            return {'total_emails': stats.number_of_documents}
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {'total_emails': 0}
