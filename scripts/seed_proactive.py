import json
import os

EVENTS_FILE = "data/events.json"

events = [
    {
        "id": "evt_logistics_001",
        "status": "pending",
        "user_id": "demo_user",
        "session_id": "demo_session_1",
        "event_type": "logistics",
        "data": {"order_id": "ORD2026001", "delay_days": 2, "amount": 5},
    },
    {
        "id": "evt_inventory_001",
        "status": "pending",
        "user_id": "demo_user",
        "session_id": "demo_session_1",
        "event_type": "inventory",
        "data": {"title": "机械键盘K8"},
    },
    {
        "id": "evt_promotion_001",
        "status": "pending",
        "user_id": "demo_user",
        "session_id": "demo_session_1",
        "event_type": "promotion",
        "data": {"title": "蓝牙耳机Pro", "price": 299, "origin": 399, "stock": 10},
    },
]

os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
with open(EVENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=2)

print(f"seeded {len(events)} events -> {EVENTS_FILE}")
for e in events:
    print(f"  {e['id']} [{e['event_type']}] {e['data'].get('title', e['data'].get('order_id', ''))}")
