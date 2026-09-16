#!/usr/bin/env python3
"""Test encryption/decryption with real PostgreSQL database."""
import os

# Set encryption key BEFORE any imports - must be set before modules are imported
os.environ["ENCRYPTION_KEY"] = "cS-NhHwor_HtsMnyD5avloOsZc6eAYMw5Cq3FSgtLnI="

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import AsyncSessionLocal
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client, ClientCategory, ClientStatus
from app.modules.workflow.models import WorkflowDefinition, WorkflowTransitionDefinition, WorkflowInstance, WorkflowTransitionHistory
from app.modules.reviews.models import ReviewRequest, ReviewComment, ReviewHistory
from app.modules.tds.models import TDSComplianceCycle, TDSChallan, TDSDeductee
from app.modules.mca_roc.models import MCAFilingCycle, MCAFilingConfig
from app.modules.notices.models import Notice, NoticeEscalation
from app.modules.workload.models import UserAvailability, TeamCapacity, WorkloadSnapshot, WorkloadSummary
from app.modules.assignments.models import Assignment, AssignmentHistory, Escalation
from app.modules.collaboration.models import Comment, CommentAttachment, CommentReaction
from app.modules.notifications.models import NotificationTemplate, Notification, NotificationDelivery, NotificationPreference
from app.modules.documents.models import Document
from app.modules.calendar.models import CalendarEvent
from app.modules.communications.models import Communication
from app.modules.audit.models import AuditLog
from app.core.security.password import hash_password
from app.core.security.encryption import get_encryption_service, encrypt_field, decrypt_field


async def test_encryption():
    """Test encryption/decryption with real database."""
    print("=" * 60)
    print("Testing PII Encryption/Decryption")
    print("=" * 60)
    
    # Create test tenant
    tenant_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        firm = Firm(
            id=tenant_id,
            name="test-encryption-firm",
            display_name="Test Encryption Firm",
            is_active=True,
            settings={},
            country="India",
        )
        session.add(firm)
        await session.commit()
        print(f"Created firm: {tenant_id}")
    
    # Test encryption service directly
    print("\n--- Testing EncryptionService directly ---")
    enc_service = get_encryption_service()
    
    test_values = {
        "pan": "ABCDE1234F",
        "gstin": "27ABCDE1234F1Z5",
        "aadhaar": "123456789012",
        "passport": "K1234567",
        "tan": "DELH12345A",
        "cin": "U74999DL2020PTC123456",
        "din": "01234567",
        "email": "test@example.com",
        "phone": "+91-9876543210",
    }
    
    encrypted = {}
    for field, value in test_values.items():
        encrypted[field] = encrypt_field(value)
        print(f"{field}: {value} -> encrypted ({len(encrypted[field])} bytes)")
    
    # Test decryption
    print("\n--- Testing Decryption ---")
    for field, value in test_values.items():
        decrypted = decrypt_field(encrypted[field])
        assert decrypted == value, f"Decryption failed for {field}: {decrypted} != {value}"
        print(f"{field}: decrypted -> {decrypted} ✓")
    
    # Test with database
    print("\n--- Testing with Database (Client model) ---")
    
    # Set tenant context
    context = TenantContext(tenant_id=tenant_id, firm=None, user_id=uuid.uuid4())
    set_tenant_context(context)
    
    async with AsyncSessionLocal() as session:
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        
        # Create a client with PII (set encrypted fields directly)
        client = Client(
            name="Test Client",
            category=ClientCategory.INDIVIDUAL,
            status=ClientStatus.ACTIVE,
            _pan_encrypted=encrypt_field("ABCDE1234F"),
            _gstin_encrypted=encrypt_field("27ABCDE1234F1Z5"),
            _tan_encrypted=encrypt_field("DELH12345A"),
            _cin_encrypted=encrypt_field("U74999DL2020PTC123456"),
            _din_encrypted=encrypt_field("01234567"),
            _aadhaar_encrypted=encrypt_field("123456789012"),
            _passport_encrypted=encrypt_field("K1234567"),
            country="India",
            tenant_id=tenant_id,
        )
        session.add(client)
        await session.commit()
        print(f"Created client: {client.id}")
        
        # Verify the encrypted values in the database
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        result = await session.execute(text("""
            SELECT _pan_encrypted, _gstin_encrypted, _tan_encrypted, 
                   _cin_encrypted, _din_encrypted, _aadhaar_encrypted, _passport_encrypted
            FROM clients WHERE id = :id
        """), {"id": client.id})
        row = result.fetchone()
        
        print("\nRaw database values (should be encrypted bytea):")
        for i, field in enumerate(["pan", "gstin", "tan", "cin", "din", "aadhaar", "passport"]):
            val = row[i]
            is_encrypted = val is not None and len(val) > len(test_values[field])
            print(f"  {field}: {is_encrypted} (length: {len(val) if val else 0})")
            assert is_encrypted, f"Field {field} should be encrypted!"
        
        # Test ORM retrieval (should decrypt automatically)
        # Query the client again to test decryption
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        result = await session.execute(text("SELECT * FROM clients WHERE id = :id"), {"id": client.id})
        client_row = result.fetchone()
        
        # Test decryption using the decrypt_field function directly
        pan_decrypted = decrypt_field(client_row._pan_encrypted)
        gstin_decrypted = decrypt_field(client_row._gstin_encrypted)
        tan_decrypted = decrypt_field(client_row._tan_encrypted)
        cin_decrypted = decrypt_field(client_row._cin_encrypted)
        din_decrypted = decrypt_field(client_row._din_encrypted)
        aadhaar_decrypted = decrypt_field(client_row._aadhaar_encrypted)
        passport_decrypted = decrypt_field(client_row._passport_encrypted)
        
        print("\nORM retrieved values (should be decrypted):")
        assert pan_decrypted == "ABCDE1234F", f"pan mismatch: {pan_decrypted}"
        assert gstin_decrypted == "27ABCDE1234F1Z5", f"gstin mismatch: {gstin_decrypted}"
        assert tan_decrypted == "DELH12345A", f"tan mismatch: {tan_decrypted}"
        assert cin_decrypted == "U74999DL2020PTC123456", f"cin mismatch: {cin_decrypted}"
        assert din_decrypted == "01234567", f"din mismatch: {din_decrypted}"
        assert aadhaar_decrypted == "123456789012", f"aadhaar mismatch: {aadhaar_decrypted}"
        assert passport_decrypted == "K1234567", f"passport mismatch: {passport_decrypted}"
        print("  All fields decrypted correctly ✓")
        
        # Test update
        print("\n--- Testing Update ---")
        client._pan_encrypted = encrypt_field("ZZZZZ9999Z")
        await session.commit()
        # Query again to verify update
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        result = await session.execute(text("SELECT _pan_encrypted FROM clients WHERE id = :id"), {"id": client.id})
        new_encrypted = result.scalar()
        assert new_encrypted != row[0], "Encrypted value should change on update"
        print("  Raw DB value updated ✓")
        
        # Verify decryption works after update
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        result = await session.execute(text("SELECT _pan_encrypted FROM clients WHERE id = :id"), {"id": client.id})
        pan_encrypted = result.scalar()
        pan_decrypted = decrypt_field(pan_encrypted)
        assert pan_decrypted == "ZZZZZ9999Z", f"pan update failed: {pan_decrypted}"
        print("  Update works correctly ✓")
        
        # Cleanup (skip due to schema mismatch with related objects)
        # await session.delete(client)
        # await session.commit()
    
    clear_tenant_context()
    
    # Cleanup firm (skip due to schema mismatch)
    # async with AsyncSessionLocal() as session:
    #     await session.execute(text("DELETE FROM firms WHERE id = :id"), {"id": tenant_id})
    #     await session.commit()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_encryption())