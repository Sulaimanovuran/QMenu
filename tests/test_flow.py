"""Сквозная проверка golden path после реструктуризации API (этап 1).

Проходит: login (супер-админ) -> /auth/me -> CRUD компании/филиала/меню/стола
-> mCafe-скан -> заказ гостя -> CRM approve -> KDS cooking/ready ->
CRM served -> refresh/logout токенов.

Запуск: python -m tests.test_flow (из корня репозитория, активировав venv).

Как описано в CLAUDE.md — httpx.AsyncClient + ASGITransport(app=main.app),
без реального uvicorn-сервера. ASGITransport не шлёт lifespan-события, поэтому
Tortoise и сидирование ролей/админа инициализируются вручную перед запросами.
"""
import asyncio

import httpx
from httpx import ASGITransport
from tortoise import Tortoise

from config import settings


async def setup_db() -> None:
    await Tortoise.init(db_url=settings.DB_URL, modules={"models": settings.APPS_MODEL})
    await Tortoise.generate_schemas(safe=True)

    from app.common.roles import seed_roles
    from app.users.service import UserService
    from app.users.repository import UserRepository

    await seed_roles()
    await UserService(UserRepository()).create_admin()


async def run() -> None:
    await setup_db()

    import main as main_module

    transport = ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", follow_redirects=True
    ) as c:
        # ── auth ──────────────────────────────────────────────────────────
        r = await c.post("/auth/login", json={"login": "admin", "password": "admin"})
        assert r.status_code == 200, r.text
        tokens = r.json()["data"]
        access = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        auth = {"Authorization": f"Bearer {access}"}
        print("[ok] login")

        r = await c.get("/auth/me", headers=auth)
        assert r.status_code == 200, r.text
        me = r.json()["data"]
        assert me["role"] == "super_admin", me
        assert me["permissions"], "permissions пустые"
        print("[ok] /auth/me ->", me["role"])

        # ── CRM: компания/филиал ─────────────────────────────────────────
        r = await c.post("/crm/companies", json={"title": "E2E Test Co"}, headers=auth)
        assert r.status_code == 201, r.text
        company_id = r.json()["data"]["id"]

        r = await c.get("/crm/companies", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "pagination" in body and "data" in body, body
        print("[ok] companies CRUD + pagination shape")

        r = await c.post(
            f"/crm/companies/{company_id}/branches",
            json={"title": "Branch 1", "moderation_mode": "strict"},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        branch_id = r.json()["data"]["id"]
        print("[ok] branch created", branch_id)

        # ── CRM: меню ─────────────────────────────────────────────────────
        r = await c.post(
            f"/crm/branches/{branch_id}/categories",
            json={"title": "Напитки", "sort_order": 0},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        category_id = r.json()["data"]["id"]

        r = await c.post(
            f"/crm/branches/{branch_id}/items",
            json={
                "category_id": category_id,
                "title": "Чай",
                "price_minor": 10000,
                "sort_order": 0,
            },
            headers=auth,
        )
        assert r.status_code == 201, r.text
        item_id = r.json()["data"]["id"]
        print("[ok] category + item created")

        # ── CRM: стол ─────────────────────────────────────────────────────
        r = await c.post(
            f"/crm/branches/{branch_id}/tables",
            json={"number": "A1", "zone": "Зал"},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        table = r.json()["data"]
        qr_token = table["qr_token"]
        print("[ok] table created, qr_token issued")

        # ── Public: mCafe-скан (гость = host) ────────────────────────────
        r = await c.post(
            "/public/sessions/scan",
            json={"qr_token": qr_token, "display_name": "Гость"},
        )
        assert r.status_code == 200, r.text
        scan = r.json()["data"]
        device_token = scan["device_token"]
        session_id = scan["session"]["id"]
        assert scan["is_host"] is True
        assert scan["can_order"] is True
        print("[ok] scan -> host, can_order")

        # ── Public: заказ гостя ───────────────────────────────────────────
        r = await c.post(
            f"/public/sessions/{session_id}/orders",
            json={
                "device_token": device_token,
                "items": [{"menu_item_id": item_id, "qty": 2}],
            },
            headers={"X-Device-Token": device_token},
        )
        assert r.status_code == 200, r.text
        order = r.json()["data"]
        order_id = order["id"]
        assert order["status"] == "pending", order
        assert order["total_minor"] == 20000, order
        print("[ok] order created, status=pending, total=20000")

        # ── CRM: модерация ────────────────────────────────────────────────
        r = await c.get(f"/crm/branches/{branch_id}/moderation", headers=auth)
        assert r.status_code == 200, r.text
        assert any(o["id"] == order_id for o in r.json()["data"])

        r = await c.post(f"/crm/branches/{branch_id}/orders/{order_id}/approve", headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "approved"
        print("[ok] order approved")

        # ── KDS ───────────────────────────────────────────────────────────
        r = await c.get(f"/kds/branches/{branch_id}/orders", headers=auth)
        assert r.status_code == 200, r.text
        assert any(o["id"] == order_id for o in r.json()["data"])

        r = await c.post(f"/kds/branches/{branch_id}/orders/{order_id}/cooking", headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "cooking"

        r = await c.post(f"/kds/branches/{branch_id}/orders/{order_id}/ready", headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "ready"
        print("[ok] KDS cooking -> ready")

        # ── CRM: served ───────────────────────────────────────────────────
        r = await c.post(f"/crm/branches/{branch_id}/orders/{order_id}/served", headers=auth)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "served"
        print("[ok] order served")

        # ── Официант: ограниченная модерация ──────────────────────────────
        r = await c.post(
            "/auth/reg",
            json={
                "login": "waiter1",
                "full_name": "Официант Иванов",
                "phone": None,
                "password_hash": "waiterpass",
                "is_active": True,
            },
        )
        assert r.status_code == 200, r.text
        waiter_user_id = r.json()["data"]["id"]

        r = await c.post(
            f"/crm/branches/{branch_id}/employees",
            json={"user_id": waiter_user_id, "role_code": "waiter"},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        waiter_employee_id = r.json()["data"]["id"]

        r = await c.post("/auth/login", json={"login": "waiter1", "password": "waiterpass"})
        assert r.status_code == 200, r.text
        waiter_auth = {"Authorization": f"Bearer {r.json()['data']['access_token']}"}

        r = await c.get("/auth/me", headers=waiter_auth)
        assert r.status_code == 200, r.text
        waiter_me = r.json()["data"]
        assert waiter_me["role"] == "waiter", waiter_me
        assert set(waiter_me["permissions"]) == {"orders.read", "orders.moderate"}, waiter_me
        print("[ok] waiter role + limited permissions")

        # официант не может управлять меню (ограниченные права)
        r = await c.post(
            f"/crm/branches/{branch_id}/categories",
            json={"title": "Should fail", "sort_order": 0},
            headers=waiter_auth,
        )
        assert r.status_code == 403, r.text
        print("[ok] waiter forbidden from menu management")

        # новый стол/скан/заказ, чтобы официант мог его одобрить
        r = await c.post(
            f"/crm/branches/{branch_id}/tables",
            json={"number": "A2", "zone": "Зал"},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        qr_token_2 = r.json()["data"]["qr_token"]

        r = await c.post("/public/sessions/scan", json={"qr_token": qr_token_2, "display_name": "Гость2"})
        assert r.status_code == 200, r.text
        scan2 = r.json()["data"]
        device_token_2 = scan2["device_token"]
        session_id_2 = scan2["session"]["id"]

        r = await c.post(
            f"/public/sessions/{session_id_2}/orders",
            json={"device_token": device_token_2, "items": [{"menu_item_id": item_id, "qty": 1}]},
            headers={"X-Device-Token": device_token_2},
        )
        assert r.status_code == 200, r.text
        order_id_2 = r.json()["data"]["id"]

        # официант видит очередь модерации и подтверждает заказ
        r = await c.get(f"/crm/branches/{branch_id}/moderation", headers=waiter_auth)
        assert r.status_code == 200, r.text
        assert any(o["id"] == order_id_2 for o in r.json()["data"])

        r = await c.post(f"/crm/branches/{branch_id}/orders/{order_id_2}/approve", headers=waiter_auth)
        assert r.status_code == 200, r.text
        approved2 = r.json()["data"]
        assert approved2["status"] == "approved"
        assert approved2["moderated_by"] == waiter_employee_id, approved2
        print("[ok] waiter approve -> order attached to waiter's employee_id")

        # ── Ошибки: формат {success,message,code} ────────────────────────
        r = await c.get("/crm/companies/999999", headers=auth)
        assert r.status_code == 404, r.text
        err = r.json()
        assert err["success"] is False and err["code"] == "NOT_FOUND", err
        print("[ok] 404 error envelope")

        # ── refresh/logout ────────────────────────────────────────────────
        r = await c.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
        assert r.status_code == 200, r.text
        new_tokens = r.json()["data"]

        # старый refresh уже отозван ротацией -> должен быть невалиден
        r = await c.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
        assert r.status_code == 401, r.text
        print("[ok] refresh rotation revokes old token")

        r = await c.post(
            "/auth/logout", headers={"Authorization": f"Bearer {new_tokens['refresh_token']}"}
        )
        assert r.status_code == 200, r.text

        r = await c.post(
            "/auth/refresh", headers={"Authorization": f"Bearer {new_tokens['refresh_token']}"}
        )
        assert r.status_code == 401, r.text
        print("[ok] logout revokes refresh token")

    print("\nALL CHECKS PASSED")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run())
