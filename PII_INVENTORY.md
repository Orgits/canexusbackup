# CA Nexus — PII Field Inventory

**Generated:** 2026-09-16
**Source:** All SQLAlchemy models in `app/modules/**/models.py`

---

## Sensitive PII Fields Requiring Encryption

### 1. Client Model (`app/modules/clients/models.py` — `Client`)

| Field | Type | Length | Description | Sensitivity |
|-------|------|--------|-------------|-------------|
| `pan` | String | 10 | Permanent Account Number (Income Tax) | **HIGH** — Financial identity |
| `gstin` | String | 15 | GST Identification Number | **HIGH** — Tax identity |
| `tan` | String | 10 | Tax Deduction Account Number | **HIGH** — Tax identity |
| `cin` | String | 21 | Corporate Identity Number | **HIGH** — Corporate identity |
| `din` | String | 8 | Director Identification Number | **HIGH** — Personal identity |
| `aadhaar` | String | 12 | Aadhaar Number (UIDAI) | **CRITICAL** — Biometric-linked identity |
| `passport` | String | 20 | Passport Number | **CRITICAL** — Travel identity |
| `other_ids` | JSONB | — | Other government IDs (flexible) | **HIGH** — May contain sensitive IDs |

### 2. ClientContact Model (`app/modules/clients/models.py` — `ClientContact`)

| Field | Type | Length | Description | Sensitivity |
|-------|------|--------|-------------|-------------|
| `email` | String | 255 | Contact email | **MEDIUM** — PII |
| `phone` | String | 20 | Contact phone | **MEDIUM** — PII |
| `mobile` | String | 20 | Contact mobile | **MEDIUM** — PII |

### 3. Firm Model (`app/modules/firms/models.py` — `Firm`)

| Field | Type | Length | Description | Sensitivity |
|-------|------|--------|-------------|-------------|
| `gstin` | String | 15 | Firm GSTIN | **HIGH** — Tax identity |
| `pan` | String | 10 | Firm PAN | **HIGH** — Financial identity |

### 4. TDS Models (`app/modules/tds/models.py`)

| Model | Field | Type | Length | Description | Sensitivity |
|-------|-------|------|--------|-------------|-------------|
| `TDSComplianceCycle` | `tan` | String | 20 | TAN for TDS cycle | **HIGH** |
| `TDSChallan` | `cin` | String | 50 | Challan Identification Number | **HIGH** — Payment reference |
| `TDSDeductee` | `deductee_pan` | String | 20 | Deductee PAN | **HIGH** — Financial identity |

### 5. User Model (`app/modules/users/models.py` — `User`)

| Field | Type | Length | Description | Sensitivity |
|-------|------|--------|-------------|-------------|
| `email` | String | 255 | User email | **MEDIUM** — PII |
| `phone` | String | 20 | User phone | **MEDIUM** — PII |
| `hashed_password` | String | 255 | Argon2 hash | **NOT PII** — Already hashed |

### 6. Billing Models (`app/modules/billing/models.py`)

| Model | Field | Type | Description | Sensitivity |
|-------|-------|------|-------------|-------------|
| `Payment` | `reference` | String | Payment reference (may contain bank ref) | **MEDIUM** |
| `Expense` | `receipt_url` | String | Receipt URL (may contain sensitive data) | **LOW** |

---

## Fields NOT Requiring Encryption (Already Protected)

| Field | Model | Reason |
|-------|-------|--------|
| `hashed_password` | User | Already Argon2 hashed |
| `tenant_id` | All tenant models | Not sensitive, used for isolation |
| `id`, `created_at`, `updated_at` | All models | Metadata, not PII |
| `status`, `category`, `priority` | Various | Business data, not identity |

---

## Encryption Strategy

### Algorithm: **Fernet (AES-128-GCM via cryptography library)**
- Authenticated encryption (confidentiality + integrity)
- Standard, well-audited implementation
- Key rotation support via multi-key Fernet
- No custom cryptography

### Key Management
- **Encryption key**: Externalized via `ENCRYPTION_KEY` environment variable
- **Key format**: Base64-encoded 32-byte key (Fernet compatible)
- **No key in Git**: `.env` in `.gitignore`, only `.env.example` committed
- **No key in logs**: Key never logged, only used in memory
- **Rotation strategy**: Multi-key Fernet supports key rotation; old keys retained for decryption, new key used for encryption

### Column Storage
- **Encrypted columns**: `LargeBinary` (stores Fernet token: version + timestamp + IV + ciphertext + HMAC)
- **Plaintext columns**: Retained for non-sensitive fields
- **Indexes**: Cannot index encrypted columns directly; use separate searchable hashes if needed (future enhancement)

---

## Migration Plan

### Phase 1: Add Encrypted Columns
1. Add new `_encrypted` columns (e.g., `pan_encrypted` LargeBinary)
2. Keep existing plaintext columns temporarily
3. Run migration to encrypt existing data

### Phase 2: Switch to Encrypted Columns
1. Update models to use encrypted columns as primary
2. Add property accessors for transparent encryption/decryption
3. Update repositories/services

### Phase 3: Remove Plaintext Columns
1. Drop plaintext columns after verification
2. Rename encrypted columns to original names (optional)

---

## Log Redaction Requirements

| Log Source | Fields to Redact | Method |
|------------|------------------|--------|
| SQLAlchemy echo (`echo=True`) | All PII columns | Disable echo in production; use parameterized queries |
| Structlog application logs | `pan`, `aadhaar`, `passport`, `gstin`, `tan`, `cin`, `din`, `deductee_pan` | Custom processor to mask values |
| Audit logs (`AuditLog.old_values`/`new_values`) | Same PII fields | Serialize with encryption or mask before storing |
| Exception traces | Request body PII fields | Custom exception handler to sanitize |
| API responses | Never return plaintext PII in list endpoints; detail endpoints return decrypted | Schema-level control |

---

## API Exposure Control

### List Endpoints (e.g., `GET /clients`)
- **Must NOT return**: `pan`, `aadhaar`, `passport`, `gstin`, `tan`, `cin`, `din`
- **Can return**: `name`, `display_name`, `category`, `status`, `email`, `phone` (non-sensitive contact)

### Detail Endpoints (e.g., `GET /clients/{id}`)
- **Return decrypted**: Authorized users with `CLIENTS_READ` permission
- **Audit**: Log access to sensitive fields

### Search/Filter Endpoints
- **Cannot search by encrypted fields directly** (limitation)
- **Workaround**: Client-side filtering after fetch, or add searchable hash columns (future)

---

## Acceptance Criteria Mapping

| Requirement | Implementation |
|-------------|----------------|
| Sensitive fields identified | This document |
| Sensitive fields encrypted | Fernet AES-128-GCM on identified columns |
| Raw DB does not expose plaintext | Encrypted columns store only ciphertext |
| Authorized API decrypts correctly | Property accessors in models |
| Encryption key externalized | `ENCRYPTION_KEY` env var, Base64-encoded |
| Logs/audits do not leak | Structlog processor + audit log masking |
| Key rotation strategy | Multi-key Fernet with key versioning |