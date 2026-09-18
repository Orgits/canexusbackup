"""Add RLS policies for Phase 5 tables

Revision ID: 6a7b8c9d0e1f
Revises: f5a1b2c3d4e5
Create Date: 2026-09-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6a7b8c9d0e1f'
down_revision: Union[str, None] = 'f5a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Phase 5 tenant-owned tables that need RLS policies
PHASE5_TENANT_TABLES = [
    "report_definitions",
    "report_parameters",
    "report_jobs",
    "report_outputs",
    "report_schedules",
    "dashboard_widgets",
    "data_access_requests",
    "data_correction_requests",
    "data_erasure_requests",
    "retention_policies",
    "retention_executions",
    "data_residency_records",
]

# Also add outbox_events which was missing RLS
ADDITIONAL_TENANT_TABLES = [
    "outbox_events",
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
    # Enable RLS and create policies for Phase 5 tables
    all_tables = PHASE5_TENANT_TABLES + ADDITIONAL_TENANT_TABLES
    for table in all_tables:
        for stmt in _create_rls_policies_for_table(table):
            op.execute(stmt)

    # Verify RLS is enabled on all tables
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
                    'report_definitions', 'report_parameters', 'report_jobs',
                    'report_outputs', 'report_schedules', 'dashboard_widgets',
                    'data_access_requests', 'data_correction_requests',
                    'data_erasure_requests', 'retention_policies',
                    'retention_executions', 'data_residency_records',
                    'outbox_events'
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
    # Drop all policies and disable RLS for Phase 5 tables
    all_tables = PHASE5_TENANT_TABLES + ADDITIONAL_TENANT_TABLES
    for table in all_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON public.{table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON public.{table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON public.{table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON public.{table};")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")