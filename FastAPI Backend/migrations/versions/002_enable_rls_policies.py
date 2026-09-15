"""Enable RLS policies on all tenant tables

Revision ID: 002_enable_rls_policies
Revises: 4cfcf1cf520e
Create Date: 2026-09-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_enable_rls_policies'
down_revision: Union[str, None] = '4cfcf1cf520e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tenant-owned tables (46 tables) that need RLS policies
TENANT_TABLES = [
    "users",
    "teams",
    "clients",
    "client_contacts",
    "client_services",
    "matters",
    "tasks",
    "compliance_types",
    "compliance_cycles",
    "compliance_applicability",
    "documents",
    "invoices",
    "invoice_items",
    "payments",
    "expenses",
    "calendar_events",
    "communications",
    "workflow_definitions",
    "workflow_transition_definitions",
    "workflow_instances",
    "workflow_transition_history",
    "review_requests",
    "review_comments",
    "review_history",
    "tds_compliance_cycles",
    "tds_challans",
    "tds_deductees",
    "mca_filing_cycles",
    "mca_filing_configs",
    "notices",
    "notice_escalations",
    "user_availability",
    "team_capacity",
    "workload_snapshots",
    "workload_summaries",
    "assignments",
    "assignment_history",
    "escalations",
    "comments",
    "comment_attachments",
    "comment_reactions",
    "notification_templates",
    "notifications",
    "notification_deliveries",
    "notification_preferences",
    "audit_logs",
]

# The custom GUC name for tenant context
TENANT_GUC = "app.current_tenant"


def _create_rls_policies_for_table(table_name: str) -> list[str]:
    """Generate SQL statements to enable RLS and create 4 policies for a table.
    
    Uses NULLIF to handle empty string from current_setting when GUC is not set.
    This ensures fail-closed behavior: no tenant context = no data visible.
    """
    tenant_expr = f"NULLIF(current_setting('{TENANT_GUC}', true), '')::uuid"
    return [
        # Enable RLS on the table
        f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;",
        # Force RLS for table owners too (defense in depth)
        f"ALTER TABLE public.{table_name} FORCE ROW LEVEL SECURITY;",
        # SELECT policy
        f"""CREATE POLICY {table_name}_select_policy ON public.{table_name}
            FOR SELECT
            USING (tenant_id = {tenant_expr});""",
        # INSERT policy
        f"""CREATE POLICY {table_name}_insert_policy ON public.{table_name}
            FOR INSERT
            WITH CHECK (tenant_id = {tenant_expr});""",
        # UPDATE policy
        f"""CREATE POLICY {table_name}_update_policy ON public.{table_name}
            FOR UPDATE
            USING (tenant_id = {tenant_expr})
            WITH CHECK (tenant_id = {tenant_expr});""",
        # DELETE policy
        f"""CREATE POLICY {table_name}_delete_policy ON public.{table_name}
            FOR DELETE
            USING (tenant_id = {tenant_expr});""",
    ]


def upgrade() -> None:
    # The custom GUC 'app.current_tenant' is automatically created by PostgreSQL on first SET
    # No explicit creation needed - it's a runtime GUC

    # Enable RLS and create policies for each tenant table
    for table in TENANT_TABLES:
        for stmt in _create_rls_policies_for_table(table):
            op.execute(stmt)

    # Verify RLS is enabled on all tenant tables
    op.execute("""
        DO $$
        DECLARE
            tbl record;
            missing_rls text[] := '{}';
        BEGIN
            FOR tbl IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN (
                    'users', 'teams', 'clients', 'client_contacts', 'client_services',
                    'matters', 'tasks', 'compliance_types', 'compliance_cycles',
                    'compliance_applicability', 'documents', 'invoices', 'invoice_items',
                    'payments', 'expenses', 'calendar_events', 'communications',
                    'workflow_definitions', 'workflow_transition_definitions',
                    'workflow_instances', 'workflow_transition_history',
                    'review_requests', 'review_comments', 'review_history',
                    'tds_compliance_cycles', 'tds_challans', 'tds_deductees',
                    'mca_filing_cycles', 'mca_filing_configs', 'notices',
                    'notice_escalations', 'user_availability', 'team_capacity',
                    'workload_snapshots', 'workload_summaries', 'assignments',
                    'assignment_history', 'escalations', 'comments',
                    'comment_attachments', 'comment_reactions',
                    'notification_templates', 'notifications', 'notification_deliveries',
                    'notification_preferences', 'audit_logs'
                )
            LOOP
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = tbl.tablename
                    AND n.nspname = 'public'
                    AND c.relrowsecurity = true
                ) THEN
                    missing_rls := array_append(missing_rls, tbl.tablename);
                END IF;
            END LOOP;

            IF array_length(missing_rls, 1) > 0 THEN
                RAISE EXCEPTION 'RLS not enabled on tables: %', missing_rls;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop all policies and disable RLS
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON public.{table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON public.{table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON public.{table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON public.{table};")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")