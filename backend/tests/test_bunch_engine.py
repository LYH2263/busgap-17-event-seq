from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "stop_seq": 1, "trip_no": "T1", "vehicle_no": "V1", "actual_arrive": base},
        {"stop_name": "A", "stop_seq": 1, "trip_no": "T2", "vehicle_no": "V2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "stop_seq": 1, "trip_no": "T3", "vehicle_no": "V3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"

def test_events_align_with_arrivals_table():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "市民中心", "stop_seq": 1, "trip_no": "T01", "vehicle_no": "粤A1001", "actual_arrive": base},
        {"stop_name": "市民中心", "stop_seq": 1, "trip_no": "T02", "vehicle_no": "粤A1002", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "起点站", "stop_seq": 0, "trip_no": "T01", "vehicle_no": "粤A1001", "actual_arrive": base},
        {"stop_name": "起点站", "stop_seq": 0, "trip_no": "T02", "vehicle_no": "粤A1002", "actual_arrive": base + timedelta(minutes=8)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    civic = [e for e in events if e.stop_name == "市民中心"]
    assert len(civic) == 1
    ev = civic[0]
    assert ev.status == "bunching"
    assert ev.stop_seq == 1
    assert ev.earlier_trip == "T01" and ev.earlier_vehicle == "粤A1001"
    assert ev.later_trip == "T02" and ev.later_vehicle == "粤A1002"
    # 事件按站序排列，与到站表一致
    assert [e.stop_seq for e in events] == sorted(e.stop_seq for e in events)
