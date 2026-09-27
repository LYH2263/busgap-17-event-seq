"""API 级：检测事件对到站表、试算不写库、种子 B12 市民中心站序一致。"""
import os
# 导入 app 前兜底：无 DATABASE_URL 时用 sqlite，避免导入期依赖 psycopg2
os.environ.setdefault("DATABASE_URL", "sqlite://")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.seed import seed_if_empty

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

db = TestingSessionLocal()
seed_if_empty(db)
db.close()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def _report_count() -> int:
    return len(client.get("/api/reports").json())

def test_run_detection_events_align_with_arrivals():
    before = _report_count()
    r = client.post("/api/reports/run", params={"line_id": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is False and body["id"]
    # 检测成功才写入报告
    assert _report_count() == before + 1

    arrivals = client.get("/api/arrivals", params={"line_id": 1}).json()
    seq_by_stop = {a["stop_name"]: a["stop_seq"] for a in arrivals}
    vehicle_by_trip = {t["trip_no"]: t["vehicle_no"] for t in client.get("/api/trips", params={"line_id": 1}).json()}

    events = body["events"]
    assert events
    for e in events:
        # 每条事件字段齐全，且站序与到站表一致
        for field in ("stop_name", "stop_seq", "earlier_trip", "earlier_vehicle",
                      "later_trip", "later_vehicle", "gap_min", "status"):
            assert field in e, field
        assert e["stop_seq"] == seq_by_stop[e["stop_name"]]
        assert e["earlier_vehicle"] == vehicle_by_trip[e["earlier_trip"]]
        assert e["later_vehicle"] == vehicle_by_trip[e["later_trip"]]
    # 事件按站序排列
    assert [e["stop_seq"] for e in events] == sorted(e["stop_seq"] for e in events)

def test_seed_b12_civic_center_bunching_seq_matches_arrivals():
    events = client.post("/api/reports/run", params={"line_id": 1}).json()["events"]
    civic = [e for e in events if e["stop_name"] == "市民中心" and e["status"] == "bunching"]
    assert civic, "种子 B12 应在市民中心检出串车"
    ev = civic[0]
    arrivals = client.get("/api/arrivals", params={"line_id": 1}).json()
    civic_seq = {a["stop_seq"] for a in arrivals if a["stop_name"] == "市民中心"}
    assert civic_seq == {ev["stop_seq"]} == {1}
    assert (ev["earlier_trip"], ev["earlier_vehicle"]) == ("T01", "粤A1001")
    assert (ev["later_trip"], ev["later_vehicle"]) == ("T02", "粤A1002")
    assert ev["gap_min"] == 2.0

def test_dry_run_does_not_write():
    before = _report_count()
    r = client.post("/api/reports/run", params={"line_id": 1, "dry_run": "true"})
    assert r.status_code == 200
    assert r.json()["dry_run"] is True and r.json()["id"] is None
    assert r.json()["events"]
    assert _report_count() == before

def test_suggestions_do_not_write():
    before = _report_count()
    r = client.get("/api/reports/suggestions", params={"line_id": 1})
    assert r.status_code == 200
    assert r.json()["suggestions"]
    assert _report_count() == before
