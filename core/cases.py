from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import database
import json
import uuid
import exports

router = APIRouter()

# --- Models ---
class CaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    created_by: str = 'auditor'

class CaseUpdate(BaseModel):
    status: str

class CaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    item_count: int = 0

class AddToCaseRequest(BaseModel):
    case_id: int
    message_ids: List[str]
    added_by: str = 'auditor'

class TagUpdate(BaseModel):
    tags: List[str]

class ExportRequest(BaseModel):
    format: str = "native"
    redact: bool = False

class BatchAssignRequest(BaseModel):
    item_ids: List[int]
    assignee_id: int

class StatusUpdate(BaseModel):
    status: str # 'PENDING', 'IN_REVIEW', 'COMPLETED'

# --- Endpoints ---

@router.get("", response_model=List[CaseResponse])
async def list_cases(org_id: int):
    conn = await database.get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT c.*, COUNT(ci.id) as item_count 
            FROM cases c 
            LEFT JOIN case_items ci ON c.id = ci.case_id 
            WHERE c.org_id = $1
            GROUP BY c.id 
            ORDER BY c.created_at DESC
        """, org_id)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@router.post("", response_model=CaseResponse)
async def create_case(case: CaseCreate, org_id: int):
    conn = await database.get_db_connection()
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO cases (org_id, name, description, created_by)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, description, status, created_at
            """,
            org_id, case.name, case.description, case.created_by
        )
        return {**dict(row), "item_count": 0}
    finally:
        await conn.close()

# --- Specialized Item Routes (Literal segments) ---

@router.post("/items/batch-assign")
async def batch_assign_items(payload: BatchAssignRequest, org_id: int):
    conn = await database.get_db_connection()
    try:
        # Verify all items belong to a case in the same org
        check = await conn.fetchval("""
            SELECT 1 FROM case_items ci 
            JOIN cases c ON ci.case_id = c.id 
            WHERE ci.id = ANY($1) AND c.org_id != $2
        """, payload.item_ids, org_id)
        
        if check:
            raise HTTPException(status_code=403, detail="Some items do not belong to your organization")

        await conn.execute(
            "UPDATE case_items SET assignee_id = $1 WHERE id = ANY($2)",
            payload.assignee_id, payload.item_ids
        )
        return {"status": "assigned", "count": len(payload.item_ids)}
    finally:
        await conn.close()

@router.get("/assignments/{user_id}")
async def list_assignments(user_id: int):
    conn = await database.get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT ci.*, c.name as case_name 
            FROM case_items ci 
            JOIN cases c ON ci.case_id = c.id 
            WHERE ci.assignee_id = $1 
            ORDER BY ci.added_at DESC
        """, user_id)
        return [
            {
                **dict(r),
                "tags": json.loads(r['tags'])
            } for r in rows
        ]
    finally:
        await conn.close()

@router.put("/items/{item_id}/tags")
async def update_item_tags(item_id: int, payload: TagUpdate):
    conn = await database.get_db_connection()
    try:
        await conn.execute(
            "UPDATE case_items SET tags = $1 WHERE id = $2",
            json.dumps(payload.tags), item_id
        )
        return {"status": "updated"}
    finally:
        await conn.close()

@router.put("/items/{item_id}/status")
async def update_item_status(item_id: int, payload: StatusUpdate):
    conn = await database.get_db_connection()
    try:
        await conn.execute(
            "UPDATE case_items SET review_status = $1 WHERE id = $2",
            payload.status, item_id
        )
        return {"status": "updated"}
    finally:
        await conn.close()

@router.delete("/items/{item_id}")
async def remove_item_from_case(item_id: int):
    conn = await database.get_db_connection()
    try:
        exists = await conn.fetchval("SELECT 1 FROM case_items WHERE id = $1", item_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Item not found")
            
        await conn.execute("DELETE FROM case_items WHERE id = $1", item_id)
        return {"status": "removed", "id": item_id}
    finally:
        await conn.close()

# --- Parameterized Case Routes ---

@router.get("/{case_id}")
async def get_case(case_id: int, org_id: int):
    conn = await database.get_db_connection()
    try:
        case = await conn.fetchrow("SELECT * FROM cases WHERE id = $1 AND org_id = $2", case_id, org_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        items = await conn.fetch("""
            SELECT ci.*, u.username as assignee_name 
            FROM case_items ci 
            LEFT JOIN users u ON ci.assignee_id = u.id 
            WHERE ci.case_id = $1 
            ORDER BY ci.added_at DESC
        """, case_id)
        
        return {
            "case": dict(case),
            "items": [
                {
                    **dict(i), 
                    "tags": json.loads(i['tags'])
                } for i in items
            ]
        }
    finally:
        await conn.close()

@router.post("/{case_id}/items")
async def add_items_to_case(case_id: int, payload: AddToCaseRequest, org_id: int):
    conn = await database.get_db_connection()
    try:
        # Verify case org
        case_check = await conn.fetchval("SELECT 1 FROM cases WHERE id = $1 AND org_id = $2", case_id, org_id)
        if not case_check:
            raise HTTPException(status_code=403, detail="Target case does not belong to your organization")

        params = []
        for mid in payload.message_ids:
            params.append((case_id, mid, payload.added_by))
            
        await conn.executemany(
            """
            INSERT INTO case_items (case_id, message_id, added_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (case_id, message_id) DO NOTHING
            """,
            params
        )
        return {"status": "added", "count": len(payload.message_ids)}
    finally:
        await conn.close()

@router.post("/{case_id}/export")
async def export_case(case_id: int, org_id: int, background_tasks: BackgroundTasks, payload: ExportRequest = Body(...)):
    conn = await database.get_db_connection()
    try:
        case = await conn.fetchrow("SELECT name FROM cases WHERE id = $1 AND org_id = $2", case_id, org_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        items = await conn.fetch("SELECT message_id FROM case_items WHERE case_id = $1", case_id)
        if not items:
            raise HTTPException(status_code=400, detail="Case has no items to export")
            
        item_list = [{"message_id": i['message_id']} for i in items]
        job_id = str(uuid.uuid4())
        
        # Run synchronously to ensure zip is ready before response returns (prevents 0-byte race condition)
        await exports.create_export_job(job_id, item_list, payload.format, payload.redact)
        
        return {
            "status": "processing",
            "job_id": job_id,
            "message": "Export started in background.",
            "download_url": f"/api/v1/downloads/{job_id}.zip"
        }
    finally:
        await conn.close()

@router.delete("/{case_id}")
async def delete_case(case_id: int, org_id: int):
    conn = await database.get_db_connection()
    try:
        exists = await conn.fetchval("SELECT 1 FROM cases WHERE id = $1 AND org_id = $2", case_id, org_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Case not found")
            
        await conn.execute("DELETE FROM cases WHERE id = $1 AND org_id = $2", case_id, org_id)
        return {"status": "deleted", "id": case_id}
    finally:
        await conn.close()
