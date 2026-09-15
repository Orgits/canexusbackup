# CA Nexus — Tenant Table Inventory

**Generated:** 2026-09-15
**Source:** All SQLAlchemy models in `app/modules/**/models.py`

---

## Tenant Tables (inherit `TenantBaseModelMixin` — have `tenant_id` FK to `firms.id`)

| # | Table | Module | Notes |
|---|-------|--------|-------|
| 1 | `users` | users | Core user accounts |
| 2 | `teams` | users | Team groupings |
| 3 | `clients` | clients | Client master data |
| 4 | `client_contacts` | clients | Contact persons per client |
| 5 | `client_services` | clients | Service engagements per client |
| 6 | `matters` | matters | Work matters/cases |
| 7 | `tasks` | tasks | Tasks & subtasks |
| 8 | `compliance_types` | compliance | Configurable compliance type definitions |
| 9 | `compliance_cycles` | compliance | Compliance periods per client/type |
| 10 | `compliance_applicability` | compliance | Per-client type applicability |
| 11 | `documents` | documents | Document metadata & versioning |
| 12 | `invoices` | billing | Invoices |
| 13 | `invoice_items` | billing | Invoice line items |
| 14 | `payments` | billing | Payments received |
| 15 | `expenses` | billing | Expense claims |
| 16 | `calendar_events` | calendar | Calendar events |
| 17 | `communications` | communications | Emails, messages, letters |
| 18 | `workflow_definitions` | workflow | Workflow templates |
| 19 | `workflow_transition_definitions` | workflow | Transition rules |
| 20 | `workflow_instances` | workflow | Active workflow instances |
| 21 | `workflow_transition_history` | workflow | Transition audit trail |
| 22 | `review_requests` | reviews | Review/approval requests |
| 23 | `review_comments` | reviews | Threaded review comments |
| 24 | `review_history` | reviews | Review action history |
| 25 | `tds_compliance_cycles` | tds | TDS quarterly cycles |
| 26 | `tds_challans` | tds | TDS challan payments |
| 27 | `tds_deductees` | tds | TDS deductee details |
| 28 | `mca_filing_cycles` | mca_roc | MCA/ROC filing cycles |
| 29 | `mca_filing_configs` | mca_roc | Filing type configurations |
| 30 | `notices` | notices | Government/authority notices |
| 31 | `notice_escalations` | notices | Notice escalation history |
| 32 | `user_availability` | workload | Per-user daily availability |
| 33 | `team_capacity` | workload | Team capacity planning |
| 34 | `workload_snapshots` | workload | Periodic workload snapshots |
| 35 | `workload_summaries` | workload | Daily workload summaries |
| 36 | `assignments` | assignments | Entity-to-user/team assignments |
| 37 | `assignment_history` | assignments | Assignment change log |
| 38 | `escalations` | assignments | Escalation records |
| 39 | `comments` | collaboration | Polymorphic comments |
| 40 | `comment_attachments` | collaboration | Comment file attachments |
| 41 | `comment_reactions` | collaboration | Emoji reactions on comments |
| 42 | `notification_templates` | notifications | Notification templates |
| 43 | `notifications` | notifications | In-app notifications |
| 44 | `notification_deliveries` | notifications | Multi-channel delivery tracking |
| 45 | `notification_preferences` | notifications | User notification preferences |
| 46 | `audit_logs` | audit | System audit trail |

**Total: 46 tenant-owned tables**

---

## Non-Tenant Tables (do NOT have `tenant_id`)

| Table | Module | Reason |
|-------|--------|--------|
| `firms` | firms | Root tenant entity — owns all tenant data |

**Total: 1 non-tenant table**

---

## RLS Policy Requirements

Every tenant table (46 tables) requires **4 policies**:

1. **SELECT** — `USING (tenant_id = current_setting('app.current_tenant', true)::uuid)`
2. **INSERT** — `WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid)`
3. **UPDATE** — `USING (tenant_id = current_setting('app.current_tenant', true)::uuid) WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid)`
4. **DELETE** — `USING (tenant_id = current_setting('app.current_tenant', true)::uuid)`

**Total policies to create: 46 × 4 = 184 policies**

---

## Implementation Notes

- All policies use `current_setting('app.current_tenant', true)` — the `true` parameter means "return NULL if not set" rather than error
- Policies must **fail closed**: when `app.current_tenant` is NULL, no rows are visible/modifiable
- `SET LOCAL app.current_tenant = '<uuid>'` must be executed at transaction start
- Application role must **NOT** have `BYPASSRLS` attribute
- Connection pool safety: `SET LOCAL` is transaction-scoped, automatically reset on commit/rollback