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
    from app.common.seed import seed_restaurant_types
    from app.users.service import UserService
    from app.users.repository import UserRepository

    await seed_roles()
    await seed_restaurant_types()
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
        r = await c.post(
            "/crm/companies",
            json={
                "title": "E2E Test Co",
                "short_description": "Тестовая сеть",
                "type_codes": ["coffee", "restaurant"],
                "status": "active",
                "is_published": True,
            },
            headers=auth,
        )
        assert r.status_code == 201, r.text
        company = r.json()["data"]
        company_id = company["id"]
        assert company["slug"], "slug компании не сгенерирован"
        assert company["type_codes"] == ["coffee", "restaurant"], company
        print("[ok] company created, slug =", company["slug"])

        # PATCH компании
        r = await c.patch(
            f"/crm/companies/{company_id}",
            json={"description": "Обновлённое описание"},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["description"] == "Обновлённое описание"

        r = await c.get("/crm/companies", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "pagination" in body and "data" in body, body
        print("[ok] companies CRUD + pagination shape")

        r = await c.post(
            f"/crm/companies/{company_id}/branches",
            json={
                "title": "Branch 1",
                "city": "Бишкек",
                "moderation_mode": "strict",
                "schedule": [
                    {"day_of_week": 1, "opens_at": "09:00", "closes_at": "22:00", "is_closed": False}
                ],
                "status": "active",
                "is_published": True,
            },
            headers=auth,
        )
        assert r.status_code == 201, r.text
        branch = r.json()["data"]
        branch_id = branch["id"]
        assert branch["slug"], "slug филиала не сгенерирован"
        assert branch["city"] == "Бишкек", branch
        assert len(branch["schedule"]) == 1, branch
        print("[ok] branch created", branch_id, "slug =", branch["slug"])

        company_slug = company["slug"]
        branch_slug = branch["slug"]

        # ── CRM: меню (публикуем для guest-каталога) ──────────────────────
        r = await c.post(
            f"/crm/branches/{branch_id}/categories",
            json={"title": "Напитки", "sort_order": 0, "is_published": True},
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
                "weight": 250,
                "weight_unit": "ml",
                "is_published": True,
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
        assert table["title"] == "A1", table
        print("[ok] table created, qr_token issued")

        # ── 2B: загрузка картинки (multipart) ─────────────────────────────
        png_1x1 = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000a49444154789c6360000002000154a24f5f0000000049454e44ae42"
            "6082"
        )
        r = await c.post(
            "/crm/uploads",
            headers=auth,
            files={"file": ("dot.png", png_1x1, "image/png")},
        )
        assert r.status_code == 200, r.text
        image_url = r.json()["data"]["image_url"]
        assert image_url.endswith(".png"), image_url
        print("[ok] image upload ->", image_url)

        # проставим картинку блюду через PATCH
        r = await c.patch(
            f"/crm/branches/{branch_id}/items/{item_id}",
            json={"image_url": image_url},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["image_url"] == image_url

        # отклонить не-картинку
        r = await c.post(
            "/crm/uploads",
            headers=auth,
            files={"file": ("x.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400, r.text
        assert r.json()["code"] == "VALIDATION_ERROR", r.text
        print("[ok] non-image upload rejected with field_errors")

        # ── 2B: публичный Guest-каталог ───────────────────────────────────
        r = await c.get("/public/restaurant-types")
        assert r.status_code == 200, r.text
        assert any(t["code"] == "coffee" for t in r.json()["data"])

        r = await c.get("/public/places?type_ids=coffee")
        assert r.status_code == 200, r.text
        places = r.json()["data"]
        assert any(p["slug"] == company_slug for p in places), places
        assert "pagination" in r.json()
        print("[ok] public places list + type filter")

        r = await c.get(f"/public/places/{company_slug}")
        assert r.status_code == 200, r.text
        place = r.json()["data"]
        assert place["type_title"], place
        assert any(b["slug"] == branch_slug for b in place["branches"]), place
        print("[ok] public place details")

        r = await c.get(f"/public/branches/{branch_slug}")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["place"]["slug"] == company_slug

        r = await c.get(f"/public/branches/{branch_slug}/menu")
        assert r.status_code == 200, r.text
        menu = r.json()["data"]
        assert menu["categories"], "меню пустое"
        assert menu["categories"][0]["items"][0]["title"] == "Чай"
        print("[ok] public preview menu")

        r = await c.get(f"/public/branches/{branch_slug}/menu/search?search=Ча")
        assert r.status_code == 200, r.text
        assert any(i["id"] == item_id for i in r.json()["data"])

        r = await c.get(f"/public/branches/{branch_slug}/menu/items/{item_id}")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["category"]["id"] == category_id
        print("[ok] public menu search + item details")

        r = await c.get(f"/public/tables/{qr_token}")
        assert r.status_code == 200, r.text
        preview = r.json()["data"]
        assert preview["table_title"] == "A1"
        assert preview["place"]["slug"] == company_slug
        print("[ok] public table preview by QR")

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

        # ════════════════ 2C: CRM-расширения ══════════════════════════════

        # ── availability / стоп-лист ──────────────────────────────────────
        r = await c.post(
            f"/crm/branches/{branch_id}/items/{item_id}/availability",
            json={"is_available": False, "status": "stop_list"},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "stop_list"

        r = await c.post(
            f"/public/sessions/{session_id}/orders",
            json={"device_token": device_token, "items": [{"menu_item_id": item_id, "qty": 1}]},
            headers={"X-Device-Token": device_token},
        )
        assert r.status_code == 400, "стоп-лист должен блокировать заказ"

        r = await c.post(
            f"/crm/branches/{branch_id}/items/{item_id}/availability",
            json={"is_available": True, "status": "active"},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        print("[ok] availability toggle + stop-list blocks order")

        # ── reorder категорий/блюд ────────────────────────────────────────
        r = await c.post(
            f"/crm/branches/{branch_id}/categories",
            json={"title": "Горячее", "sort_order": 5},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        category_id_2 = r.json()["data"]["id"]

        r = await c.post(
            f"/crm/branches/{branch_id}/categories/reorder",
            json={"category_ids": [category_id_2, category_id]},
            headers=auth,
        )
        assert r.status_code == 200, r.text

        r = await c.get(f"/crm/branches/{branch_id}/categories", headers=auth)
        cats = r.json()["data"]
        assert cats[0]["id"] == category_id_2, cats

        r = await c.post(
            f"/crm/branches/{branch_id}/items/reorder",
            json={"category_id": category_id, "item_ids": [item_id]},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        print("[ok] categories/items reorder")

        # чужая категория в reorder -> 400
        r = await c.post(
            f"/crm/branches/{branch_id}/categories/reorder",
            json={"category_ids": [999999]},
            headers=auth,
        )
        assert r.status_code == 400, r.text

        # удалить категорию с блюдами нельзя
        r = await c.delete(f"/crm/branches/{branch_id}/categories/{category_id}", headers=auth)
        assert r.status_code == 409 and r.json()["code"] == "CATEGORY_HAS_ITEMS", r.text
        print("[ok] CATEGORY_HAS_ITEMS guard")

        # ── bulk-столы, regenerate-qr, qr-данные ──────────────────────────
        r = await c.post(
            f"/crm/branches/{branch_id}/tables/bulk",
            json={"zone": "Терраса", "prefix": "T", "from": 1, "to": 3, "seats": 2},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        bulk_tables = r.json()["data"]
        assert len(bulk_tables) == 3 and bulk_tables[0]["number"] == "T-1", bulk_tables

        # повторный bulk с теми же номерами -> 409
        r = await c.post(
            f"/crm/branches/{branch_id}/tables/bulk",
            json={"zone": "Терраса", "prefix": "T", "from": 1, "to": 3},
            headers=auth,
        )
        assert r.status_code == 409 and r.json()["code"] == "TABLE_NUMBER_TAKEN", r.text

        t1 = bulk_tables[0]
        old_qr = t1["qr_token"]
        r = await c.post(
            f"/crm/branches/{branch_id}/tables/{t1['id']}/regenerate-qr", headers=auth
        )
        assert r.status_code == 200, r.text
        new_qr = r.json()["data"]["qr_token"]
        assert new_qr != old_qr

        r = await c.get(f"/crm/branches/{branch_id}/tables/{t1['id']}/qr", headers=auth)
        assert r.status_code == 200 and new_qr in r.json()["data"]["public_url"], r.text

        # старый QR больше не работает для гостя
        r = await c.get(f"/public/tables/{old_qr}")
        assert r.status_code == 404, r.text
        print("[ok] bulk tables + regenerate-qr + qr data")

        # ── копирование меню в новый филиал ───────────────────────────────
        r = await c.post(
            f"/crm/companies/{company_id}/branches",
            json={"title": "Branch 2", "city": "Ош", "moderation_mode": "strict"},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        branch_id_2 = r.json()["data"]["id"]

        r = await c.post(
            f"/crm/branches/{branch_id_2}/menu/copy-from",
            json={"source_branch_id": branch_id, "copy_categories": True,
                  "copy_items": True, "replace_existing": False},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        copy_result = r.json()["data"]
        assert copy_result["copied_categories"] == 2, copy_result
        assert copy_result["copied_items"] == 1, copy_result

        r = await c.get(f"/crm/branches/{branch_id_2}/items", headers=auth)
        assert r.json()["pagination"]["total"] == 1, r.text
        print("[ok] menu copy-from")

        # ── /crm/users CRUD + reset-password ──────────────────────────────
        r = await c.post(
            "/crm/users",
            json={"login": "manager2", "password": "pass1", "full_name": "Менеджер Второй",
                  "phone": "+996700000001", "is_active": True},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        u2_id = r.json()["data"]["id"]

        # дубликат логина -> 409 + field_errors
        r = await c.post(
            "/crm/users",
            json={"login": "manager2", "password": "x", "full_name": "Дубль"},
            headers=auth,
        )
        assert r.status_code == 409 and "login" in r.json().get("field_errors", {}), r.text

        r = await c.get("/crm/users?search=manager2", headers=auth)
        assert any(u["id"] == u2_id for u in r.json()["data"]), r.text

        r = await c.patch(f"/crm/users/{u2_id}", json={"full_name": "Переименован"}, headers=auth)
        assert r.status_code == 200 and r.json()["data"]["full_name"] == "Переименован", r.text

        r = await c.post(f"/crm/users/{u2_id}/reset-password", json={"password": "pass2"}, headers=auth)
        assert r.status_code == 200, r.text
        r = await c.post("/auth/login", json={"login": "manager2", "password": "pass2"})
        assert r.status_code == 200, "новый пароль должен работать"
        print("[ok] /crm/users CRUD + reset-password")

        # ── сотрудники уровня компании ────────────────────────────────────
        r = await c.post(
            f"/crm/companies/{company_id}/employees",
            json={"user_id": u2_id, "role": "owner"},
            headers=auth,  # супер-админ может назначить owner
        )
        assert r.status_code == 201, r.text
        company_emp_id = r.json()["data"]["id"]

        r = await c.get(f"/crm/companies/{company_id}/employees", headers=auth)
        assert any(e["id"] == company_emp_id for e in r.json()["data"]), r.text

        r = await c.get(f"/crm/employees/{waiter_employee_id}", headers=auth)
        assert r.status_code == 200 and r.json()["data"]["role"]["code"] == "waiter", r.text

        r = await c.delete(f"/crm/companies/{company_id}/employees/{company_emp_id}", headers=auth)
        assert r.status_code == 204, r.text
        print("[ok] company employees + employee detail")

        # ── PATCH сотрудника филиала (роль/статус) ────────────────────────
        r = await c.patch(
            f"/crm/branches/{branch_id}/employees/{waiter_employee_id}",
            json={"status": "blocked"},
            headers=auth,
        )
        assert r.status_code == 200 and r.json()["data"]["status"] == "blocked", r.text
        # заблокированный официант больше не модерирует
        r = await c.get(f"/crm/branches/{branch_id}/moderation", headers=waiter_auth)
        assert r.status_code == 403, r.text
        r = await c.patch(
            f"/crm/branches/{branch_id}/employees/{waiter_employee_id}",
            json={"status": "active"},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        print("[ok] employee block/unblock")

        # ── CRM-сессии: pending-гость -> decide -> rename -> leave ────────
        r = await c.post("/public/sessions/scan", json={"qr_token": qr_token, "display_name": "Третий"})
        assert r.status_code == 200, r.text
        scan3 = r.json()["data"]
        device_token_3 = scan3["device_token"]
        p3_id = scan3["participant"]["id"]
        assert scan3["participant"]["status"] == "pending", scan3

        r = await c.post(
            f"/crm/sessions/{session_id}/participants/{p3_id}/decide",
            json={"decision": "approved"},
            headers=auth,
        )
        assert r.status_code == 200 and r.json()["data"]["status"] == "approved", r.text

        r = await c.patch(
            f"/public/sessions/{session_id}/participants/me",
            json={"name": "Даурен"},
            headers={"X-Device-Token": device_token_3},
        )
        assert r.status_code == 200 and r.json()["data"]["display_name"] == "Даурен", r.text

        r = await c.post(
            f"/public/sessions/{session_id}/participants/me/leave",
            headers={"X-Device-Token": device_token_3},
        )
        assert r.status_code == 200 and r.json()["data"]["status"] == "left", r.text
        print("[ok] CRM decide + guest rename/leave")

        # ── отмена заказов: гостем и персоналом ───────────────────────────
        r = await c.post(
            f"/public/sessions/{session_id}/orders",
            json={"device_token": device_token, "items": [{"menu_item_id": item_id, "qty": 1}]},
            headers={"X-Device-Token": device_token},
        )
        assert r.status_code == 200, r.text
        cancel_order_id = r.json()["data"]["id"]

        r = await c.post(
            f"/public/sessions/{session_id}/orders/{cancel_order_id}/cancel",
            json={"reason": "Передумали"},
            headers={"X-Device-Token": device_token},
        )
        assert r.status_code == 200 and r.json()["data"]["status"] == "cancelled", r.text

        r = await c.post(
            f"/public/sessions/{session_id}/orders",
            json={"device_token": device_token, "items": [{"menu_item_id": item_id, "qty": 1}]},
            headers={"X-Device-Token": device_token},
        )
        staff_cancel_order_id = r.json()["data"]["id"]
        r = await c.post(
            f"/crm/branches/{branch_id}/orders/{staff_cancel_order_id}/cancel",
            json={"reason": "Гость отменил заказ"},
            headers=auth,
        )
        assert r.status_code == 200 and r.json()["data"]["status"] == "cancelled", r.text
        print("[ok] guest cancel + staff cancel")

        # ── CRM: список заказов + деталка ─────────────────────────────────
        r = await c.get(f"/crm/branches/{branch_id}/orders?status=served", headers=auth)
        assert r.status_code == 200, r.text
        assert any(o["id"] == order_id for o in r.json()["data"]), r.text
        assert r.json()["pagination"]["total"] >= 1

        r = await c.get(f"/crm/orders/{order_id}", headers=auth)
        assert r.status_code == 200 and r.json()["data"]["id"] == order_id, r.text
        print("[ok] CRM orders list + flat detail")

        # ── настройки филиала: авто-модерация и вход без хоста ────────────
        r = await c.get(f"/crm/branches/{branch_id}/settings", headers=auth)
        assert r.status_code == 200 and r.json()["data"]["moderation_mode"] == "strict", r.text

        r = await c.patch(
            f"/crm/branches/{branch_id}/settings",
            json={"moderation_mode": "auto", "allow_guest_join_without_host": True},
            headers=auth,
        )
        assert r.status_code == 200 and r.json()["data"]["moderation_mode"] == "auto", r.text

        # новый гость сразу approved (без подтверждения хостом)
        r = await c.post("/public/sessions/scan", json={"qr_token": qr_token, "display_name": "Четвёртый"})
        scan4 = r.json()["data"]
        assert scan4["participant"]["status"] == "approved", scan4
        assert scan4["can_order"] is True

        # заказ минует модерацию (auto) -> сразу approved
        r = await c.post(
            f"/public/sessions/{session_id}/orders",
            json={"device_token": scan4["device_token"], "items": [{"menu_item_id": item_id, "qty": 1}]},
            headers={"X-Device-Token": scan4["device_token"]},
        )
        assert r.status_code == 200 and r.json()["data"]["status"] == "approved", r.text

        # вернуть строгий режим
        r = await c.patch(
            f"/crm/branches/{branch_id}/settings",
            json={"moderation_mode": "strict", "allow_guest_join_without_host": False},
            headers=auth,
        )
        assert r.status_code == 200, r.text
        print("[ok] branch settings: auto moderation + join without host")

        # ── сводка филиала ────────────────────────────────────────────────
        r = await c.get(f"/crm/branches/{branch_id}/summary", headers=auth)
        assert r.status_code == 200, r.text
        summary = r.json()["data"]
        assert summary["tables_count"] == 5, summary          # A1, A2, T-1..T-3
        assert summary["active_sessions_count"] >= 2, summary
        print("[ok] branch summary")

        # ── CRM-сессии: список, деталка, закрытие ─────────────────────────
        r = await c.get(f"/crm/branches/{branch_id}/sessions?status=open", headers=auth)
        assert r.status_code == 200, r.text
        assert any(s["id"] == session_id_2 for s in r.json()["data"]), r.text

        r = await c.get(f"/crm/sessions/{session_id}", headers=auth)
        assert r.status_code == 200, r.text
        sdetail = r.json()["data"]
        assert sdetail["participants"] and sdetail["orders"], sdetail

        r = await c.post(f"/crm/sessions/{session_id_2}/close", headers=auth)
        assert r.status_code == 200 and r.json()["data"]["status"] == "closed", r.text
        print("[ok] CRM sessions list/detail/close")

        # ── KDS: мои филиалы + DTO + деталка ──────────────────────────────
        r = await c.get("/kds/branches/my", headers=auth)
        assert r.status_code == 200 and len(r.json()["data"]) >= 2, r.text

        r = await c.get(f"/kds/branches/{branch_id}/orders", headers=auth)
        assert r.status_code == 200, r.text
        kds_orders = r.json()["data"]
        assert kds_orders, "KDS-доска пуста"
        assert "table_title" in kds_orders[0] and "items" in kds_orders[0], kds_orders[0]
        assert "title_snapshot" in kds_orders[0]["items"][0], kds_orders[0]
        assert "total_minor" not in kds_orders[0], "KDS не должен видеть CRM-поля"

        r = await c.get(f"/kds/branches/{branch_id}/orders/{order_id_2}", headers=auth)
        assert r.status_code == 200 and r.json()["data"]["id"] == order_id_2, r.text
        print("[ok] KDS my branches + KdsOrder DTO + detail")

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
