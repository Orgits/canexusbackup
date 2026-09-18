# CA Nexus — Phase 5 Requirement Mapping

**Source**: CA_Nexus_Master_PRD_TRD_SOW-2.docx (Part D.1 Unified Delivery Phases, Table 22)
**Phase 5 Definition**: "Reporting, Search & Enterprise Hardening"
- **Backend Scope**: Reporting/analytics domain with a read replica and materialized views; advanced automation; full OpenSearch rollout; DPDP data-residency/consent workflow; zone-redundant HA; disaster-recovery drill.
- **Frontend Scope**: Reports landing and detail screens; advanced analytics; payment and authorized external integrations; profitability intelligence; mobile refinement.

---

## Requirement Mapping

### 1. Analytics & Reporting Domain

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Report Definitions (CRUD) | ReportDefinition | ✅ | ✅ | ✅ | ✅ | REPORT_READ/CREATE/UPDATE/DELETE | tenant_id + RLS | ✅ | — | — | ✅ |
| Report Filters & Parameters | ReportParameter | ✅ | ✅ | ✅ | ✅ | REPORT_READ | tenant_id + RLS | — | — | — | ✅ |
| Report Generation Jobs | ReportJob | ✅ | ✅ | ✅ | ✅ | REPORT_GENERATE | tenant_id + RLS | ✅ | Celery (reporting queue) | — | ✅ |
| Report Output/Results | ReportOutput | ✅ | ✅ | ✅ | ✅ | REPORT_READ | tenant_id + RLS | ✅ | — | Azure Blob (storage) | ✅ |
| Scheduled Reports | ReportSchedule | ✅ | ✅ | ✅ | ✅ | REPORT_SCHEDULE_READ/CREATE/UPDATE/DELETE | tenant_id + RLS | ✅ | Celery Beat | — | ✅ |
| Dashboard Widgets/Metrics | DashboardWidget | ✅ | ✅ | ✅ | ✅ | ANALYTICS_READ | tenant_id + RLS | — | — | — | ✅ |
| Materialized Views (Profitability, Productivity) | — (DB views) | ✅ (SQL) | — | ✅ | ✅ | ANALYTICS_READ | tenant_id + RLS | — | pg_cron / Celery | Read Replica | ✅ |

### 2. Asynchronous Report Generation

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Job Queue & Status | ReportJob (extends) | ✅ | ✅ | ✅ | ✅ | REPORT_GENERATE | tenant_id + RLS | ✅ | Celery (reporting queue) | — | ✅ |
| Idempotency Keys | ReportJob.idempotency_key | ✅ | ✅ | ✅ | ✅ | — | tenant_id + RLS | — | ✅ | — | ✅ |
| Retry & Timeout Handling | ReportJob.retry_count | ✅ | ✅ | ✅ | ✅ | — | tenant_id + RLS | — | Celery retry policy | — | ✅ |
| Result Persistence | ReportOutput | ✅ | ✅ | ✅ | ✅ | REPORT_READ | tenant_id + RLS | ✅ | — | Azure Blob | ✅ |
| Failure/Dead Letter | ReportJob.status=FAILED/DLQ | ✅ | ✅ | ✅ | ✅ | — | tenant_id + RLS | ✅ | Celery DLQ | — | ✅ |
| Progress Tracking | ReportJob.progress | ✅ | ✅ | ✅ | ✅ | — | tenant_id + RLS | — | WebSocket/SSE | — | ✅ |

### 3. Global Search (OpenSearch)

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Search API (Global) | — | — | — | SearchService | ✅ | SEARCH_GLOBAL | tenant-partitioned indices | ✅ | — | OpenSearch | ✅ |
| Indexable Entities | — | — | — | IndexerService | — | — | tenant_id in doc | — | Celery (indexing queue) | OpenSearch | ✅ |
| Document Indexing | — | — | — | IndexerService | — | — | documents-{tenant_id} | — | Outbox → Indexer | OpenSearch | ✅ |
| Communication Indexing | — | — | — | IndexerService | — | — | communications-{tenant_id} | — | Outbox → Indexer | OpenSearch | ✅ |
| Filtering & Facets | — | — | — | SearchService | ✅ | SEARCH_GLOBAL | tenant-partitioned | — | — | OpenSearch | ✅ |
| Pagination & Ranking | — | — | — | SearchService | ✅ | — | tenant-partitioned | — | — | OpenSearch | ✅ |
| Stale Index Handling | — | — | — | IndexerService | — | — | tenant-partitioned | — | Reindex job | OpenSearch | ✅ |
| Deletion Propagation | — | — | — | IndexerService | — | — | tenant-partitioned | ✅ | Outbox → Indexer | OpenSearch | ✅ |

### 4. DPDP Workflows (Data Protection)

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Data Access Requests | DataAccessRequest | ✅ | ✅ | ✅ | ✅ | DPDP_ACCESS_READ/CREATE | tenant_id + RLS | ✅ | — | — | ✅ |
| Data Correction Requests | DataCorrectionRequest | ✅ | ✅ | ✅ | ✅ | DPDP_CORRECTION_READ/CREATE/UPDATE | tenant_id + RLS | ✅ | — | — | ✅ |
| Data Erasure Requests | DataErasureRequest | ✅ | ✅ | ✅ | ✅ | DPDP_ERASURE_READ/CREATE/EXECUTE | tenant_id + RLS | ✅ | Celery (erasure queue) | Cross-system (12B) | ✅ |
| Consent Management | ConsentRecord (Phase 3) | ✅ | ✅ | ✅ | ✅ | CONSENT_* | tenant_id + RLS | ✅ | — | — | ✅ |
| Retention Policies | RetentionPolicy | ✅ | ✅ | ✅ | ✅ | RETENTION_READ/CREATE/UPDATE/DELETE | tenant_id + RLS | ✅ | Celery (retention queue) | — | ✅ |
| Retention Execution | RetentionExecution | ✅ | ✅ | ✅ | ✅ | RETENTION_EXECUTE | tenant_id + RLS | ✅ | Celery (retention queue) | — | ✅ |
| Data Residency Tracking | DataResidencyRecord | ✅ | ✅ | ✅ | ✅ | DPDP_RESIDENCY_READ | tenant_id + RLS | ✅ | — | — | ✅ |

### 5. Data Access Workflow

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Access Request Creation | DataAccessRequest | ✅ | ✅ | ✅ | ✅ | DPDP_ACCESS_CREATE | tenant_id + RLS | ✅ | — | — | ✅ |
| Scope Validation | — | — | — | DataAccessService | ✅ | — | tenant_id + RLS | — | — | — | ✅ |
| Data Compilation | — | — | — | DataAccessService | — | — | tenant_id + RLS | ✅ | Celery (export queue) | Azure Blob | ✅ |
| Delivery & Expiry | DataAccessRequest.delivered_at | ✅ | ✅ | ✅ | ✅ | — | tenant_id + RLS | ✅ | — | — | ✅ |

### 6. Data Correction Workflow

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Correction Request | DataCorrectionRequest | ✅ | ✅ | ✅ | ✅ | DPDP_CORRECTION_CREATE | tenant_id + RLS | ✅ | — | — | ✅ |
| Validation & Approval | — | — | — | DataCorrectionService | ✅ | DPDP_CORRECTION_APPROVE | tenant_id + RLS | ✅ | — | — | ✅ |
| Change Application | — | — | — | DataCorrectionService | — | — | tenant_id + RLS | ✅ | Transaction | — | ✅ |
| Previous/Current Tracking | DataCorrectionRequest.old/new_value | ✅ | ✅ | ✅ | ✅ | — | tenant_id + RLS | ✅ | — | — | ✅ |

### 7. Data Erasure Workflow (Application Level)

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Erasure Request | DataErasureRequest | ✅ | ✅ | ✅ | ✅ | DPDP_ERASURE_CREATE | tenant_id + RLS | ✅ | — | — | ✅ |
| Validation & Scope | — | — | — | DataErasureService | ✅ | DPDP_ERASURE_APPROVE | tenant_id + RLS | ✅ | — | — | ✅ |
| Orchestration | — | — | — | DataErasureService | — | — | tenant_id + RLS | ✅ | Celery (erasure queue) | — | ✅ |
| Status Tracking | DataErasureRequest.status | ✅ | ✅ | ✅ | ✅ | DPDP_ERASURE_READ | tenant_id + RLS | ✅ | — | — | ✅ |
| Cross-System (12B) | DataErasureRequest.external_refs | ✅ | ✅ | ✅ | — | — | tenant_id + RLS | ✅ | — | Webhook/Callback | ✅ |

### 8. Retention

| Requirement | Model | Migration | Repository | Service | API | Permission | Tenant Isolation | Audit Trail | Background Processing | External Integration | Tests |
|-------------|-------|-----------|------------|---------|-----|------------|------------------|-------------|----------------------|---------------------|-------|
| Retention Rules | RetentionPolicy | ✅ | ✅ | ✅ | ✅ | RETENTION_* | tenant_id + RLS | ✅ | — | — | ✅ |
| Retention Metadata | Document.retention_* (existing) | ✅ | ✅ | — | — | — | tenant_id + RLS | — | — | — | ✅ |
| Scheduled Processing | RetentionExecution | ✅ | ✅ | ✅ | — | RETENTION_EXECUTE | tenant_id + RLS | ✅ | Celery Beat (daily) | — | ✅ |
| Protected Records | RetentionPolicy.protected | ✅ | ✅ | ✅ | — | — | tenant_id + RLS | ✅ | — | — | ✅ |
| Audit Trail | RetentionExecution.audit | ✅ | ✅ | ✅ | — | — | tenant_id + RLS | ✅ | — | — | ✅ |

### 9. Enterprise Hardening (Infrastructure)

| Requirement | Implementation | Tests |
|-------------|----------------|-------|
| Read Replica Config | DATABASE_READ_REPLICA_URL setting | ✅ |
| Materialized Views | SQL migrations for profitability/productivity | ✅ |
| Zone-Redundant HA | Docker Compose / K8s config (deployment) | — |
| DR Drill | Documented runbook + backup/restore test | — |
| OpenSearch HA | Multi-AZ domain config (deployment) | — |

---

## New Database Tables Required

| Table | Purpose | Tenant Scoped | RLS | Key Columns |
|-------|---------|---------------|-----|-------------|
| report_definitions | Report templates/definitions | Yes | Yes | id, name, description, query_config, output_format, created_by |
| report_parameters | Dynamic parameters for reports | Yes | Yes | id, report_definition_id, name, type, required, default |
| report_jobs | Async report generation jobs | Yes | Yes | id, report_definition_id, parameters, status, progress, result_ref, idempotency_key, retry_count |
| report_outputs | Generated report artifacts | Yes | Yes | id, job_id, storage_key, format, size, checksum, expires_at |
| report_schedules | Scheduled report configurations | Yes | Yes | id, report_definition_id, cron, parameters, recipients, active |
| dashboard_widgets | Custom dashboard widgets | Yes | Yes | id, name, type, query_config, layout, is_default |
| data_access_requests | DPDP data access requests | Yes | Yes | id, subject_id, scope, status, compiled_data_ref, delivered_at |
| data_correction_requests | DPDP data correction requests | Yes | Yes | id, subject_id, field, old_value, new_value, status, approved_by |
| data_erasure_requests | DPDP data erasure requests | Yes | Yes | id, subject_id, scope, status, external_refs, executed_at |
| retention_policies | Retention rules per entity/type | Yes | Yes | id, entity_type, criteria, retention_days, action, protected |
| retention_executions | Retention job executions | Yes | Yes | id, policy_id, entities_affected, status, executed_at |
| data_residency_records | Data residency tracking | Yes | Yes | id, entity_type, entity_id, region, legal_basis |

---

## New Permissions Required

| Permission | Description | Roles |
|------------|-------------|-------|
| REPORT_READ | View reports and definitions | All except CLIENT_PORTAL |
| REPORT_CREATE | Create report definitions | FIRM_ADMIN, PARTNER, MANAGER, ADMIN_STAFF |
| REPORT_UPDATE | Update report definitions | FIRM_ADMIN, PARTNER, MANAGER, ADMIN_STAFF |
| REPORT_DELETE | Delete report definitions | FIRM_ADMIN, PARTNER |
| REPORT_GENERATE | Trigger report generation | FIRM_ADMIN, PARTNER, MANAGER, SENIOR_ASSOCIATE, ASSOCIATE, ADMIN_STAFF |
| REPORT_SCHEDULE_READ | View report schedules | All except CLIENT_PORTAL |
| REPORT_SCHEDULE_CREATE | Create report schedules | FIRM_ADMIN, PARTNER, MANAGER, ADMIN_STAFF |
| REPORT_SCHEDULE_UPDATE | Update report schedules | FIRM_ADMIN, PARTNER, MANAGER, ADMIN_STAFF |
| REPORT_SCHEDULE_DELETE | Delete report schedules | FIRM_ADMIN, PARTNER |
| ANALYTICS_READ | View analytics/dashboard | All except CLIENT_PORTAL |
| SEARCH_GLOBAL | Global search across entities | All except CLIENT_PORTAL |
| DPDP_ACCESS_READ | View data access requests | FIRM_ADMIN, PARTNER, MANAGER |
| DPDP_ACCESS_CREATE | Create data access requests | FIRM_ADMIN, PARTNER, MANAGER, SENIOR_ASSOCIATE |
| DPDP_CORRECTION_READ | View data correction requests | FIRM_ADMIN, PARTNER, MANAGER |
| DPDP_CORRECTION_CREATE | Create data correction requests | FIRM_ADMIN, PARTNER, MANAGER, SENIOR_ASSOCIATE |
| DPDP_CORRECTION_UPDATE | Update/approve corrections | FIRM_ADMIN, PARTNER, MANAGER |
| DPDP_ERASURE_READ | View data erasure requests | FIRM_ADMIN, PARTNER |
| DPDP_ERASURE_CREATE | Create data erasure requests | FIRM_ADMIN, PARTNER |
| DPDP_ERASURE_EXECUTE | Execute erasure | FIRM_ADMIN, PARTNER |
| DPDP_RESIDENCY_READ | View residency records | FIRM_ADMIN, PARTNER |
| RETENTION_READ | View retention policies | FIRM_ADMIN, PARTNER, MANAGER |
| RETENTION_CREATE | Create retention policies | FIRM_ADMIN, PARTNER |
| RETENTION_UPDATE | Update retention policies | FIRM_ADMIN, PARTNER |
| RETENTION_DELETE | Delete retention policies | FIRM_ADMIN, PARTNER |
| RETENTION_EXECUTE | Execute retention jobs | FIRM_ADMIN, PARTNER |

---

## New Celery Workers/Tasks Required

| Worker | Queue | Tasks | Schedule |
|--------|-------|-------|----------|
| reporting_worker | reporting | generate_report, compile_report_data, deliver_report | On-demand |
| retention_worker | compliance | execute_retention_policies, cleanup_expired_data | Daily (Celery Beat) |
| dpdp_worker | compliance | process_data_access, process_data_correction, process_data_erasure | On-demand |
| search_indexer | indexing | index_document, index_communication, reindex_tenant | Outbox-driven |

---

## Implementation Priority Order

1. **Database Migrations** (foundational)
2. **Reporting Module** (core domain)
3. **Async Report Generation** (worker + API)
4. **OpenSearch Global Search** (extend existing)
5. **DPDP Workflows** (data access, correction, erasure)
6. **Retention** (policies + execution)
7. **Permissions & Role Updates**
8. **Tests & Verification**
9. **Documentation**

---

## Cross-References to Existing Implementation

- **OpenSearch**: Already has `OpenSearchManager`, `OpenSearchService`, index templates for documents, communications, ai-processing, webhook-events
- **Celery**: Already has 5 queues (default, compliance, notifications, workload, outbox) + Beat scheduler
- **Outbox**: Transactional outbox with 30+ event types, worker processing
- **Azure Blob**: Document storage with SAS URLs, versioning, malware scanning
- **MongoDB**: Raw payload storage for documents, AI, webhooks
- **RLS**: 364 policies on 94 tables, fail-closed `SET LOCAL app.current_tenant`
- **PII Encryption**: Fernet (AES-128-GCM) for sensitive fields
- **Audit**: `AuditLog` model with 50+ action types

---

## Notes

1. **Read Replica**: Configure `DATABASE_READ_REPLICA_URL` in settings; use for analytics queries
2. **Materialized Views**: Create via SQL in migration; refresh via Celery Beat
3. **DPDP Erasure**: Application-level orchestration only; cross-system verification in Command 12B
4. **OpenSearch**: Tenant-partitioned indices (`documents-{tenant_id}`) already implemented
5. **Retention**: Reuse existing `Document.retention_policy` and `retention_until` fields
6. **Materialized Views**: Profitability, productivity, compliance metrics