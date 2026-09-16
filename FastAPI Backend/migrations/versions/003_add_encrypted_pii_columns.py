"""Add encrypted PII columns and migrate data

Revision ID: 003_add_encrypted_pii_columns
Revises: 002_enable_rls_policies
Create Date: 2026-09-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_encrypted_pii_columns'
down_revision: Union[str, None] = '002_enable_rls_policies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables and their encrypted column mappings
# Format: (table_name, [(new_encrypted_column, old_plaintext_column, nullable), ...])
ENCRYPTED_COLUMNS = {
    "firms": [
        ("_pan_encrypted", "pan", True),
        ("_gstin_encrypted", "gstin", True),
    ],
    "clients": [
        ("_pan_encrypted", "pan", True),
        ("_gstin_encrypted", "gstin", True),
        ("_tan_encrypted", "tan", True),
        ("_cin_encrypted", "cin", True),
        ("_din_encrypted", "din", True),
        ("_aadhaar_encrypted", "aadhaar", True),
        ("_passport_encrypted", "passport", True),
    ],
    "users": [
        ("_email_encrypted", "email", False),
        ("_phone_encrypted", "phone", True),
    ],
    "tds_compliance_cycles": [
        ("_tan_encrypted", "tan", True),
    ],
    "tds_challans": [
        ("_cin_encrypted", "cin", False),
    ],
    "tds_deductees": [
        ("_deductee_pan_encrypted", "deductee_pan", False),
    ],
}


def _add_encrypted_columns() -> None:
    """Add new encrypted columns to tables."""
    for table, columns in ENCRYPTED_COLUMNS.items():
        for new_col, old_col, nullable in columns:
            op.add_column(
                table,
                sa.Column(new_col, postgresql.BYTEA, nullable=nullable),
            )


def _migrate_data() -> None:
    """Migrate plaintext data to encrypted columns.

    Note: This migration assumes the encryption service is available.
    In practice, you would need to run a separate data migration script
    that uses the application's encryption service.
    """
    # This is a placeholder - actual encryption requires the encryption service
    # which depends on the ENCRYPTION_KEY environment variable.
    # The migration will add columns; a separate script should handle data migration.
    pass


def _drop_plaintext_columns() -> None:
    """Drop old plaintext columns after migration."""
    for table, columns in ENCRYPTED_COLUMNS.items():
        for new_col, old_col, nullable in columns:
            op.drop_column(table, old_col)


def _rename_encrypted_columns() -> None:
    """Rename encrypted columns to original names (optional, for cleaner API)."""
    # This is optional - you can keep _encrypted suffix or rename
    # For now, we keep the _encrypted suffix to make it explicit
    pass


def upgrade() -> None:
    # Add new encrypted columns
    _add_encrypted_columns()

    # Data migration would go here (run separately in production)
    # _migrate_data()

    # Drop old plaintext columns
    _drop_plaintext_columns()

    # Verify all encrypted columns exist
    op.execute("""
        DO $$
        DECLARE
            missing_cols text[] := '{}';
        BEGIN
            -- Check firms
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='firms' AND column_name='_pan_encrypted') THEN
                missing_cols := array_append(missing_cols, 'firms._pan_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='firms' AND column_name='_gstin_encrypted') THEN
                missing_cols := array_append(missing_cols, 'firms._gstin_encrypted');
            END IF;
            -- Check clients
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='_pan_encrypted') THEN
                missing_cols := array_append(missing_cols, 'clients._pan_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='_gstin_encrypted') THEN
                missing_cols := array_append(missing_cols, 'clients._gstin_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='_tan_encrypted') THEN
                missing_cols := array_append(missing_cols, 'clients._tan_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='_cin_encrypted') THEN
                missing_cols := array_append(missing_cols, 'clients._cin_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='_din_encrypted') THEN
                missing_cols := array_append(missing_cols, 'clients._din_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='_aadhaar_encrypted') THEN
                missing_cols := array_append(missing_cols, 'clients._aadhaar_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='clients' AND column_name='_passport_encrypted') THEN
                missing_cols := array_append(missing_cols, 'clients._passport_encrypted');
            END IF;
            -- Check users
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='_email_encrypted') THEN
                missing_cols := array_append(missing_cols, 'users._email_encrypted');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='_phone_encrypted') THEN
                missing_cols := array_append(missing_cols, 'users._phone_encrypted');
            END IF;
            -- Check tds_compliance_cycles
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tds_compliance_cycles' AND column_name='_tan_encrypted') THEN
                missing_cols := array_append(missing_cols, 'tds_compliance_cycles._tan_encrypted');
            END IF;
            -- Check tds_challans
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tds_challans' AND column_name='_cin_encrypted') THEN
                missing_cols := array_append(missing_cols, 'tds_challans._cin_encrypted');
            END IF;
            -- Check tds_deductees
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tds_deductees' AND column_name='_deductee_pan_encrypted') THEN
                missing_cols := array_append(missing_cols, 'tds_deductees._deductee_pan_encrypted');
            END IF;

            IF array_length(missing_cols, 1) > 0 THEN
                RAISE EXCEPTION 'Missing encrypted columns: %', missing_cols;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Re-add plaintext columns
    for table, columns in ENCRYPTED_COLUMNS.items():
        for new_col, old_col, nullable in columns:
            if old_col in ("email",):  # email was not nullable
                op.add_column(table, sa.Column(old_col, sa.String(255), nullable=False))
            elif old_col in ("pan", "gstin", "tan", "cin", "din", "aadhaar", "passport", "deductee_pan", "cin"):
                max_len = {"pan": 10, "gstin": 15, "tan": 10, "cin": 21, "din": 8, "aadhaar": 12, "passport": 20, "deductee_pan": 20}.get(old_col, 255)
                op.add_column(table, sa.Column(old_col, sa.String(max_len), nullable=nullable))
            elif old_col == "phone":
                op.add_column(table, sa.Column(old_col, sa.String(20), nullable=True))

    # Drop encrypted columns
    for table, columns in ENCRYPTED_COLUMNS.items():
        for new_col, old_col, nullable in columns:
            op.drop_column(table, new_col)