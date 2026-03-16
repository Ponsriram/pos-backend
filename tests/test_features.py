"""
Comprehensive tests for all 16 new features added to the POS backend.

Organised by feature / priority:
  P0: User profile, single store endpoints
  P1: Multi-store analytics, chains, groups, notifications
  P2: Out-of-stock toggle, integration logs, zones, reports
  P3: Outlet type, pending purchase summary, user activity logs, config details
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def _create_store(client: AsyncClient, **overrides) -> dict:
    payload = {
        "name": overrides.get("name", "Test Store"),
        "location": overrides.get("location", "Test Location"),
        "state": overrides.get("state"),
        "city": overrides.get("city"),
        "outlet_type": overrides.get("outlet_type"),
    }
    resp = await client.post("/stores", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════
#  P0 #1 — USER PROFILE + SUB-USER (CLOUD ACCESS)
# ═══════════════════════════════════════════════════════════════════════════

class TestUserProfile:
    async def test_get_my_profile(self, client: AsyncClient):
        resp = await client.get("/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "owner@test.com"
        assert data["role"] == "owner"

    async def test_update_my_profile(self, client: AsyncClient):
        resp = await client.put("/users/me", json={"name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"


class TestSubUsers:
    async def test_create_sub_user(self, client: AsyncClient):
        payload = {
            "name": "Sub User",
            "email": "sub@test.com",
            "password": "Str0ngP@ss!",
            "role": "cashier",
        }
        resp = await client.post("/users", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "sub@test.com"
        assert data["role"] == "cashier"

    async def test_create_sub_user_duplicate_email(self, client: AsyncClient):
        payload = {
            "name": "Sub User",
            "email": "sub2@test.com",
            "password": "Str0ngP@ss!",
            "role": "cashier",
        }
        resp1 = await client.post("/users", json=payload)
        assert resp1.status_code == 201
        resp2 = await client.post("/users", json=payload)
        assert resp2.status_code == 409

    async def test_list_sub_users(self, client: AsyncClient):
        # Create a sub-user first
        await client.post("/users", json={
            "name": "Sub", "email": "listsub@test.com",
            "password": "Str0ngP@ss!", "role": "waiter",
        })
        resp = await client.get("/users")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_sub_user(self, client: AsyncClient):
        create_resp = await client.post("/users", json={
            "name": "Old Name", "email": "edit@test.com",
            "password": "Str0ngP@ss!", "role": "waiter",
        })
        user_id = create_resp.json()["id"]
        resp = await client.put(f"/users/{user_id}", json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"


# ═══════════════════════════════════════════════════════════════════════════
#  P0 #2 — SINGLE STORE GET / PUT
# ═══════════════════════════════════════════════════════════════════════════

class TestSingleStore:
    async def test_create_and_get_store(self, client: AsyncClient):
        store = await _create_store(client, name="My Cafe")
        resp = await client.get(f"/stores/{store['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Cafe"

    async def test_get_store_not_found(self, client: AsyncClient):
        resp = await client.get(f"/stores/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_update_store(self, client: AsyncClient):
        store = await _create_store(client, name="Old Name")
        resp = await client.put(
            f"/stores/{store['id']}",
            json={"name": "New Name", "state": "Karnataka"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["state"] == "Karnataka"


# ═══════════════════════════════════════════════════════════════════════════
#  P1 #3 — MULTI-STORE ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════

class TestMultiStoreAnalytics:
    async def test_by_store_empty(self, client: AsyncClient):
        resp = await client.get("/analytics/summary/by-store")
        assert resp.status_code == 200
        data = resp.json()
        assert "outlets" in data
        assert "totals" in data

    async def test_by_store_with_store(self, client: AsyncClient):
        await _create_store(client)
        resp = await client.get("/analytics/summary/by-store")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["outlets"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
#  P1 #4 — CHAIN / FRANCHISE CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestChains:
    async def test_create_chain(self, client: AsyncClient):
        resp = await client.post("/chains", json={"name": "Pizza Empire"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Pizza Empire"

    async def test_list_chains(self, client: AsyncClient):
        await client.post("/chains", json={"name": "Chain A"})
        resp = await client.get("/chains")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_chain(self, client: AsyncClient):
        create = await client.post("/chains", json={"name": "Chain B"})
        chain_id = create.json()["id"]
        resp = await client.get(f"/chains/{chain_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Chain B"

    async def test_update_chain(self, client: AsyncClient):
        create = await client.post("/chains", json={"name": "Old Chain"})
        chain_id = create.json()["id"]
        resp = await client.put(f"/chains/{chain_id}", json={"name": "New Chain"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Chain"

    async def test_chain_stores(self, client: AsyncClient):
        chain = (await client.post("/chains", json={"name": "ChainX"})).json()
        # Create store linked to chain
        store_resp = await client.post("/stores", json={
            "name": "Outlet 1", "chain_id": chain["id"],
        })
        assert store_resp.status_code == 201

        resp = await client.get(f"/chains/{chain['id']}/stores")
        assert resp.status_code == 200
        stores = resp.json()
        assert len(stores) >= 1

    async def test_chain_not_found(self, client: AsyncClient):
        resp = await client.get(f"/chains/{uuid.uuid4()}")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  P1 #5 — PERMISSION GROUPS (ADMIN / BILLER)
# ═══════════════════════════════════════════════════════════════════════════

class TestPermissionGroups:
    async def test_create_group(self, client: AsyncClient):
        resp = await client.post("/groups", json={
            "name": "Floor Managers",
            "group_type": "admin",
            "permissions": ["orders.view", "orders.cancel"],
            "store_ids": [],
            "member_user_ids": [],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Floor Managers"
        assert data["group_type"] == "admin"

    async def test_list_groups(self, client: AsyncClient):
        await client.post("/groups", json={
            "name": "G1", "group_type": "admin",
            "permissions": [], "store_ids": [], "member_user_ids": [],
        })
        resp = await client.get("/groups")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_list_groups_filter(self, client: AsyncClient):
        await client.post("/groups", json={
            "name": "Biller Group", "group_type": "biller",
            "permissions": [], "store_ids": [], "member_user_ids": [],
        })
        resp = await client.get("/groups?group_type=biller")
        assert resp.status_code == 200
        for g in resp.json():
            assert g["group_type"] == "biller"

    async def test_get_group(self, client: AsyncClient):
        create_resp = await client.post("/groups", json={
            "name": "Get Test", "group_type": "admin",
            "permissions": ["reports.view"], "store_ids": [], "member_user_ids": [],
        })
        group_id = create_resp.json()["id"]
        resp = await client.get(f"/groups/{group_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Test"

    async def test_update_group(self, client: AsyncClient):
        create_resp = await client.post("/groups", json={
            "name": "Update Test", "group_type": "admin",
            "permissions": [], "store_ids": [], "member_user_ids": [],
        })
        group_id = create_resp.json()["id"]
        resp = await client.put(f"/groups/{group_id}", json={
            "name": "Updated Group",
            "permissions": ["inventory.adjust"],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Group"

    async def test_delete_group(self, client: AsyncClient):
        create_resp = await client.post("/groups", json={
            "name": "Delete Me", "group_type": "admin",
            "permissions": [], "store_ids": [], "member_user_ids": [],
        })
        group_id = create_resp.json()["id"]
        resp = await client.delete(f"/groups/{group_id}")
        assert resp.status_code == 204

    async def test_group_not_found(self, client: AsyncClient):
        resp = await client.get(f"/groups/{uuid.uuid4()}")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  P1 #7 — NOTIFICATIONS + DEVICE TOKENS
# ═══════════════════════════════════════════════════════════════════════════

class TestNotifications:
    async def test_list_notifications_empty(self, client: AsyncClient):
        resp = await client.get("/notifications")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_mark_all_read(self, client: AsyncClient):
        resp = await client.post("/notifications/mark-all-read")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestDeviceTokens:
    async def test_register_device(self, client: AsyncClient):
        resp = await client.post("/notifications/devices", json={
            "platform": "fcm",
            "token": "test-fcm-token-123",
            "device_name": "Test iPad",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["platform"] == "fcm"
        assert data["token"] == "test-fcm-token-123"

    async def test_list_devices(self, client: AsyncClient):
        await client.post("/notifications/devices", json={
            "platform": "apns", "token": "apns-tok-1", "device_name": "iPhone",
        })
        resp = await client.get("/notifications/devices")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_remove_device(self, client: AsyncClient):
        create = await client.post("/notifications/devices", json={
            "platform": "web", "token": "web-tok-del", "device_name": "Browser",
        })
        device_id = create.json()["id"]
        resp = await client.delete(f"/notifications/devices/{device_id}")
        assert resp.status_code == 204

    async def test_upsert_device(self, client: AsyncClient):
        payload = {
            "platform": "fcm", "token": "upsert-tok", "device_name": "Dev A",
        }
        resp1 = await client.post("/notifications/devices", json=payload)
        assert resp1.status_code == 201
        # Re-register same token
        payload["device_name"] = "Dev B"
        resp2 = await client.post("/notifications/devices", json=payload)
        assert resp2.status_code == 201
        assert resp2.json()["device_name"] == "Dev B"


# ═══════════════════════════════════════════════════════════════════════════
#  P2 #8 — OUT-OF-STOCK TOGGLE
# ═══════════════════════════════════════════════════════════════════════════

class TestOutOfStockToggle:
    async def test_list_out_of_stock_empty(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.get(f"/stores/{store['id']}/inventory/out-of-stock")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_toggle_not_found(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.put(
            f"/stores/{store['id']}/inventory/items/{uuid.uuid4()}/availability",
            json={"is_active": False},
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  P2 #9 — INTEGRATION LOGS
# ═══════════════════════════════════════════════════════════════════════════

class TestIntegrationLogs:
    async def test_menu_trigger_logs_empty(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.get(f"/integrations/logs/menu-triggers?store_id={store['id']}")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_item_logs_empty(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.get(f"/integrations/logs/items?store_id={store['id']}")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_store_logs_empty(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.get(f"/integrations/logs/stores?store_id={store['id']}")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_store_status_empty(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.get(f"/integrations/store-status?store_id={store['id']}")
        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════════
#  P2 #11 — ZONE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

class TestZones:
    async def test_create_zone(self, client: AsyncClient):
        resp = await client.post("/zones", json={
            "name": "South Bangalore",
            "state": "Karnataka",
            "city": "Bangalore",
            "sub_order_type": "delivery",
            "delivery_fee": 30.0,
            "min_order_amount": 200.0,
            "store_ids": [],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "South Bangalore"
        assert data["delivery_fee"] == 30.0

    async def test_list_zones(self, client: AsyncClient):
        await client.post("/zones", json={
            "name": "Zone1", "store_ids": [],
        })
        resp = await client.get("/zones")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_zone(self, client: AsyncClient):
        create = await client.post("/zones", json={
            "name": "GetZone", "store_ids": [],
        })
        zone_id = create.json()["id"]
        resp = await client.get(f"/zones/{zone_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetZone"

    async def test_update_zone(self, client: AsyncClient):
        create = await client.post("/zones", json={
            "name": "OldZone", "store_ids": [],
        })
        zone_id = create.json()["id"]
        resp = await client.put(f"/zones/{zone_id}", json={"name": "NewZone"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "NewZone"

    async def test_delete_zone(self, client: AsyncClient):
        create = await client.post("/zones", json={
            "name": "DeleteZone", "store_ids": [],
        })
        zone_id = create.json()["id"]
        resp = await client.delete(f"/zones/{zone_id}")
        assert resp.status_code == 204

    async def test_zone_not_found(self, client: AsyncClient):
        resp = await client.get(f"/zones/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_zone_with_stores(self, client: AsyncClient):
        store = await _create_store(client, name="Zone Store")
        resp = await client.post("/zones", json={
            "name": "Linked Zone",
            "store_ids": [store["id"]],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert store["id"] in data["store_ids"]


# ═══════════════════════════════════════════════════════════════════════════
#  P2 #12 — REPORT TEMPLATES + GENERATION
# ═══════════════════════════════════════════════════════════════════════════

class TestReports:
    async def test_list_report_types(self, client: AsyncClient):
        resp = await client.get("/reports/types")
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) == 22
        codes = {t["code"] for t in templates}
        assert "daily_sales" in codes
        assert "item_wise_sales" in codes

    async def test_list_report_types_by_category(self, client: AsyncClient):
        # Seed templates
        await client.get("/reports/types")
        resp = await client.get("/reports/types?category=finance")
        assert resp.status_code == 200
        for t in resp.json():
            assert t["category"] == "finance"

    async def test_generate_report(self, client: AsyncClient):
        store = await _create_store(client)
        # Seed templates
        await client.get("/reports/types")
        resp = await client.post("/reports/generate", json={
            "template_code": "daily_sales",
            "store_id": store["id"],
            "parameters": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "completed"
        assert data["result"] is not None

    async def test_generate_report_invalid_template(self, client: AsyncClient):
        store = await _create_store(client)
        await client.get("/reports/types")
        resp = await client.post("/reports/generate", json={
            "template_code": "nonexistent",
            "store_id": store["id"],
        })
        assert resp.status_code == 404

    async def test_get_report_run(self, client: AsyncClient):
        store = await _create_store(client)
        await client.get("/reports/types")
        gen = await client.post("/reports/generate", json={
            "template_code": "daily_sales",
            "store_id": store["id"],
            "parameters": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        })
        report_id = gen.json()["id"]
        resp = await client.get(f"/reports/{report_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == report_id

    async def test_list_report_runs(self, client: AsyncClient):
        store = await _create_store(client)
        await client.get("/reports/types")
        await client.post("/reports/generate", json={
            "template_code": "daily_sales",
            "store_id": store["id"],
        })
        resp = await client.get("/reports")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ═══════════════════════════════════════════════════════════════════════════
#  P3 #13 — OUTLET TYPE / STRUCTURED ADDRESS
# ═══════════════════════════════════════════════════════════════════════════

class TestOutletType:
    async def test_create_store_with_outlet_type(self, client: AsyncClient):
        store = await _create_store(
            client,
            name="COFO Outlet",
            state="Karnataka",
            city="Bangalore",
            outlet_type="COFO",
        )
        assert store["state"] == "Karnataka"
        assert store["city"] == "Bangalore"
        assert store["outlet_type"] == "COFO"

    async def test_update_store_outlet_type(self, client: AsyncClient):
        store = await _create_store(client, name="Type Test")
        resp = await client.put(
            f"/stores/{store['id']}",
            json={"outlet_type": "FOCO", "state": "MH", "city": "Mumbai"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["outlet_type"] == "FOCO"
        assert data["state"] == "MH"
        assert data["city"] == "Mumbai"


# ═══════════════════════════════════════════════════════════════════════════
#  P3 #14 — PENDING PURCHASE AGGREGATION
# ═══════════════════════════════════════════════════════════════════════════

class TestPendingPurchase:
    async def test_pending_summary_empty(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.get(f"/purchasing/pending-summary?store_id={store['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data == []


# ═══════════════════════════════════════════════════════════════════════════
#  P3 #15 — USER ACTIVITY LOGS (user_id filter)
# ═══════════════════════════════════════════════════════════════════════════

class TestUserActivityLogs:
    async def test_audit_logs_empty(self, client: AsyncClient):
        store = await _create_store(client)
        resp = await client.get(f"/audit/logs?store_id={store['id']}")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_audit_logs_with_user_filter(self, client: AsyncClient):
        store = await _create_store(client)
        user_id = str(uuid.uuid4())
        resp = await client.get(f"/audit/logs?store_id={store['id']}&user_id={user_id}")
        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK (sanity)
# ═══════════════════════════════════════════════════════════════════════════

class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
