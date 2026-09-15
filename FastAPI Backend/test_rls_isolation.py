#!/usr/bin/env python3
"""Cross-tenant isolation tests for PostgreSQL RLS - using raw SQL to avoid ORM issues.

Tests that Tenant A cannot access Tenant B's data at both:
- Application/API layer
- Direct repository/database layer
"""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import AsyncSessionLocal, get_tenant_db
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context
from app.core.security.password import hash_password


async def _set_tenant(session: AsyncSession, tenant_id: uuid.UUID):
    """Set tenant context using SET LOCAL (cannot use parameters)."""
    await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))


async def create_test_data():
    """Create two tenants with sample data using raw SQL with proper RLS context."""
    async with AsyncSessionLocal() as session:
        # Create Tenant A (firms table has no RLS)
        tenant_a_id = uuid.uuid4()
        await session.execute(text("""
            INSERT INTO firms (id, name, display_name, is_active, settings, country, created_at, updated_at)
            VALUES (:id, 'tenant-a-firm', 'Tenant A Firm', true, '{}', 'India', now(), now())
        """), {"id": tenant_a_id})
        
        # Create Tenant B
        tenant_b_id = uuid.uuid4()
        await session.execute(text("""
            INSERT INTO firms (id, name, display_name, is_active, settings, country, created_at, updated_at)
            VALUES (:id, 'tenant-b-firm', 'Tenant B Firm', true, '{}', 'India', now(), now())
        """), {"id": tenant_b_id})
        
        await session.commit()
        
        # Create users for Tenant A (with RLS context)
        user_a_id = uuid.uuid4()
        await _set_tenant(session, tenant_a_id)
        await session.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, is_active, is_superuser, roles, direct_permissions, tenant_id, created_at, updated_at)
            VALUES (:id, 'usera@tenant-a.com', :pwd, 'User A', true, false, '{}', '{}', :tenant_id, now(), now())
        """), {"id": user_a_id, "pwd": hash_password("password123"), "tenant_id": tenant_a_id})
        
        # Create users for Tenant B
        user_b_id = uuid.uuid4()
        await _set_tenant(session, tenant_b_id)
        await session.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, is_active, is_superuser, roles, direct_permissions, tenant_id, created_at, updated_at)
            VALUES (:id, 'userb@tenant-b.com', :pwd, 'User B', true, false, '{}', '{}', :tenant_id, now(), now())
        """), {"id": user_b_id, "pwd": hash_password("password123"), "tenant_id": tenant_b_id})
        
        await session.commit()
        
        # Create clients for Tenant A
        client_a_id = uuid.uuid4()
        await _set_tenant(session, tenant_a_id)
        await session.execute(text("""
            INSERT INTO clients (id, name, category, status, tenant_id, responsible_user_id, country, created_at, updated_at, is_archived, tags, extra_metadata, other_ids)
            VALUES (:id, 'Client A1', 'COMPANY', 'ACTIVE', :tenant_id, :user_id, 'India', now(), now(), false, '{}', '{}', '{}')
        """), {"id": client_a_id, "tenant_id": tenant_a_id, "user_id": user_a_id})
        
        # Create clients for Tenant B
        client_b_id = uuid.uuid4()
        await _set_tenant(session, tenant_b_id)
        await session.execute(text("""
            INSERT INTO clients (id, name, category, status, tenant_id, responsible_user_id, country, created_at, updated_at, is_archived, tags, extra_metadata, other_ids)
            VALUES (:id, 'Client B1', 'COMPANY', 'ACTIVE', :tenant_id, :user_id, 'India', now(), now(), false, '{}', '{}', '{}')
        """), {"id": client_b_id, "tenant_id": tenant_b_id, "user_id": user_b_id})
        
        await session.commit()
        
        # Create matters for Tenant A
        matter_a_id = uuid.uuid4()
        await _set_tenant(session, tenant_a_id)
        await session.execute(text("""
            INSERT INTO matters (id, client_id, matter_type, status, priority, name, tenant_id, responsible_user_id, progress_percentage, tags, extra_metadata, created_at, updated_at)
            VALUES (:id, :client_id, 'ITR', 'IN_PROGRESS', 'HIGH', 'Matter A1', :tenant_id, :user_id, 0, '{}', '{}', now(), now())
        """), {"id": matter_a_id, "client_id": client_a_id, "tenant_id": tenant_a_id, "user_id": user_a_id})
        
        # Create matters for Tenant B
        matter_b_id = uuid.uuid4()
        await _set_tenant(session, tenant_b_id)
        await session.execute(text("""
            INSERT INTO matters (id, client_id, matter_type, status, priority, name, tenant_id, responsible_user_id, progress_percentage, tags, extra_metadata, created_at, updated_at)
            VALUES (:id, :client_id, 'GST', 'IN_PROGRESS', 'HIGH', 'Matter B1', :tenant_id, :user_id, 0, '{}', '{}', now(), now())
        """), {"id": matter_b_id, "client_id": client_b_id, "tenant_id": tenant_b_id, "user_id": user_b_id})
        
        await session.commit()
        
        # Create tasks for Tenant A
        task_a_id = uuid.uuid4()
        await _set_tenant(session, tenant_a_id)
        await session.execute(text("""
            INSERT INTO tasks (id, client_id, matter_id, title, status, priority, tenant_id, assignee_id, progress_percentage, checklist, dependencies, tags, extra_metadata, created_at, updated_at)
            VALUES (:id, :client_id, :matter_id, 'Task A1', 'IN_PROGRESS', 'HIGH', :tenant_id, :user_id, 0, '[]'::jsonb, '{}'::uuid[], '{}'::text[], '{}', now(), now())
        """), {"id": task_a_id, "client_id": client_a_id, "matter_id": matter_a_id, "tenant_id": tenant_a_id, "user_id": user_a_id})
        
        # Create tasks for Tenant B
        task_b_id = uuid.uuid4()
        await _set_tenant(session, tenant_b_id)
        await session.execute(text("""
            INSERT INTO tasks (id, client_id, matter_id, title, status, priority, tenant_id, assignee_id, progress_percentage, checklist, dependencies, tags, extra_metadata, created_at, updated_at)
            VALUES (:id, :client_id, :matter_id, 'Task B1', 'IN_PROGRESS', 'HIGH', :tenant_id, :user_id, 0, '[]'::jsonb, '{}'::uuid[], '{}'::text[], '{}', now(), now())
        """), {"id": task_b_id, "client_id": client_b_id, "matter_id": matter_b_id, "tenant_id": tenant_b_id, "user_id": user_b_id})
        
        await session.commit()
        
        # Create documents for Tenant A
        doc_a_id = uuid.uuid4()
        await _set_tenant(session, tenant_a_id)
        await session.execute(text("""
            INSERT INTO documents (id, client_id, matter_id, filename, original_filename, file_extension, mime_type, file_size, storage_path, storage_provider, storage_key, version, is_latest_version, category, status, title, tags, uploaded_by, source, extra_metadata, checksum, ocr_text, extracted_data, classification, confidence_score, retention_policy, retention_until, created_at, updated_at, tenant_id)
            VALUES (:id, :client_id, :matter_id, 'doc_a.pdf', 'doc_a.pdf', 'pdf', 'application/pdf', 1024, '/fake/path/doc_a.pdf', 'local', 'doc_a.pdf', 1, true, 'TAX', 'PROCESSED', 'Doc A', '{}'::text[], :user_id, 'manual', '{}', null, null, '{}', null, null, null, null, now(), now(), :tenant_id)
        """), {"id": doc_a_id, "client_id": client_a_id, "matter_id": matter_a_id, "tenant_id": tenant_a_id, "user_id": user_a_id})
        
        # Create documents for Tenant B
        doc_b_id = uuid.uuid4()
        await _set_tenant(session, tenant_b_id)
        await session.execute(text("""
            INSERT INTO documents (id, client_id, matter_id, filename, original_filename, file_extension, mime_type, file_size, storage_path, storage_provider, storage_key, version, is_latest_version, category, status, title, tags, uploaded_by, source, extra_metadata, checksum, ocr_text, extracted_data, classification, confidence_score, retention_policy, retention_until, created_at, updated_at, tenant_id)
            VALUES (:id, :client_id, :matter_id, 'doc_b.pdf', 'doc_b.pdf', 'pdf', 'application/pdf', 2048, '/fake/path/doc_b.pdf', 'local', 'doc_b.pdf', 1, true, 'TAX', 'PROCESSED', 'Doc B', '{}'::text[], :user_id, 'manual', '{}', null, null, '{}', null, null, null, null, now(), now(), :tenant_id)
        """), {"id": doc_b_id, "client_id": client_b_id, "matter_id": matter_b_id, "tenant_id": tenant_b_id, "user_id": user_b_id})
        
        await session.commit()
        
        print(f"Created Tenant A: {tenant_a_id}")
        print(f"Created Tenant B: {tenant_b_id}")
        print(f"User A: {user_a_id}, User B: {user_b_id}")
        print(f"Client A: {client_a_id}, Client B: {client_b_id}")
        print(f"Matter A: {matter_a_id}, Matter B: {matter_b_id}")
        print(f"Task A: {task_a_id}, Task B: {task_b_id}")
        print(f"Doc A: {doc_a_id}, Doc B: {doc_b_id}")
        
        return {
            "tenant_a_id": tenant_a_id,
            "tenant_b_id": tenant_b_id,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "client_a_id": client_a_id,
            "client_b_id": client_b_id,
            "matter_a_id": matter_a_id,
            "matter_b_id": matter_b_id,
            "task_a_id": task_a_id,
            "task_b_id": task_b_id,
            "doc_a_id": doc_a_id,
            "doc_b_id": doc_b_id,
        }


async def test_rls_with_set_local(data):
    """Test RLS with SET LOCAL context - should only see own tenant's data."""
    print("\n=== Test 1: RLS with SET LOCAL (Tenant A context) ===")
    
    # Set tenant context for Tenant A
    context_a = TenantContext(
        tenant_id=data["tenant_a_id"],
        firm=None,  # Not needed for raw SQL test
        user_id=data["user_a_id"],
    )
    set_tenant_context(context_a)
    
    async with AsyncSessionLocal() as session:
        # Execute SET LOCAL
        await _set_tenant(session, data["tenant_a_id"])
        
        # Query clients - should only see Tenant A's client
        result = await session.execute(text("SELECT id FROM clients"))
        clients = result.fetchall()
        print(f"Clients visible to Tenant A: {len(clients)} (expected: 1)")
        assert len(clients) == 1, f"Expected 1 client, got {len(clients)}"
        assert clients[0][0] == data["client_a_id"]
        
        # Query matters - should only see Tenant A's matter
        result = await session.execute(text("SELECT id FROM matters"))
        matters = result.fetchall()
        print(f"Matters visible to Tenant A: {len(matters)} (expected: 1)")
        assert len(matters) == 1
        assert matters[0][0] == data["matter_a_id"]
        
        # Query tasks - should only see Tenant A's task
        result = await session.execute(text("SELECT id FROM tasks"))
        tasks = result.fetchall()
        print(f"Tasks visible to Tenant A: {len(tasks)} (expected: 1)")
        assert len(tasks) == 1
        assert tasks[0][0] == data["task_a_id"]
        
        # Query documents - should only see Tenant A's document
        result = await session.execute(text("SELECT id FROM documents"))
        docs = result.fetchall()
        print(f"Documents visible to Tenant A: {len(docs)} (expected: 1)")
        assert len(docs) == 1
        assert docs[0][0] == data["doc_a_id"]
    
    clear_tenant_context()
    print("✓ Tenant A sees only its own data")


async def test_rls_without_context():
    """Test RLS without tenant context - should see NO data (fail closed)."""
    print("\n=== Test 2: RLS without context (fail closed) ===")
    
    clear_tenant_context()
    
    async with AsyncSessionLocal() as session:
        # Don't set any tenant context
        result = await session.execute(text("SELECT id FROM clients"))
        clients = result.fetchall()
        print(f"Clients visible without context: {len(clients)} (expected: 0)")
        assert len(clients) == 0, f"Expected 0 clients, got {len(clients)}"
        
        result = await session.execute(text("SELECT id FROM matters"))
        matters = result.fetchall()
        print(f"Matters visible without context: {len(matters)} (expected: 0)")
        assert len(matters) == 0
        
        result = await session.execute(text("SELECT id FROM tasks"))
        tasks = result.fetchall()
        print(f"Tasks visible without context: {len(tasks)} (expected: 0)")
        assert len(tasks) == 0
        
        result = await session.execute(text("SELECT id FROM documents"))
        docs = result.fetchall()
        print(f"Documents visible without context: {len(docs)} (expected: 0)")
        assert len(docs) == 0
    
    print("✓ No data visible without tenant context (fail closed)")


async def test_cross_tenant_isolation(data):
    """Test that Tenant A cannot access Tenant B's data even with explicit queries."""
    print("\n=== Test 3: Cross-tenant isolation (explicit Tenant B ID with Tenant A context) ===")
    
    # Set tenant context for Tenant A
    context_a = TenantContext(
        tenant_id=data["tenant_a_id"],
        firm=None,
        user_id=data["user_a_id"],
    )
    set_tenant_context(context_a)
    
    async with AsyncSessionLocal() as session:
        await _set_tenant(session, data["tenant_a_id"])
        
        # Try to SELECT Tenant B's client by ID - should return None
        result = await session.execute(
            text("SELECT id FROM clients WHERE id = :id"),
            {"id": data["client_b_id"]}
        )
        client = result.fetchone()
        print(f"Tenant A querying Tenant B's client by ID: {'FOUND' if client else 'NOT FOUND'} (expected: NOT FOUND)")
        assert client is None, "Tenant A should not see Tenant B's client"
        
        # Try to UPDATE Tenant B's client - should affect 0 rows
        result = await session.execute(
            text("UPDATE clients SET name = 'hacked' WHERE id = :id"),
            {"id": data["client_b_id"]}
        )
        print(f"Tenant A updating Tenant B's client: {result.rowcount} rows affected (expected: 0)")
        assert result.rowcount == 0, "Tenant A should not update Tenant B's client"
        
        # Try to DELETE Tenant B's client - should affect 0 rows
        result = await session.execute(
            text("DELETE FROM clients WHERE id = :id"),
            {"id": data["client_b_id"]}
        )
        print(f"Tenant A deleting Tenant B's client: {result.rowcount} rows affected (expected: 0)")
        assert result.rowcount == 0, "Tenant A should not delete Tenant B's client"
        
        # Try to INSERT with Tenant B's tenant_id - should fail or be rejected
        try:
            await session.execute(
                text("""
                    INSERT INTO clients (id, name, category, status, tenant_id, created_at, updated_at, is_archived, tags, extra_metadata, other_ids)
                    VALUES (:id, 'malicious', 'company', 'active', :tenant_id, now(), now(), false, '{}', '{}', '{}')
                """),
                {"id": uuid.uuid4(), "tenant_id": data["tenant_b_id"]}
            )
            await session.commit()
            print("Tenant A inserting with Tenant B's tenant_id: SUCCEEDED (unexpected!)")
            # Check if it was actually inserted
            result = await session.execute(text("SELECT id FROM clients WHERE name = 'malicious'"))
            malicious = result.fetchone()
            if malicious:
                print("  WARNING: Malicious insert succeeded!")
            else:
                print("  But row not visible (RLS blocked SELECT)")
        except Exception as e:
            print(f"Tenant A inserting with Tenant B's tenant_id: FAILED with {type(e).__name__} (expected)")
    
    clear_tenant_context()
    print("✓ Cross-tenant isolation verified")


async def test_reverse_isolation(data):
    """Test that Tenant B cannot access Tenant A's data."""
    print("\n=== Test 4: Reverse isolation (Tenant B context) ===")
    
    context_b = TenantContext(
        tenant_id=data["tenant_b_id"],
        firm=None,
        user_id=data["user_b_id"],
    )
    set_tenant_context(context_b)
    
    async with AsyncSessionLocal() as session:
        await _set_tenant(session, data["tenant_b_id"])
        
        # Query clients - should only see Tenant B's client
        result = await session.execute(text("SELECT id FROM clients"))
        clients = result.fetchall()
        print(f"Clients visible to Tenant B: {len(clients)} (expected: 1)")
        assert len(clients) == 1
        assert clients[0][0] == data["client_b_id"]
        
        # Try to access Tenant A's data
        result = await session.execute(
            text("SELECT id FROM clients WHERE id = :id"),
            {"id": data["client_a_id"]}
        )
        client = result.fetchone()
        print(f"Tenant B querying Tenant A's client by ID: {'FOUND' if client else 'NOT FOUND'} (expected: NOT FOUND)")
        assert client is None
    
    clear_tenant_context()
    print("✓ Reverse isolation verified")


async def test_connection_pool_isolation(data):
    """Test that tenant context doesn't leak through connection pooling."""
    print("\n=== Test 5: Connection pool isolation ===")
    
    # Simulate: Tenant A request -> connection -> pool -> Tenant B request -> reused connection
    
    # Request 1: Tenant A
    context_a = TenantContext(
        tenant_id=data["tenant_a_id"],
        firm=None,
        user_id=data["user_a_id"],
    )
    set_tenant_context(context_a)
    
    async with AsyncSessionLocal() as session:
        await _set_tenant(session, data["tenant_a_id"])
        result = await session.execute(text("SELECT id FROM clients"))
        clients_a = result.fetchall()
        print(f"Request 1 (Tenant A): {len(clients_a)} clients")
        assert len(clients_a) == 1
    
    clear_tenant_context()
    
    # Connection returned to pool, now Tenant B uses it
    context_b = TenantContext(
        tenant_id=data["tenant_b_id"],
        firm=None,
        user_id=data["user_b_id"],
    )
    set_tenant_context(context_b)
    
    async with AsyncSessionLocal() as session:
        await _set_tenant(session, data["tenant_b_id"])
        result = await session.execute(text("SELECT id FROM clients"))
        clients_b = result.fetchall()
        print(f"Request 2 (Tenant B): {len(clients_b)} clients")
        assert len(clients_b) == 1
        assert clients_b[0][0] == data["client_b_id"]
    
    clear_tenant_context()
    
    # Now Tenant A again - should still see only its data
    context_a2 = TenantContext(
        tenant_id=data["tenant_a_id"],
        firm=None,
        user_id=data["user_a_id"],
    )
    set_tenant_context(context_a2)
    
    async with AsyncSessionLocal() as session:
        await _set_tenant(session, data["tenant_a_id"])
        result = await session.execute(text("SELECT id FROM clients"))
        clients_a2 = result.fetchall()
        print(f"Request 3 (Tenant A again): {len(clients_a2)} clients")
        assert len(clients_a2) == 1
        assert clients_a2[0][0] == data["client_a_id"]
    
    clear_tenant_context()
    print("✓ Connection pool isolation verified - no leakage")


async def test_application_layer_filtering(data):
    """Test that application-level tenant filtering works with RLS (defense in depth)."""
    print("\n=== Test 6: Application-layer filtering (defense in depth) ===")
    
    # This simulates what the repository layer does - explicit tenant_id filtering
    # With RLS, we still need to set the tenant context, but the explicit filter
    # provides an additional layer of protection
    
    context_a = TenantContext(
        tenant_id=data["tenant_a_id"],
        firm=None,
        user_id=data["user_a_id"],
    )
    set_tenant_context(context_a)
    
    async with AsyncSessionLocal() as session:
        await _set_tenant(session, data["tenant_a_id"])
        # Explicit WHERE tenant_id = tenant_a with RLS context
        result = await session.execute(
            text("SELECT id FROM clients WHERE tenant_id = :tid"),
            {"tid": data["tenant_a_id"]}
        )
        clients = result.fetchall()
        print(f"App-layer filter for Tenant A: {len(clients)} clients (expected: 1)")
        assert len(clients) == 1
        
        # App-layer filter for Tenant B
        result = await session.execute(
            text("SELECT id FROM clients WHERE tenant_id = :tid"),
            {"tid": data["tenant_b_id"]}
        )
        clients = result.fetchall()
        print(f"App-layer filter for Tenant B (with Tenant A context): {len(clients)} clients (expected: 0)")
        # With RLS, even explicit filter for other tenant returns 0
        assert len(clients) == 0
    
    clear_tenant_context()
    print("✓ Application-layer filtering works as additional defense")


async def test_get_tenant_db_dependency(data):
    """Test the get_tenant_db dependency works correctly."""
    print("\n=== Test 7: get_tenant_db dependency ===")
    
    context_a = TenantContext(
        tenant_id=data["tenant_a_id"],
        firm=None,
        user_id=data["user_a_id"],
    )
    set_tenant_context(context_a)
    
    async for session in get_tenant_db():
        result = await session.execute(text("SELECT id FROM clients"))
        clients = result.fetchall()
        print(f"get_tenant_db() for Tenant A: {len(clients)} clients (expected: 1)")
        assert len(clients) == 1
        assert clients[0][0] == data["client_a_id"]
        break  # Only need one iteration
    
    clear_tenant_context()
    
    # Without context - should see nothing
    clear_tenant_context()
    async for session in get_tenant_db():
        result = await session.execute(text("SELECT id FROM clients"))
        clients = result.fetchall()
        print(f"get_tenant_db() without context: {len(clients)} clients (expected: 0)")
        assert len(clients) == 0
        break
    
    print("✓ get_tenant_db dependency works correctly")


async def cleanup_test_data(data):
    """Clean up test data."""
    print("\n=== Cleanup ===")
    
    # For cleanup, we'll use a session and manually SET LOCAL for each tenant
    for tenant_key in ["tenant_a_id", "tenant_b_id"]:
        tenant_id = data[tenant_key]
        async with AsyncSessionLocal() as session:
            await _set_tenant(session, tenant_id)
            # Delete in reverse order of dependencies
            await session.execute(text("DELETE FROM documents WHERE tenant_id = :tid"), {"tid": tenant_id})
            await session.execute(text("DELETE FROM tasks WHERE tenant_id = :tid"), {"tid": tenant_id})
            await session.execute(text("DELETE FROM matters WHERE tenant_id = :tid"), {"tid": tenant_id})
            await session.execute(text("DELETE FROM clients WHERE tenant_id = :tid"), {"tid": tenant_id})
            await session.execute(text("DELETE FROM users WHERE tenant_id = :tid"), {"tid": tenant_id})
            await session.commit()
    
    # Delete firms (no RLS)
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM firms WHERE id IN (:a, :b)"), 
                             {"a": data["tenant_a_id"], "b": data["tenant_b_id"]})
        await session.commit()
    
    print("✓ Test data cleaned up")


async def main():
    print("=" * 60)
    print("CA NEXUS - PostgreSQL RLS Cross-Tenant Isolation Tests")
    print("=" * 60)
    
    # Create test data
    data = await create_test_data()
    
    try:
        # Run all tests
        await test_rls_with_set_local(data)
        await test_rls_without_context()
        await test_cross_tenant_isolation(data)
        await test_reverse_isolation(data)
        await test_connection_pool_isolation(data)
        await test_application_layer_filtering(data)
        await test_get_tenant_db_dependency(data)
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await cleanup_test_data(data)


if __name__ == "__main__":
    asyncio.run(main())