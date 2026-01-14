import database
import search
from typing import Dict, Any

async def get_org_analytics(org_id: int) -> Dict[str, Any]:
    """Returns analytics data for a specific organization."""
    conn = await database.get_db_connection()
    try:
        # 1. Total Messages
        stats = search.get_stats(filter_query=f"org_id = {org_id}")
        total_messages = stats.get('total_emails', 0)
        
        # 2. Total Holds
        holds = await conn.fetchval("SELECT COUNT(*) FROM legal_holds WHERE org_id = $1 AND active = TRUE", org_id)
        
        # 3. Held Items
        held_items = await conn.fetchval(
            "SELECT COUNT(i.id) FROM legal_hold_items i JOIN legal_holds h ON i.hold_id = h.id WHERE h.org_id = $1", 
            org_id
        )
        
        # 4. Storage Estimates (Simplified)
        # In a real system, we'd sum the 'size' field from Meilisearch
        # Meilisearch doesn't support sum() directly yet, so we'd need to aggregate or track in DB.
        # For MVP, we'll return a placeholder or sum some samples.
        total_size_bytes = total_messages * 50000 # 50KB average estimate
        
        # 5. Domain Breakdown
        # We can fetch categories if we had them.
        
        return {
            "total_messages": total_messages,
            "active_holds": holds,
            "held_items": held_items,
            "storage_volume_bytes": total_size_bytes,
            "hold_ratio": (held_items / total_messages) if total_messages > 0 else 0
        }
    finally:
        await conn.close()
