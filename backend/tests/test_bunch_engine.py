import json
from datetime import datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.models import Arrival, BunchReport, Line
from app.services.bunch_engine import classify_gap, detect_bunching
from app.services.seed import seed_if_empty


def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "stop_seq": 3, "trip_no": "T1", "vehicle_no": "V1", "actual_arrive": base},
        {"stop_name": "A", "stop_seq": 3, "trip_no": "T2", "vehicle_no": "V2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "stop_seq": 3, "trip_no": "T3", "vehicle_no": "V3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"
    e = events[0]
    assert e.stop_name == "A" and e.stop_seq == 3
    assert (e.earlier_trip, e.earlier_vehicle) == ("T1", "V1")
    assert (e.later_trip, e.later_vehicle) == ("T2", "V2")


def _seeded_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    seed_if_empty(db)
    return db


def _b12_line(db):
    return db.scalars(select(Line).where(Line.code == "B12")).one()


def test_seed_b12_civic_center_event_matches_arrival_table():
    from app.api.reports import run_detection

    db = _seeded_db()
    try:
        line = _b12_line(db)
        table_seq = db.scalars(select(Arrival.stop_seq).where(Arrival.stop_name == "市民中心")).first()
        res = run_detection(line_id=line.id, db=db)
        civic = [e for e in res["events"] if e["stop_name"] == "市民中心" and e["status"] == "bunching"]
        assert civic, "种子 B12 应在市民中心检出串车事件"
        for e in civic:
            assert e["stop_seq"] == table_seq
        assert civic[0]["earlier_trip"] == "T01" and civic[0]["earlier_vehicle"] == "粤A1001"
        assert civic[0]["later_trip"] == "T02" and civic[0]["later_vehicle"] == "粤A1002"
    finally:
        db.close()


def test_trial_suggestions_never_writes_report():
    from app.api.reports import run_detection, suggestions

    db = _seeded_db()
    try:
        line = _b12_line(db)
        report_count = lambda: db.scalar(select(func.count()).select_from(BunchReport))

        tips = suggestions(line_id=line.id, db=db)  # 试算
        assert tips["suggestions"]
        assert report_count() == 0, "试算不得写库"

        res = run_detection(line_id=line.id, db=db)  # 检测成功才写入
        assert res["events"]
        assert report_count() == 1
        stored = json.loads(db.scalars(select(BunchReport)).one().summary_json)
        assert stored == res["events"]
        assert all("stop_seq" in e and "earlier_vehicle" in e and "later_vehicle" in e for e in stored)
    finally:
        db.close()
