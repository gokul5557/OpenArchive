OpenArchive Architecture: Data & Security Flow
1. High-Level Architecture
This diagram illustrates the connection between the Mail Server Environment (Edge) and the Central Archive (Core).

Central Core (OpenArchive)
Edge Node (Mail Server)
Backend Services
Sidecar Agent
SMTP (StartTLS) :2525
Extract
Strip
Check Hash
Upload HTTPS
Auth
Index
Store
Prune
Verify
HTTPS
Stalwart / Postfix
Sidecar Agent
SMTP Handler
SQLite Buffer
Attachment Extractor
CAS Blob Store
Email Skeleton
Sync Process
FastAPI Core :8000
Nginx Reverse Proxy :443
Background Workers
PostgreSQL
MeiliSearch
MinIO Object Store
Admin / Compliance Officer
2. Detailed Data Flow (The Lifecycle of an Email)
Step 1: Ingestion (Edge)
Arrival: An email arrives at the Mail Server (Stalwart).
Journaling: Stalwart sends a blind copy (BCC) to the local Sidecar Agent on Port 2525.
Security Handshake: The connection is secured via STARTTLS to prevent local sniffing.
Step 2: Processing (Agent)
Parsing: The Agent parses the raw email bytes.
Deduplication (CAS):
Attachments are extracted.
SHA-256 Hash is calculated.
Attachment is saved to a separate "CAS Buffer".
Email body is replaced with a reference: [CAS_REF: sha256...].
Buffering: The email "Skeleton" and the "CAS Blob" are saved to buffer.db (SQLite) to ensure no data loss if the network is down.
Step 3: Synchronization (Transit)
Hash Check: The Sync Worker asks Core: "Do you already have file Hash X?"
Upload:
If No: The CAS Blob is uploaded (Secure HTTPS).
If Yes: Upload is skipped (Bandwidth & Storage Saving).
Encryption: The Core Server receives the raw data and encrypts it using AES-256-GCM before writing to disk.
Step 4: Storage & Indexing (Core)
MinIO: Stores the Encrypted .enc blobs (WORM compliant).
MeiliSearch: Indexes metadata (Subject, Sender, Body Text) for millisecond-speed searching.
PostgreSQL:
Audit: Records "Email Ingested" event with a Cryptographic Hash Chain.
Integrity: Stores the SHA-256 of the encrypted blob to detect future tampering.
3. Security Flow (The "Unbreakable" Chain)
Layer	Security Mechanism	Status
Transport (Agent -> Core)	TLS 1.3 (HTTPS)	✅ Active
Transport (Localhost)	STARTTLS	✅ Active
Data at Rest (MinIO)	AES-256-GCM (Authenticated Encryption)	✅ Active
Tamper Protection	Merkle-like Hash Chain (Audit Logs)	✅ Active
Access Control	Role-Based (RBAC) + Row Level Security (RLS)	✅ Active
4. Multi-Node Scaling
You can run 100s of Agents across different regions.

They all push to the same Central Core.
Deduplication works globally: If Agent A uploads a PDF, Agent B will skip uploading it 5 minutes later.
# OpenArchive
