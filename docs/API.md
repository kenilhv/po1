# PayCrew — Backend API Specification

> **For:** Backend developer integrating with the PayCrew React frontend  
> **Base URL:** `https://api.paycrew.example.com/v1` (configure via `VITE_API_BASE_URL`)  
> **Auth:** Bearer token returned from login (stored in frontend as `paycrew_auth`)

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [AP Dashboard](#2-ap-dashboard)
3. [CFO Dashboard](#3-cfo-dashboard)
4. [Invoice Upload & Processing](#4-invoice-upload--processing)
5. [WebSocket — Live Agent Trace](#5-websocket--live-agent-trace)
6. [Shared Data Models](#6-shared-data-models)
7. [Error Responses](#7-error-responses)
8. [Frontend → Endpoint Map](#8-frontend--endpoint-map)

---

## 1. Authentication

### `POST /auth/login`

Validate access code and return session token + role.

**Request**
```json
{
  "code": "AP2024"
}
```

**Response `200`**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "role": "ap",
  "expiresAt": "2026-06-17T15:00:00Z"
}
```

| Code | Role |
|------|------|
| `AP2024` | `ap` |
| `CFO2024` | `cfo` |

**Response `401`**
```json
{
  "error": "INVALID_CODE",
  "message": "Invalid code. Try again."
}
```

---

### `POST /auth/logout`

Invalidate session token.

**Headers:** `Authorization: Bearer <token>`

**Response `204`** — no body

---

### `GET /auth/me`

Verify current session (used on protected route load).

**Headers:** `Authorization: Bearer <token>`

**Response `200`**
```json
{
  "role": "ap"
}
```

---

## 2. AP Dashboard

All AP routes require `Authorization: Bearer <token>` and role `ap`.

### `GET /ap/stats`

Dashboard stat cards.

**Response `200`**
```json
{
  "total": 47,
  "autoApproved": 38,
  "flagged": 7,
  "blocked": 2
}
```

---

### `GET /ap/invoices`

List invoices with optional risk filter.

**Query params**

| Param | Type | Values |
|-------|------|--------|
| `risk` | string | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` (omit for all) |
| `page` | number | default `1` |
| `limit` | number | default `50` |

**Response `200`**
```json
{
  "invoices": [ /* Invoice[] — see §6 */ ],
  "total": 8,
  "page": 1,
  "limit": 50
}
```

---

### `GET /ap/invoices/:id`

Single invoice with full agent trace.

**Response `200`** — `Invoice` object (see §6)

**Response `404`**
```json
{ "error": "NOT_FOUND", "message": "Invoice not found" }
```

---

### `GET /ap/decisions`

Agent decisions panel (grouped by risk level).

**Response `200`**
```json
{
  "low": {
    "count": 4,
    "recent": ["INV-2024-443", "INV-2024-444"]
  },
  "medium": {
    "count": 2,
    "recent": ["INV-2024-445", "INV-2024-446"]
  },
  "high": {
    "count": 1,
    "recent": ["INV-2024-447"]
  },
  "critical": {
    "count": 1,
    "recent": ["INV-2024-448"]
  }
}
```

> **Note:** Frontend currently derives this from the invoice list. A dedicated endpoint is optional but recommended for performance at scale.

---

## 3. CFO Dashboard

All CFO routes require `Authorization: Bearer <token>` and role `cfo`.

### `GET /cfo/stats`

**Response `200`**
```json
{
  "totalProcessed": 47,
  "autoApproved": 38,
  "pendingApproval": 2,
  "totalSaved": 46200
}
```

---

### `GET /cfo/invoices`

Same as `GET /ap/invoices` — CFO sees all invoices.

**Query params:** same as AP (`risk`, `page`, `limit`)

**Response `200`:** same shape as AP invoices list

---

### `GET /cfo/invoices/:id`

Same as AP single invoice endpoint.

---

### `GET /cfo/pending-approvals`

Invoices requiring CFO action.

**Response `200`**
```json
{
  "pending": [
    {
      "id": "8",
      "number": "INV-2024-448",
      "vendor": "FastConsult LLC",
      "amount": 45000,
      "risk": "CRITICAL",
      "status": "Pending CFO Approval",
      "timestamp": "2024-06-14T17:00:00Z",
      "riskReasons": ["No PO found", "Unknown vendor", "Suspicious bank details"],
      "evidence": "Vendor FastConsult LLC registered 14 days ago. Bank account ACC-999 flagged in fraud database. No purchase order on file. Invoice amount 12x above vendor average.",
      "agents": [ /* AgentResult[] */ ]
    }
  ],
  "count": 2
}
```

**Filter logic:** status in `["Pending CFO Approval", "Escalated"]`

---

### `POST /cfo/invoices/:id/approve`

CFO approves a pending invoice.

**Request**
```json
{}
```

**Response `200`**
```json
{
  "invoice": {
    "id": "8",
    "number": "INV-2024-448",
    "status": "Approved",
    "approvedBy": "CFO",
    "approvedAt": "2026-06-16T15:30:00Z"
  },
  "auditEntry": {
    "id": "a-new-1",
    "timestamp": "2026-06-16T15:30:00Z",
    "invoice": "INV-2024-448",
    "agent": "CFO Review",
    "decision": "Approved",
    "model": "—",
    "confidence": null,
    "approvedBy": "CFO"
  }
}
```

**Response `409`** — invoice not in pending state

---

### `POST /cfo/invoices/:id/reject`

CFO rejects a pending invoice.

**Request**
```json
{
  "reason": "Suspicious vendor — do not pay"
}
```

`reason` is optional.

**Response `200`**
```json
{
  "invoice": {
    "id": "8",
    "number": "INV-2024-448",
    "status": "Rejected",
    "rejectedBy": "CFO",
    "rejectedAt": "2026-06-16T15:30:00Z",
    "rejectionReason": "Suspicious vendor — do not pay"
  },
  "auditEntry": {
    "id": "a-new-2",
    "timestamp": "2026-06-16T15:30:00Z",
    "invoice": "INV-2024-448",
    "agent": "CFO Review",
    "decision": "Rejected: Suspicious vendor — do not pay",
    "model": "—",
    "confidence": null,
    "approvedBy": "CFO"
  }
}
```

---

### `GET /cfo/audit-log`

Audit trail table (newest first).

**Query params**

| Param | Type | Default |
|-------|------|---------|
| `page` | number | `1` |
| `limit` | number | `50` |
| `invoice` | string | filter by invoice number |

**Response `200`**
```json
{
  "entries": [ /* AuditEntry[] — see §6 */ ],
  "total": 15,
  "page": 1,
  "limit": 50
}
```

---

### `GET /cfo/audit-log/export`

CSV download of audit trail.

**Query params:** same filters as audit log

**Response `200`**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="paycrew-audit-trail.csv"`

**CSV columns:** `Timestamp, Invoice #, Agent, Decision, Model, Confidence, Approved By`

---

## 4. Invoice Upload & Processing

### `POST /ap/invoices/upload`

Upload PDF and start agent pipeline.

**Headers**
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Body**
```
file: <PDF binary>
```

**Response `202 Accepted`** — processing started asynchronously
```json
{
  "jobId": "job_abc123",
  "invoiceId": "9",
  "status": "processing"
}
```

**Response `400`** — wrong file type
```json
{
  "error": "INVALID_FILE_TYPE",
  "message": "Please upload a PDF file"
}
```

---

### `GET /ap/invoices/jobs/:jobId`

Poll processing status (fallback if WebSocket unavailable).

**Response `200` — processing**
```json
{
  "jobId": "job_abc123",
  "status": "processing",
  "currentAgent": "PO Matcher",
  "completedAgents": 2,
  "totalAgents": 6
}
```

**Response `200` — complete**
```json
{
  "jobId": "job_abc123",
  "status": "complete",
  "invoice": { /* full Invoice object */ }
}
```

**Response `200` — failed**
```json
{
  "jobId": "job_abc123",
  "status": "failed",
  "error": "Failed to parse PDF"
}
```

---

## 5. WebSocket — Live Agent Trace

Replaces frontend `useSimulatedTrace` hook during upload.

### Connect

```
wss://api.paycrew.example.com/v1/ws?token=<JWT>
```

### Subscribe to job

**Client → Server**
```json
{
  "type": "subscribe",
  "jobId": "job_abc123"
}
```

### Agent step events (streamed sequentially)

**Server → Client** — one event per agent (~600ms apart)

```json
{
  "type": "agent_start",
  "jobId": "job_abc123",
  "agent": {
    "id": "parser",
    "name": "Invoice Parser"
  },
  "index": 0
}
```

```json
{
  "type": "agent_complete",
  "jobId": "job_abc123",
  "agent": {
    "id": "parser",
    "name": "Invoice Parser",
    "result": "Extracted: OfficeSupplyCo, $800, INV-441",
    "confidence": 99,
    "model": "gpt-3.5-turbo",
    "status": "pass"
  },
  "index": 0
}
```

**Agent status values:** `pass` | `fail` | `warn` | `route`

### Pipeline complete

```json
{
  "type": "job_complete",
  "jobId": "job_abc123",
  "invoice": { /* full Invoice object */ },
  "risk": "LOW",
  "decision": "Auto Approved"
}
```

### Error

```json
{
  "type": "error",
  "jobId": "job_abc123",
  "message": "Processing failed"
}
```

---

## 6. Shared Data Models

### Invoice

```typescript
interface Invoice {
  id: string;
  number: string;           // "INV-2024-441"
  vendor: string;
  amount: number;           // USD, no cents in display
  risk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status:
    | "Auto Approved"
    | "Flagged"
    | "Escalated"
    | "Pending CFO Approval"
    | "Approved"
    | "Rejected";
  timestamp: string;        // ISO 8601
  fileName?: string;        // present on uploaded invoices
  riskReasons?: string[];   // CFO pending cards only
  evidence?: string;        // CFO pending cards only
  agents: AgentResult[];
}
```

### AgentResult

```typescript
interface AgentResult {
  agent: string;            // "Invoice Parser", "PO Matcher", etc.
  result: string;
  confidence: number | null;
  model: string;            // "gpt-3.5-turbo", "gpt-4o"
  status: "pass" | "fail" | "warn" | "route";
}
```

**Agent order (always 6):**
1. Invoice Parser
2. PO Matcher
3. Duplicate Detector
4. Fraud Signal
5. Risk Scorer
6. Approval Router

### AuditEntry

```typescript
interface AuditEntry {
  id: string;
  timestamp: string;        // ISO 8601
  invoice: string;          // invoice number
  agent: string;
  decision: string;
  model: string;
  confidence: number | null;
  approvedBy: "System" | "CFO" | "—";
}
```

---

## 7. Error Responses

Standard error shape:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable message"
}
```

| HTTP | Code | When |
|------|------|------|
| 400 | `INVALID_FILE_TYPE` | Non-PDF upload |
| 401 | `UNAUTHORIZED` | Missing/invalid token |
| 403 | `FORBIDDEN` | Wrong role for endpoint |
| 404 | `NOT_FOUND` | Invoice/job not found |
| 409 | `INVALID_STATE` | Approve/reject on non-pending invoice |
| 422 | `VALIDATION_ERROR` | Bad request body |
| 500 | `INTERNAL_ERROR` | Server error |

---

## 8. Frontend → Endpoint Map

| UI Feature | Current (mock) | Backend endpoint |
|------------|----------------|------------------|
| Login code entry | `ACCESS_CODES` in mockData | `POST /auth/login` |
| Change User / logout | `localStorage.removeItem` | `POST /auth/logout` |
| Route protection | `localStorage` role check | `GET /auth/me` |
| AP stat cards | `apStats` constant | `GET /ap/stats` |
| AP invoice list + filters | `initialInvoices` state | `GET /ap/invoices?risk=` |
| Expand invoice → agent trace | `invoice.agents` array | `GET /ap/invoices/:id` |
| AP decisions panel | derived from invoices | `GET /ap/decisions` (optional) |
| Upload PDF | `generateUploadInvoice()` | `POST /ap/invoices/upload` |
| Live agent animation | `useSimulatedTrace` hook | WebSocket `subscribe` + events |
| CFO stat cards | `cfoStats` constant | `GET /cfo/stats` |
| CFO pending banner + cards | filter `status` | `GET /cfo/pending-approvals` |
| Approve modal confirm | local state update | `POST /cfo/invoices/:id/approve` |
| Reject modal confirm | local state update | `POST /cfo/invoices/:id/reject` |
| Audit trail table | `initialAuditLog` state | `GET /cfo/audit-log` |
| Export CSV button | client-side CSV gen | `GET /cfo/audit-log/export` |
| Landing page | static, no API | none |

---

## Environment Variables (Frontend)

```env
VITE_API_BASE_URL=https://api.paycrew.example.com/v1
VITE_WS_URL=wss://api.paycrew.example.com/v1/ws
```

---

## Suggested Implementation Order

1. `POST /auth/login` + `GET /auth/me`
2. `GET /ap/invoices` + `GET /cfo/invoices` (seed with 8 mock invoices)
3. `GET /ap/stats` + `GET /cfo/stats`
4. `GET /cfo/pending-approvals` + approve/reject endpoints
5. `GET /cfo/audit-log` + export
6. `POST /ap/invoices/upload` + WebSocket agent trace

---

## Seed Data Reference

The frontend mock data lives in `src/data/mockData.js` — use it as the canonical seed dataset for invoices and audit log entries during development.
