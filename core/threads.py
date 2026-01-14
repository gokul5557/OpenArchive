import search

def get_thread(message_id: str, org_id: int):
    """
    Finds all messages in the same conversation as message_id, scoped by org_id.
    """
    # 1. Get the starting message
    index = search.client.index('emails')
    try:
        doc = index.get_document(message_id)
        
        # Verify org
        doc_org_id = getattr(doc, 'org_id', None) or doc.get('org_id')
        if doc_org_id != org_id:
            return []

        # Attribute access for meilisearch client compatibility
        msg_id = getattr(doc, 'message_id', None) or doc.get('message_id')
        refs = getattr(doc, 'references', None) or doc.get('references')
        
        # Build filter query
        # We want all messages where (org_id match) AND (thread match)
        thread_filters = []
        if msg_id:
            mid_q = f'"{msg_id}"'
            thread_filters.append(f"message_id = {mid_q}")
            thread_filters.append(f"in_reply_to = {mid_q}")
            thread_filters.append(f"references = {mid_q}")
        
        if refs:
            for r in refs:
                rq = f'"{r}"'
                thread_filters.append(f"message_id = {rq}")
                thread_filters.append(f"references = {rq}")

        if not thread_filters:
            return [doc]

        combined_filter = f"(org_id = {org_id}) AND ({' OR '.join(thread_filters)})"
        
        # Search for everything in this thread
        results = search.search_documents(query="", filter_query=combined_filter, limit=100)
        
        # Sort by date
        hits = results.get('hits', [])
        hits.sort(key=lambda x: x.get('date') or 0)
        
        return hits

    except Exception as e:
        print(f"Error fetching thread: {e}")
        return []
