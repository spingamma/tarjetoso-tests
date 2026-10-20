import os
import pytest
import requests
import uuid

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

def get_auth_token(email: str, name: str, phone: str, is_delivery: bool = False, is_admin: bool = False):
    res = requests.post(
        f"{API_BASE}/auth/e2e-login",
        json={
            "email": email,
            "name": name,
            "phone": phone,
            "is_verified": True,
            "is_delivery": is_delivery,
            "is_admin": is_admin
        },
        timeout=10
    )
    assert res.status_code == 200, f"Error logging in: {res.text}"
    return res.json()["access_token"], res.json()["id"]

def test_delivery_board_rbac_and_claiming_concurrency():
    """
    Verifica:
    1. RBAC: Solo usuarios con is_delivery=True o is_admin=True pueden consultar el tablero.
    2. Concurrencia de toma de pedidos:
       - Repartidor 1 toma el pedido exitosamente (200 OK -> status='en_camino').
       - Repartidor 2 intenta tomar el mismo pedido -> 409 Conflict amigable.
       - El pedido desaparece del listado para otros repartidores.
    """
    unique_id = uuid.uuid4().hex[:6]
    
    # 1. Crear dueño y negocio premium con delivery en La Paz
    owner_token, owner_id = get_auth_token(
        email=f"owner_{unique_id}_Test@example.com",
        name=f"Owner {unique_id} Test",
        phone=f"71{unique_id[:6]}",
        is_delivery=False
    )

    biz_slug = f"restaurante-{unique_id}-test"
    biz_payload = {
        "name": f"Restaurante {unique_id} Test",
        "slug": biz_slug,
        "description": "Comida de prueba para delivery",
        "category": "Comida Rápida & Burgers",
        "subcategories": '["Hamburguesas"]',
        "phone": "59170011223",
        "country": "Bolivia",
        "state": "La Paz",
        "delivery_methods": '["Delivery"]',
        "orders_enabled": "true",
        "ubicacion_url": "https://www.google.com/maps?q=-16.5000,-68.1500"
    }
    biz_res = requests.post(
        f"{API_BASE}/businesses/",
        headers={"Authorization": f"Bearer {owner_token}"},
        data=biz_payload,
        timeout=10
    )
    biz_data = biz_res.json()
    biz_id = biz_data["id"]
    real_slug = biz_data["slug"]

    # Activar plan premium para permitir pedidos en el negocio de test
    from sqlalchemy import create_engine, text
    from datetime import datetime, timedelta
    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://test_user:test_password@localhost:5433/tarjetoso_test")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE business_subscriptions SET premium = TRUE, plan_months = 12, expiration_date = :exp
            WHERE business_id = :bid
        """), {
            "bid": biz_id,
            "exp": (datetime.now() + timedelta(days=365)).isoformat()
        })

    # 2. Cliente crea una orden con Delivery
    client_token, client_id = get_auth_token(
        email=f"client_{unique_id}_Test@example.com",
        name=f"Cliente {unique_id} Test",
        phone=f"73{unique_id[:6]}"
    )
    order_res = requests.post(
        f"{API_BASE}/businesses/{real_slug}/orders",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "customer_name": f"Cliente {unique_id} Test",
            "delivery_method": "Delivery",
            "total_price": 45.0,
            "delivery_cost": 10.0,
            "distance_km": 2.5,
            "delivery_location_url": "https://www.google.com/maps?q=-16.5100,-68.1400",
            "items": [
                {
                    "product_name": "Hamburguesa Doble",
                    "quantity": 1,
                    "price_at_time": 35.0,
                    "subtotal": 35.0
                }
            ]
        },
        timeout=10
    )
    assert order_res.status_code == 200, f"Error creando orden: {order_res.text}"
    order_id = order_res.json()["id"]

    order2_res = requests.post(
        f"{API_BASE}/businesses/{real_slug}/orders",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "customer_name": f"Cliente 2 {unique_id} Test",
            "delivery_method": "Delivery",
            "total_price": 50.0,
            "delivery_cost": 10.0,
            "distance_km": 2.0,
            "delivery_location_url": "https://www.google.com/maps?q=-16.5100,-68.1400",
            "items": [
                {
                    "product_name": "Pizza Personal",
                    "quantity": 1,
                    "price_at_time": 40.0,
                    "subtotal": 40.0
                }
            ]
        },
        timeout=10
    )
    assert order2_res.status_code == 200
    order2_id = order2_res.json()["id"]

    requests.put(
        f"{API_BASE}/businesses/{real_slug}/orders/{order2_id}/status",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "pagado"},
        timeout=10
    )

    # 3. Negocio marca la orden como pagada
    status_res = requests.put(
        f"{API_BASE}/businesses/{real_slug}/orders/{order_id}/status",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "pagado"},
        timeout=10
    )
    assert status_res.status_code == 200, f"Error marcando pagado: {status_res.text}"

    # 4. Verificar RBAC: Usuario normal (sin is_delivery ni is_admin) recibe 403
    forbidden_res = requests.get(
        f"{API_BASE}/delivery/orders",
        headers={"Authorization": f"Bearer {client_token}"},
        timeout=10
    )
    assert forbidden_res.status_code == 403

    # 5. Crear dos repartidores (Driver 1 y Driver 2) en La Paz
    driver1_token, driver1_id = get_auth_token(
        email=f"driver1_{unique_id}_Test@example.com",
        name=f"Driver1 {unique_id} Test",
        phone=f"74{unique_id[:6]}",
        is_delivery=True
    )
    driver2_token, driver2_id = get_auth_token(
        email=f"driver2_{unique_id}_Test@example.com",
        name=f"Driver2 {unique_id} Test",
        phone=f"75{unique_id[:6]}",
        is_delivery=True
    )

    # 6. Driver 1 consulta el tablero con GPS (cerca del restaurante a -16.5020,-68.1510)
    list_res = requests.get(
        f"{API_BASE}/delivery/orders?state=La%20Paz&lat=-16.5020&lng=-68.1510",
        headers={"Authorization": f"Bearer {driver1_token}"},
        timeout=10
    )
    assert list_res.status_code == 200
    available_orders = list_res.json()
    order_ids = [o["id"] for o in available_orders]
    assert order_id in order_ids, "La orden pagada debe figurar en el tablero de delivery"

    target_order = next(o for o in available_orders if o["id"] == order_id)
    assert target_order["distance_to_restaurant_km"] is not None
    assert target_order["distance_to_restaurant_km"] < 3.0, "La distancia debe estar en el rango verde (< 3km)"

    # 7. Driver 1 toma el pedido exitosamente (200 OK)
    claim1_res = requests.post(
        f"{API_BASE}/delivery/orders/{order_id}/claim",
        headers={"Authorization": f"Bearer {driver1_token}"},
        timeout=10
    )
    assert claim1_res.status_code == 200
    assert claim1_res.json()["status"] == "en_camino"
    assert claim1_res.json()["delivery_agent_id"] == driver1_id

    # 7.1. Driver 1 intenta tomar un SEGUNDO pedido teniendo uno en camino -> 400 Bad Request
    claim_second_res = requests.post(
        f"{API_BASE}/delivery/orders/{order2_id}/claim",
        headers={"Authorization": f"Bearer {driver1_token}"},
        timeout=10
    )
    assert claim_second_res.status_code == 400
    assert "Ya tienes un pedido en camino" in claim_second_res.json()["detail"]

    # 8. Driver 2 intenta tomar el MISMO pedido 1 -> debe recibir 409 Conflict amigable
    claim2_res = requests.post(
        f"{API_BASE}/delivery/orders/{order_id}/claim",
        headers={"Authorization": f"Bearer {driver2_token}"},
        timeout=10
    )
    assert claim2_res.status_code == 409
    assert "tomado por otro repartidor" in claim2_res.json()["detail"]

    # 9. En la siguiente consulta de Driver 2, la orden ya no debe aparecer en el panel (desaparece en vivo)
    list2_res = requests.get(
        f"{API_BASE}/delivery/orders?state=La%20Paz",
        headers={"Authorization": f"Bearer {driver2_token}"},
        timeout=10
    )
    assert list2_res.status_code == 200
    remaining_ids = [o["id"] for o in list2_res.json()]
    assert order_id not in remaining_ids, "El pedido tomado debe desaparecer del tablero disponible"

    # ── FASE 2: GESTIÓN DE MIS ENTREGAS Y CONFIRMACIÓN DE ENTREGA ──

    # 10. Driver 1 consulta sus entregas activas
    my_orders_res = requests.get(
        f"{API_BASE}/delivery/my-orders?status=en_camino",
        headers={"Authorization": f"Bearer {driver1_token}"},
        timeout=10
    )
    assert my_orders_res.status_code == 200
    my_active_orders = my_orders_res.json()
    assert any(o["id"] == order_id for o in my_active_orders), "Driver 1 debe ver el pedido en 'Mis Entregas'"

    # 11. Driver 1 emite su ubicación GPS en vivo mientras va en camino
    loc_res = requests.post(
        f"{API_BASE}/delivery/orders/{order_id}/location",
        headers={"Authorization": f"Bearer {driver1_token}"},
        json={"lat": -16.5050, "lng": -68.1450},
        timeout=10
    )
    assert loc_res.status_code == 200
    loc_data = loc_res.json()
    assert loc_data["driver_lat"] == -16.5050
    assert loc_data["driver_lng"] == -68.1450
    assert loc_data["driver_location_updated_at"] is not None

    # Driver 2 no puede emitir GPS para una orden que no le pertenece -> 403
    unauth_loc = requests.post(
        f"{API_BASE}/delivery/orders/{order_id}/location",
        headers={"Authorization": f"Bearer {driver2_token}"},
        json={"lat": -16.5099, "lng": -68.1499},
        timeout=10
    )
    assert unauth_loc.status_code == 403

    # 12. Driver 2 intenta marcar como entregado un pedido ajeno -> 403 Forbidden
    unauth_deliver = requests.post(
        f"{API_BASE}/delivery/orders/{order_id}/deliver",
        headers={"Authorization": f"Bearer {driver2_token}"},
        timeout=10
    )
    assert unauth_deliver.status_code == 403

    # 13. Driver 1 marca el pedido como entregado -> 200 OK
    deliver_res = requests.post(
        f"{API_BASE}/delivery/orders/{order_id}/deliver",
        headers={"Authorization": f"Bearer {driver1_token}"},
        timeout=10
    )
    assert deliver_res.status_code == 200
    delivered_data = deliver_res.json()
    assert delivered_data["status"] == "entregado"
    assert delivered_data["delivered_at"] is not None

    # 14. Driver 1 consulta el resumen con rango de fechas (estilo restaurante)
    today_iso = datetime.now().strftime("%Y-%m-%d")
    summary_res = requests.get(
        f"{API_BASE}/delivery/my-summary?start_date={today_iso}&end_date={today_iso}",
        headers={"Authorization": f"Bearer {driver1_token}"},
        timeout=10
    )
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["completed_count"] >= 1
    assert summary_data["total_earnings"] >= 10.0

    # 15. Driver 1 consulta su lista de historial filtrada por fechas
    history_res = requests.get(
        f"{API_BASE}/delivery/my-orders?status=entregado&start_date={today_iso}&end_date={today_iso}",
        headers={"Authorization": f"Bearer {driver1_token}"},
        timeout=10
    )
    assert history_res.status_code == 200
    history_orders = history_res.json()
    assert any(o["id"] == order_id for o in history_orders)

