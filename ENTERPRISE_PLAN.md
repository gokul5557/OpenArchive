# Enterprise Enhancements Plan: Phase 1

This document outlines the immediate technical strategy for upgrading OpenArchive to enterprise-grade functionality.

## 1. Feature Roadmap & Scope

| Feature | Objective | Implementation Strategy |
| :--- | :--- | :--- |
| **Tamper-Proof Audit Logs** | Audit Fidelity | Ensure audit logs are signed and chained. If a row is deleted or modified, the chain breaks. |
| **PII Detection & Redaction** | Data Privacy | Implement a scanner to identify SSNs, Credit Cards, and emails. Allow auditors to apply redaction masks during review. |
| **Advanced Legal Holds** | Granular Compliance | Support complex `filter_criteria` (keywords in body, date ranges, attachment types) instead of just "Sender/Recipient". |
| **Global Search Hits** | Auditor Experience | Implement hit-highlighting in results so auditors see *why* a message matched (snippet generation). |
| **Retention Engine** | Lifecycle Management | Fully automate the cleanup of expired messages based on per-organization retention policies. |
| **Advanced Analytics** | Decision Support | Build a dashboard showing data growth trends and hold-to-total-archive ratios. |

## 2. Technical Decisions

- **Audit Fidelity**: I will use a simple "Hash Chain" approach. Every audit log entry will contain a `last_hash` and a `current_hash`. The `current_hash` is `HMAC(id + action + details + timestamp + last_hash)`.
- **Advanced Holds**: I will update `core/admin.py` to translate `filter_criteria` into complex Meilisearch filter strings (e.g., `(sender = X) AND (date > Y)`).
- **PII Detection**: I'll add a helper in `core/redaction.py` using Regex patterns initially, and potentially a lightweight NLP library if needed later.

## 3. What is a "Direct Cloud Connector"?

You asked why we'd need this. 
Currently, we rely on an **SMTP Agent** (the sidecar). This means the mail server (like Postfix) must be configured to "forward" or "bcc" every email to us via SMTP. 

**The Problem**: Many companies don't want to manage local SMTP configurations.
**The Solution (Connector)**: Instead of the SMTP Agent, the Core API connects directly to **Microsoft Graph API** or **Google Workspace API**. It "logs in" with an admin token and "pulls" the mail. It's easier for the customer to set up, more reliable, and doesn't require "intercepting" mail flow.

*I will not implement connectors in this phase as per your request to focus on the others.*

## 4. Execution Plan

1.  **Branch**: `feat/enterprise-enhancements` (Active)
2.  **Order of Work**:
    - Audit Chaining (Security Foundation)
    - Advanced Legal Hold logic (Compliance Core)
    - PII Detection & UI Redaction (Privacy)
    - Global Search Highlighting (UI/UX)
    - Retention Engine Automation (Lifecycle)
    - Analytics Dashboard (Reporting)
