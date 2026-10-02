"""여행 일정표 데이터 처리 로직 (Streamlit 의존성 없음)."""

import csv
import io
import json
import re
import uuid
from datetime import date, timedelta
from urllib.parse import quote

DATA_VERSION = 1
WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]
CATEGORIES = {"관광": "🏛️", "식사": "🍽️", "이동": "🚌", "쇼핑": "🛍️", "기타": "📌"}
DEFAULT_CATEGORY = "기타"

GMAPS_SEARCH = "https://www.google.com/maps/search/?api=1&query="
GMAPS_DIR = "https://www.google.com/maps/dir/?api=1"

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# ---------------- 생성 ----------------

def new_trip(start: date | None = None) -> dict:
    """빈 여행 데이터를 만든다. 기본 기간은 시작일부터 2박 3일."""
    start = start or date.today()
    return {
        "version": DATA_VERSION,
        "title": "",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=2)).isoformat(),
        "schedules": [],
        "lodgings": [],
    }


def make_schedule(
    date_str: str,
    start_time: str,
    title: str,
    end_time: str = "",
    place: str = "",
    address: str = "",
    memo: str = "",
    category: str = DEFAULT_CATEGORY,
) -> dict:
    """일정 항목 하나를 만든다. 날짜는 'YYYY-MM-DD', 시간은 'HH:MM' 문자열."""
    return {
        "id": str(uuid.uuid4()),
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "title": title.strip(),
        "category": category if category in CATEGORIES else DEFAULT_CATEGORY,
        "place": place.strip(),
        "address": address.strip(),
        "memo": memo.strip(),
    }


def make_lodging(date_str: str, name: str, address: str = "", memo: str = "") -> dict:
    """숙박 항목 하나. date_str은 '그날 밤 묵는' 날짜."""
    return {
        "id": str(uuid.uuid4()),
        "date": date_str,
        "name": name.strip(),
        "address": address.strip(),
        "memo": memo.strip(),
    }


def make_lodgings(first_night: date, last_night: date, name: str, address: str = "", memo: str = "") -> list[dict]:
    """연박 등록: first_night~last_night(포함) 각 밤마다 숙박 항목을 만든다."""
    return [make_lodging(d.isoformat(), name, address, memo) for d in date_range(first_night, last_night)]


# ---------------- 날짜/시간 ----------------

def date_range(start: date, end: date) -> list[date]:
    """start~end(포함) 날짜 목록. end < start 이면 빈 리스트."""
    if end < start:
        return []
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def format_day_label(day_index: int, d: date) -> str:
    """'Day 1 · 10/10 (토)' 형식. day_index는 0부터 시작."""
    return f"Day {day_index + 1} · {d.month:02d}/{d.day:02d} ({WEEKDAYS_KO[d.weekday()]})"


def format_date_ko(date_str: str) -> str:
    """'2026-10-10' → '10/10 (토)'."""
    d = date.fromisoformat(date_str)
    return f"{d.month:02d}/{d.day:02d} ({WEEKDAYS_KO[d.weekday()]})"


def nights_days(start: date, end: date) -> tuple[int, int] | None:
    """(박, 일). 기간이 잘못되면 None."""
    if end < start:
        return None
    nights = (end - start).days
    return nights, nights + 1


def day_number(trip: dict, date_str: str) -> int | None:
    """여행 기간 내 날짜면 1부터 시작하는 Day 번호, 아니면 None."""
    start = date.fromisoformat(trip["start_date"])
    end = date.fromisoformat(trip["end_date"])
    d = date.fromisoformat(date_str)
    if start <= d <= end:
        return (d - start).days + 1
    return None


def is_valid_time_range(start_time: str, end_time: str) -> bool:
    """종료 시간이 없거나 시작 시간 이후면 True. ('HH:MM'은 문자열 비교로 순서가 맞다)"""
    return not end_time or end_time >= start_time


def format_time_range(schedule: dict) -> str:
    """'09:00–10:30', 종료 시간이 없으면 '09:00'."""
    if schedule.get("end_time"):
        return f"{schedule['start_time']}–{schedule['end_time']}"
    return schedule["start_time"]


# ---------------- 조회/정렬 ----------------

def sort_schedules(schedules: list[dict]) -> list[dict]:
    """날짜, 시작 시간, 종료 시간 순으로 정렬한 새 리스트."""
    return sorted(schedules, key=lambda s: (s["date"], s["start_time"], s.get("end_time") or ""))


def schedules_by_date(schedules: list[dict], date_str: str) -> list[dict]:
    """해당 날짜의 일정을 시간순으로 반환."""
    return sort_schedules([s for s in schedules if s["date"] == date_str])


def lodgings_by_date(lodgings: list[dict], date_str: str) -> list[dict]:
    return [l for l in lodgings if l["date"] == date_str]


def lodging_conflicts(lodgings: list[dict], dates: list[str]) -> list[dict]:
    """주어진 밤(ISO 날짜)들에 이미 등록된 숙박 (날짜순)."""
    wanted = set(dates)
    return sorted((l for l in lodgings if l["date"] in wanted), key=lambda l: l["date"])


def group_lodging_stays(lodgings: list[dict]) -> list[dict]:
    """같은 숙소(숙소명·주소·메모)의 연속된 밤을 하나의 숙박 기간으로 묶는다.

    반환: [{"name", "address", "memo", "first", "last", "nights"}] (첫 밤 날짜순)
    """
    def same(l):
        return l["name"], l.get("address", ""), l.get("memo", "")

    stays: list[dict] = []
    for l in sorted(lodgings, key=lambda l: (same(l), l["date"])):
        prev = stays[-1] if stays else None
        if prev and prev["_key"] == same(l):
            gap = (date.fromisoformat(l["date"]) - date.fromisoformat(prev["last"])).days
            if gap == 0:  # 같은 밤 중복은 한 번만
                continue
            if gap == 1:
                prev["last"] = l["date"]
                prev["nights"] += 1
                continue
        stays.append({"_key": same(l), "name": l["name"], "address": l.get("address", ""),
                      "memo": l.get("memo", ""), "first": l["date"], "last": l["date"], "nights": 1})
    for stay in stays:
        del stay["_key"]
    return sorted(stays, key=lambda s: (s["first"], s["name"]))


def out_of_range(items: list[dict], start: date, end: date) -> list[dict]:
    """여행 기간 밖 날짜를 가진 항목(날짜순). 기간 변경 시 삭제하지 않고 따로 보여주기 위함."""
    s, e = start.isoformat(), end.isoformat()
    return sorted((i for i in items if not s <= i["date"] <= e), key=lambda i: i["date"])


def find_overlaps(schedules: list[dict]) -> set[str]:
    """같은 날 시간이 겹치는 일정 id 집합.

    종료 시간이 없는 일정은 시작 시각 한 점으로 보고, 다른 일정 구간 안에 있거나
    시작 시각이 같으면 겹침으로 본다. 한 일정이 끝나는 시각에 다음 일정이 시작하면 겹치지 않는다.
    """
    overlapping: set[str] = set()
    by_date: dict[str, list[dict]] = {}
    for s in schedules:
        by_date.setdefault(s["date"], []).append(s)
    for items in by_date.values():
        for i, a in enumerate(items):
            a_end = a.get("end_time") or a["start_time"]
            for b in items[i + 1:]:
                b_end = b.get("end_time") or b["start_time"]
                same_start = a["start_time"] == b["start_time"]
                if same_start or (a["start_time"] < b_end and b["start_time"] < a_end):
                    overlapping.update((a["id"], b["id"]))
    return overlapping


# ---------------- 구글 지도 ----------------

def location_query(item: dict) -> str:
    """지도 검색어: 주소 우선, 없으면 장소명(일정) 또는 숙소명(숙박)."""
    return item.get("address") or item.get("place") or item.get("name") or ""


def gmaps_search_url(query: str) -> str:
    """구글 지도 검색 URL. 검색어가 비면 빈 문자열."""
    query = (query or "").strip()
    if not query:
        return ""
    return GMAPS_SEARCH + quote(query, safe="")


def route_url(queries: list[str]) -> str:
    """순서대로 장소를 잇는 구글 지도 경로 URL. 장소가 2개 미만이면 빈 문자열."""
    queries = [q.strip() for q in queries if q and q.strip()]
    if len(queries) < 2:
        return ""
    url = f"{GMAPS_DIR}&origin={quote(queries[0], safe='')}&destination={quote(queries[-1], safe='')}"
    if len(queries) > 2:
        url += "&waypoints=" + "%7C".join(quote(q, safe="") for q in queries[1:-1])
    return url


def day_route_url(schedules: list[dict]) -> str:
    """하루 일정(시간순)의 장소들로 경로 URL을 만든다."""
    return route_url([location_query(s) for s in sort_schedules(schedules)])


# ---------------- 내보내기 ----------------

def _day_text(trip: dict, date_str: str) -> str:
    n = day_number(trip, date_str)
    return f"Day {n}" if n else "기간 외"


def _csv_bytes(header: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")  # BOM: 엑셀/My Maps 한글 깨짐 방지


MYMAPS_COLUMNS = ["Name", "Address", "Day", "Date", "Time", "Type", "Memo"]


def to_mymaps_csv(trip: dict) -> bytes:
    """Google My Maps 가져오기용 CSV. 위치(주소/장소명)가 있는 일정·숙박만 포함한다."""
    rows = []
    for s in sort_schedules(trip["schedules"]):
        loc = location_query(s)
        if not loc:
            continue
        name = f"{s['title']} - {s['place']}" if s.get("place") and s["place"] != s["title"] else s["title"]
        rows.append([name, loc, _day_text(trip, s["date"]), s["date"], format_time_range(s),
                     f"일정({s.get('category', DEFAULT_CATEGORY)})", s.get("memo", "")])
    # 연박은 한 행으로 합쳐 같은 위치에 핀이 박 수만큼 겹치지 않게 한다
    for stay in group_lodging_stays(trip["lodgings"]):
        loc = location_query(stay)
        if not loc:
            continue
        first, last = _day_text(trip, stay["first"]), _day_text(trip, stay["last"])
        day = first if first == last else f"{first}~{last}"
        nights = f"{format_date_ko(stay['first'])} 밤"
        if stay["nights"] > 1:
            nights += f" ~ {format_date_ko(stay['last'])} 밤"
        rows.append([stay["name"], loc, day, stay["first"], f"{nights} ({stay['nights']}박)", "숙박", stay["memo"]])
    return _csv_bytes(MYMAPS_COLUMNS, rows)


TABLE_COLUMNS = ["구분", "Day", "날짜", "시간", "분류", "일정/숙소", "장소", "주소", "메모", "지도 링크"]


def to_table_csv(trip: dict) -> bytes:
    """엑셀용 일정표 CSV. 날짜별로 일정(시간순) 다음에 숙박을 둔다."""
    rows = []
    dates = sorted({i["date"] for i in trip["schedules"] + trip["lodgings"]})
    for d in dates:
        for s in schedules_by_date(trip["schedules"], d):
            rows.append(["일정", _day_text(trip, d), d, format_time_range(s), s.get("category", ""), s["title"],
                         s.get("place", ""), s.get("address", ""), s.get("memo", ""),
                         gmaps_search_url(location_query(s))])
        for l in lodgings_by_date(trip["lodgings"], d):
            rows.append(["숙박", _day_text(trip, d), d, "", "", l["name"], "", l.get("address", ""),
                         l.get("memo", ""), gmaps_search_url(location_query(l))])
    return _csv_bytes(TABLE_COLUMNS, rows)


def to_json(trip: dict) -> str:
    return json.dumps(trip, ensure_ascii=False, indent=2)


# ---------------- 불러오기 ----------------

def _require_date(value, where: str) -> str:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{where}: 날짜 형식이 올바르지 않습니다 ({value!r}).")
    return value


def _require_time(value, where: str, optional: bool = False) -> str:
    if optional and not value:
        return ""
    if not isinstance(value, str) or not _TIME_RE.match(value):
        raise ValueError(f"{where}: 시간 형식이 올바르지 않습니다 ({value!r}).")
    return value


def _str(value) -> str:
    return value if isinstance(value, str) else ""


def from_json(text: str | bytes) -> dict:
    """JSON 텍스트를 검증해 여행 데이터로 복원한다. 문제가 있으면 ValueError(한국어 메시지)."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("JSON 파일을 읽을 수 없습니다. 파일이 손상되었거나 형식이 다릅니다.")
    if not isinstance(data, dict):
        raise ValueError("여행 데이터 형식이 아닙니다.")
    if data.get("version") != DATA_VERSION:
        raise ValueError(f"지원하지 않는 데이터 버전입니다 ({data.get('version')!r}).")
    missing = [k for k in ("start_date", "end_date", "schedules", "lodgings") if k not in data]
    if missing:
        raise ValueError(f"필수 항목이 없습니다: {', '.join(missing)}")
    if not isinstance(data["schedules"], list) or not isinstance(data["lodgings"], list):
        raise ValueError("schedules / lodgings 는 목록이어야 합니다.")

    trip = {
        "version": DATA_VERSION,
        "title": _str(data.get("title")),
        "start_date": _require_date(data["start_date"], "시작일"),
        "end_date": _require_date(data["end_date"], "종료일"),
        "schedules": [],
        "lodgings": [],
    }
    for n, s in enumerate(data["schedules"], 1):
        where = f"{n}번째 일정"
        if not isinstance(s, dict) or not _str(s.get("title")).strip():
            raise ValueError(f"{where}: 일정명이 없습니다.")
        start_time = _require_time(s.get("start_time"), where)
        end_time = _require_time(s.get("end_time"), where, optional=True)
        category = s.get("category")
        trip["schedules"].append({
            "id": _str(s.get("id")) or str(uuid.uuid4()),
            "date": _require_date(s.get("date"), where),
            "start_time": start_time,
            "end_time": end_time,
            "title": s["title"].strip(),
            "category": category if category in CATEGORIES else DEFAULT_CATEGORY,
            "place": _str(s.get("place")),
            "address": _str(s.get("address")),
            "memo": _str(s.get("memo")),
        })
    for n, l in enumerate(data["lodgings"], 1):
        where = f"{n}번째 숙박"
        if not isinstance(l, dict) or not _str(l.get("name")).strip():
            raise ValueError(f"{where}: 숙소명이 없습니다.")
        trip["lodgings"].append({
            "id": _str(l.get("id")) or str(uuid.uuid4()),
            "date": _require_date(l.get("date"), where),
            "name": l["name"].strip(),
            "address": _str(l.get("address")),
            "memo": _str(l.get("memo")),
        })
    # 중복 id가 있으면 위젯 key 충돌이 나므로 새로 발급
    seen: set[str] = set()
    for item in trip["schedules"] + trip["lodgings"]:
        if item["id"] in seen:
            item["id"] = str(uuid.uuid4())
        seen.add(item["id"])
    return trip
