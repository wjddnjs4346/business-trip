import html
import re
from datetime import date, time, timedelta

import streamlit as st

import utils

st.set_page_config(page_title="여행 일정표 플래너", page_icon="🧳", layout="wide")

# ---------------- 스타일 (One UI 스타일) ----------------
# - 상단은 큰 제목과 넓은 여백의 '보기 영역', 아래는 둥근 흰색 카드로 묶은 '조작 영역'
# - 카드 스타일은 키가 있는 컨테이너(st-key-<key> 클래스)에 건다:
#   side_info / side_data  사이드바 카드,  day_<date>  하루 카드,  srow_<scope>_<id>  일정 행,
#   lodg_<scope>_<id>  숙박 줄,  outside  기간 외 카드,  toolbar  내보내기 카드
#   (<scope> = 날짜 또는 out. 같은 키의 컨테이너가 다른 부모로 옮겨 다니지 않게 해서
#    Streamlit이 이전 카드를 화면에 남기는 문제를 막는다. 겹침 표시는 키가 아니라 :has(.t-warn)으로 건다)
CSS = """
<style>
:root {
  --ou-bg: #F6F6F8;
  --ou-card: #FFFFFF;
  --ou-fill: #EEEEF1;
  --ou-divider: #EBEBEE;
  --ou-text: #111111;
  --ou-sub: #7A7A80;
  --ou-blue: #387AFF;
  --ou-blue-soft: #E9F0FF;
  --ou-sat: #387AFF;
  --ou-sun: #F2464B;
  --ou-orange: #F57C00;
  --ou-orange-soft: #FFF3E5;
  --ou-purple: #7C5CFA;
  --ou-purple-soft: #F2EEFF;
  --ou-radius-card: 26px;
  --ou-radius-item: 18px;
}
.block-container { padding-top: 4.5rem; max-width: 1080px; }

/* ---------- 보기 영역: 큰 제목 ---------- */
.hero { padding: 1.5rem .4rem 1.6rem; }
.hero-eyebrow { color: var(--ou-sub); font-size: .95rem; font-weight: 500; margin-bottom: .35rem; }
.hero h1 { font-size: 2.6rem; font-weight: 700; letter-spacing: -.02em; color: var(--ou-text);
           margin: 0; padding: 0; line-height: 1.25; overflow-wrap: anywhere; }
.hero .period { color: var(--ou-sub); font-size: 1.02rem; margin-top: .55rem; }

.summary { display: grid; grid-template-columns: repeat(3, 1fr); background: var(--ou-card);
           border-radius: var(--ou-radius-card); padding: 1rem .4rem; margin-bottom: .5rem; }
.sum { display: flex; align-items: center; gap: .8rem; padding: .2rem 1rem; }
.sum + .sum { border-left: 1px solid var(--ou-divider); }
.sum-num { font-size: 1.45rem; font-weight: 700; color: var(--ou-text); line-height: 1.2; }
.sum-label { font-size: .82rem; color: var(--ou-sub); }
.notice { color: var(--ou-sub); font-size: .8rem; margin: .6rem 0 0 .6rem; }

/* ---------- 색 타일 아이콘 ---------- */
.ic { flex: 0 0 auto; width: 38px; height: 38px; border-radius: 13px; display: flex; align-items: center;
      justify-content: center; font-size: 1.15rem; }
.ic.sight { background: #E6F0FF; } .ic.food { background: #FFEFE3; } .ic.move { background: #E2F6EE; }
.ic.shop { background: #FDE8F0; } .ic.etc { background: #EFEFF2; } .ic.lodge-ic { background: #E9E3FF; }
.ic.sm { width: 34px; height: 34px; border-radius: 12px; font-size: 1rem; }

/* ---------- 날짜 그룹 ---------- */
.day-head { display: flex; align-items: baseline; gap: .55rem; margin: 2rem .9rem .55rem; }
.day-no { color: var(--ou-blue); font-weight: 700; font-size: 1rem; }
.day-date { color: var(--ou-text); font-weight: 700; font-size: 1.12rem; }
.day-date.sat { color: var(--ou-sat); }
.day-date.sun { color: var(--ou-sun); }
.day-count { color: var(--ou-sub); font-size: .85rem; margin-left: auto; }

[class*="st-key-day_"] { background: var(--ou-card); border-radius: var(--ou-radius-card);
                         padding: .45rem 1rem .6rem; gap: 0; }
.empty-day { color: var(--ou-sub); font-size: .92rem; padding: 1rem .4rem; text-align: center; }

/* 리스트 항목 (구분선으로 나눔) */
[class*="st-key-srow"] { padding: .7rem .2rem .7rem .4rem; border-bottom: 1px solid var(--ou-divider); }
/* 각 행은 stLayoutWrapper로 감싸지므로, 카드의 마지막 래퍼 안의 행만 구분선을 없앤다 */
[data-testid="stLayoutWrapper"]:last-child > [class*="st-key-srow"] { border-bottom-color: transparent; }
[class*="st-key-srow"]:has(.t-warn) { background: var(--ou-orange-soft); border-radius: var(--ou-radius-item);
                              border-bottom-color: transparent; margin: .2rem 0; }

/* 한 줄 = 가로 컨테이너 하나(마크다운 + 버튼 2개). 컬럼을 쓰지 않아야 일정이 많을 때 빠르다 */
.t-row { display: flex; gap: 1rem; align-items: center; }
.t-row > .t-time-wrap { flex: 0 0 5.4rem; }
.t-row > .t-body { flex: 1 1 auto; min-width: 0; }
.t-time-wrap { display: flex; flex-direction: column; gap: .1rem; }
.t-time { font-weight: 700; font-size: 1.05rem; font-variant-numeric: tabular-nums; color: var(--ou-text);
          white-space: nowrap; }
.t-end { color: var(--ou-sub); font-size: .82rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
.t-date { color: var(--ou-sub); font-size: .78rem; }
.t-warn { display: inline-block; width: fit-content; background: #FFE2C2; color: var(--ou-orange);
          border-radius: 999px; padding: 0 .5rem; font-size: .72rem; font-weight: 600; white-space: nowrap;
          cursor: help; margin-top: .15rem; }

.item { display: flex; gap: .85rem; align-items: flex-start; }
.item .txt { min-width: 0; flex: 1; }
.t-title { font-weight: 600; font-size: 1rem; color: var(--ou-text); line-height: 1.45; overflow-wrap: anywhere; }
.chip { display: inline-block; border-radius: 999px; padding: 0 .55rem; font-size: .72rem; font-weight: 600;
        margin-left: .4rem; vertical-align: 2px; background: var(--ou-fill); color: var(--ou-sub); }
.chip.sight { background: #E6F0FF; color: #2F6BE6; } .chip.food { background: #FFEFE3; color: #D46A1F; }
.chip.move { background: #E2F6EE; color: #17895F; } .chip.shop { background: #FDE8F0; color: #C93B73; }
.t-loc { font-size: .86rem; color: #4A4A50; margin-top: .1rem; overflow-wrap: anywhere; }
.t-memo { font-size: .82rem; color: var(--ou-sub); margin-top: .15rem; overflow-wrap: anywhere; }
.t-loc a, .lodge a, .route a { color: var(--ou-blue); text-decoration: none; font-weight: 500; }
.t-loc a:hover, .lodge a:hover, .route a:hover { text-decoration: underline; }
.route { text-align: right; font-size: .88rem; padding: .65rem .3rem .3rem; }

/* 숙박: 일정 리스트와 구분되는 보라 톤 블록 */
[class*="st-key-lodg_"] { background: var(--ou-purple-soft); border-radius: var(--ou-radius-item);
                          padding: .6rem .4rem .6rem .7rem; margin-top: .45rem; }
.lodge { display: flex; gap: .75rem; align-items: center; color: #3E2F7A; font-size: .92rem; overflow-wrap: anywhere; }
.lodge .txt { min-width: 0; flex: 1; }
.lodge .lodge-label { color: var(--ou-purple); font-weight: 700; margin-right: .35rem; }
.lodge .t-loc { color: #5A4F86; }

/* 행 안 아이콘 버튼: 원형, 평소 흐리게. 라벨("수정"/"삭제")은 화면에서만 숨기고 스크린리더에는 읽힌다 */
[class*="st-key-srow"] .stButton button, [class*="st-key-lodg_"] .stButton button {
  min-height: 0; width: 38px; height: 38px; padding: 0; border-radius: 50%; opacity: .5; gap: 0; }
[class*="st-key-srow"] .stButton button:hover, [class*="st-key-lodg_"] .stButton button:hover {
  opacity: 1; background: rgba(0,0,0,.05); }
[class*="st-key-srow"] .stButton button:disabled { opacity: .2; }
[class*="st-key-srow"] .stButton button [data-testid="stMarkdownContainer"],
[class*="st-key-lodg_"] .stButton button [data-testid="stMarkdownContainer"] {
  position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
[class*="st-key-srow"], [class*="st-key-lodg_"] { flex-wrap: nowrap; }
[class*="st-key-srow"] > [data-testid="stElementContainer"]:first-child,
[class*="st-key-lodg_"] > [data-testid="stElementContainer"]:first-child { flex: 1 1 auto; min-width: 0; }

/* Streamlit이 Markdown 컨테이너에 주는 음수 margin 상쇄 (카드 하단 잘림 방지) */
[class*="st-key-day_"] [data-testid="stMarkdownContainer"],
[class*="st-key-srow"] [data-testid="stMarkdownContainer"],
[class*="st-key-lodg_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }

/* 하루 카드 안의 수정 폼 */
[class*="st-key-day_"] [data-testid="stForm"] { background: #FAFAFC; border: 1px solid var(--ou-divider);
                                                border-radius: var(--ou-radius-item); margin: .4rem 0; }

/* ---------- 카드 공통 (폼, 내보내기, 기간 외, 펼침) ---------- */
[data-testid="stForm"] { background: var(--ou-card); border: none; border-radius: var(--ou-radius-card);
                         padding: 1.1rem 1.1rem .9rem; }
.st-key-toolbar, .st-key-outside { background: var(--ou-card); border-radius: var(--ou-radius-card);
                                   padding: 1.2rem 1.2rem 1rem; margin-top: 2rem; }
.st-key-outside { padding-top: .8rem; }
[data-testid="stExpander"] details { border: none; background: var(--ou-bg); border-radius: var(--ou-radius-item); }
[data-testid="stAlert"] > div { border-radius: var(--ou-radius-item); }
.card-title { font-size: 1.1rem; font-weight: 700; color: var(--ou-text); margin: .1rem 0 .2rem; }
.card-sub { font-size: .84rem; color: var(--ou-sub); margin-bottom: .5rem; }

/* ---------- 사이드바 ---------- */
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarUserContent"] { padding-top: 1.5rem; }
.side-title { font-size: 1.6rem; font-weight: 700; letter-spacing: -.01em; margin: .6rem .3rem .1rem; }
.side-desc { color: var(--ou-sub); font-size: .84rem; margin: 0 .3rem 1rem; }
.side-section { font-size: .8rem; font-weight: 600; color: var(--ou-sub); margin: .9rem .6rem .35rem; }
.st-key-side_info, .st-key-side_data { background: var(--ou-card); border-radius: var(--ou-radius-card);
                                       padding: 1rem 1rem .9rem; }
[data-testid="stSidebar"] [data-testid="stForm"] { padding: 1rem 1rem .8rem; }
.pill { display: inline-block; background: var(--ou-blue-soft); color: var(--ou-blue); font-weight: 600;
        border-radius: 999px; padding: .15rem .8rem; font-size: .85rem; }

/* 탭 → 세그먼트 버튼 */
[data-testid="stTabs"] [data-baseweb="tab-list"] { background: #E7E7EB; border-radius: 999px; padding: 4px; gap: 4px; }
[data-testid="stTabs"] [data-baseweb="tab"] { flex: 1; justify-content: center; border-radius: 999px;
                                              height: auto; padding: .45rem .6rem; margin: 0; }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { background: #FFFFFF;
                                                                     box-shadow: 0 1px 4px rgba(0,0,0,.08); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
[data-testid="stTabs"] [data-baseweb="tab-panel"] { padding-top: .8rem; }

/* ---------- 모바일 ---------- */
@media (max-width: 640px) {
  .block-container { padding: 2.5rem .9rem 2rem; }
  .hero { padding: 1rem .3rem 1.2rem; }
  .hero h1 { font-size: 2rem; }
  .summary { padding: .8rem .2rem; }
  .sum { flex-direction: column; gap: .35rem; padding: .2rem .4rem; text-align: center; }
  .sum-num { font-size: 1.2rem; }
  [class*="st-key-day_"] { padding: .35rem .7rem .5rem; }
  .day-head { margin: 1.6rem .6rem .45rem; }
  /* 모바일: [시간 줄] / [내용] 두 줄. 버튼은 시간 줄 오른쪽에 띄워 내용이 전체 폭을 쓰게 한다 */
  [class*="st-key-srow"] { position: relative; }
  [class*="st-key-srow"] > [data-testid="stElementContainer"]:nth-child(n+2) { position: absolute; top: .35rem; }
  [class*="st-key-srow"] > [data-testid="stElementContainer"]:nth-child(2) { right: 3.1rem; }
  [class*="st-key-srow"] > [data-testid="stElementContainer"]:nth-child(3) { right: .3rem; }
  .t-row { flex-wrap: wrap; gap: .35rem; }
  .t-row > .t-time-wrap { flex: 1 1 100%; flex-direction: row; align-items: baseline; gap: .45rem; flex-wrap: wrap;
                          padding-right: 6.2rem; min-height: 2.2rem; }
  .t-row > .t-body { flex: 1 1 100%; }
  /* 터치 영역 44px 이상 */
  [class*="st-key-srow"] .stButton button, [class*="st-key-lodg_"] .stButton button { width: 44px; height: 44px; }
}

/* ---------- 인쇄: 일정표만 ---------- */
@media print {
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], header[data-testid="stHeader"],
  .stButton, .stDownloadButton, .st-key-toolbar, .notice, [data-testid="stToolbar"],
  [data-testid="stAlert"] { display: none !important; }
  .block-container { padding: 0 1.2rem !important; max-width: 100% !important; }
  .hero { padding-top: 0; }
  .summary, [class*="st-key-day_"], .st-key-outside { border: 1px solid #D9D9DE; }
  [class*="st-key-srow"], [class*="st-key-lodg_"] { break-inside: avoid; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# 분류 → CSS 클래스 (색 타일/칩 색상)
CAT_CLASS = {"관광": "sight", "식사": "food", "이동": "move", "쇼핑": "shop", "기타": "etc"}

# Streamlit은 HTML 주변 텍스트를 Markdown으로도 해석하므로, HTML 이스케이프 후 Markdown 특수문자도 엔티티로 바꾼다.
# HTML 특수문자와 Markdown 특수문자를 한 번에 숫자 엔티티로 바꾼다.
# (html.escape 후 다시 바꾸면 &#x27; 의 '#'까지 바뀌어 작은따옴표가 "&#x27;"로 그대로 보이는 문제가 있었다)
_ENTITIES = str.maketrans({c: f"&#{ord(c)};" for c in "&<>\"'\\`*_{}[]()#+-.!|~$:"})


def esc(text: str) -> str:
    return (text or "").translate(_ENTITIES)


def sync_widgets_from_trip(trip: dict) -> None:
    """여행 기본정보 위젯 값을 trip 데이터에 맞춘다 (초기화·JSON 불러오기 시)."""
    st.session_state["w_title"] = trip["title"]
    st.session_state["w_start"] = date.fromisoformat(trip["start_date"])
    st.session_state["w_end"] = date.fromisoformat(trip["end_date"])


if "trip" not in st.session_state:
    st.session_state["trip"] = utils.new_trip()
    st.session_state["editing_id"] = None
    st.session_state["uploader_n"] = 0
    sync_widgets_from_trip(st.session_state["trip"])
trip = st.session_state["trip"]


# ---------------- 콜백 (스크립트 실행 전에 호출되므로 session_state의 trip을 직접 사용) ----------------

def delete_item(kind: str, item_id: str) -> None:
    t = st.session_state["trip"]
    t[kind] = [i for i in t[kind] if i["id"] != item_id]
    if st.session_state.get("editing_id") == item_id:
        st.session_state["editing_id"] = None


def start_edit(item_id: str) -> None:
    st.session_state["editing_id"] = item_id
    st.session_state.pop("edit_error", None)


def cancel_edit() -> None:
    st.session_state["editing_id"] = None
    st.session_state.pop("edit_error", None)


def add_pending_lodging() -> None:
    new = st.session_state.pop("pending_lodging", [])
    st.session_state["trip"]["lodgings"].extend(new)
    st.session_state["lodging_msg"] = f"숙박 {len(new)}박을 추가했습니다."


def discard_pending_lodging() -> None:
    st.session_state.pop("pending_lodging", None)


def save_edit(sid: str) -> None:
    """수정 폼 저장. 콜백에서 처리해 스크립트 중간 재실행(st.rerun) 없이 한 번에 반영한다."""
    ss = st.session_state
    s = next((i for i in ss["trip"]["schedules"] if i["id"] == sid), None)
    if s is None:
        cancel_edit()
        return
    title = ss[f"e_title_{sid}"].strip()
    start_str = ss[f"e_start_{sid}"].strftime("%H:%M")
    end_str = ss[f"e_end_{sid}"].strftime("%H:%M") if ss[f"e_end_{sid}"] else ""
    if not title:
        ss["edit_error"] = "일정명을 입력해 주세요."
        return
    if not utils.is_valid_time_range(start_str, end_str):
        ss["edit_error"] = "종료 시간이 시작 시간보다 빠릅니다."
        return
    s.update(date=ss[f"e_date_{sid}"], start_time=start_str, end_time=end_str, category=ss[f"e_cat_{sid}"],
             title=title, place=ss[f"e_place_{sid}"].strip(), address=ss[f"e_addr_{sid}"].strip(),
             memo=ss[f"e_memo_{sid}"].strip())
    cancel_edit()


def load_json() -> None:
    f = st.session_state.get(f"uploader_{st.session_state['uploader_n']}")
    if f is None:
        return
    # 성공·실패와 관계없이 업로더를 새로 만든다. 파일이 남아 있는 업로더에 다른 파일을 올리면
    # '제거 + 추가'로 rerun이 연달아 겹치면서 이전 카드가 화면에 남는 문제가 있었다 (QA BUG-1)
    st.session_state["uploader_n"] += 1
    try:
        new_trip = utils.from_json(f.getvalue())
    except ValueError as e:
        st.session_state["flash"] = ("error", f"불러오기 실패: {esc(str(e))}")
        return
    st.session_state["trip"] = new_trip
    cancel_edit()
    discard_pending_lodging()
    sync_widgets_from_trip(new_trip)
    st.session_state["flash"] = (
        "success",
        f"'{esc(f.name)}'을(를) 불러왔습니다. (일정 {len(new_trip['schedules'])}개, 숙박 {len(new_trip['lodgings'])}박)",
    )


# ---------------- 렌더링 헬퍼 ----------------

def link(text: str, url: str) -> str:
    return f'<a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">{esc(text)}</a>'


def schedule_location_html(s: dict) -> str:
    url = utils.gmaps_search_url(utils.location_query(s))
    place, address = s.get("place", ""), s.get("address", "")
    if address:
        head = f"{esc(place)} · " if place else ""
        return f'<div class="t-loc">{head}📍 {link(address, url)}</div>'
    if place:
        return f'<div class="t-loc">📍 {link(place, url)}</div>'
    return ""


def day_options(days: list[date], current: str | None = None) -> list[str]:
    """날짜 선택지(ISO 문자열). 기간 밖 날짜의 항목을 수정할 때는 원래 날짜도 포함."""
    opts = [d.isoformat() for d in days]
    if current and current not in opts:
        opts.append(current)
    return opts


def day_option_label(trip: dict, date_str: str) -> str:
    n = utils.day_number(trip, date_str)
    d = date.fromisoformat(date_str)
    return utils.format_day_label(n - 1, d) if n else f"{utils.format_date_ko(date_str)} · 기간 외"


def render_edit_form(s: dict, days: list[date], scope: str) -> None:
    sid = s["id"]
    with st.form(f"edit_form_{scope}_{sid}", border=True):
        st.markdown(f'<div class="card-title">일정 수정</div><div class="card-sub">{esc(s["title"])}</div>',
                    unsafe_allow_html=True)
        opts = day_options(days, s["date"])
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        c1.selectbox("날짜", opts, index=opts.index(s["date"]), key=f"e_date_{sid}",
                                format_func=lambda v: day_option_label(trip, v))
        c2.time_input("시작 시간", value=time.fromisoformat(s["start_time"]), step=600,
                                   key=f"e_start_{sid}")
        c3.time_input("종료 시간", value=time.fromisoformat(s["end_time"]) if s["end_time"] else None,
                                step=600, key=f"e_end_{sid}")
        cats = list(utils.CATEGORIES)
        c4.selectbox("분류", cats, index=cats.index(s.get("category", utils.DEFAULT_CATEGORY)),
                               key=f"e_cat_{sid}", format_func=lambda c: f"{utils.CATEGORIES[c]} {c}")
        c5, c6, c7 = st.columns(3)
        c5.text_input("일정명 *", value=s["title"], key=f"e_title_{sid}")
        c6.text_input("장소명", value=s["place"], key=f"e_place_{sid}")
        c7.text_input("주소", value=s["address"], key=f"e_addr_{sid}")
        st.text_area("메모", value=s["memo"], height=68, key=f"e_memo_{sid}")
        b1, b2, _ = st.columns([1, 1, 5])
        b1.form_submit_button("저장", type="primary", width="stretch", on_click=save_edit, args=(sid,))
        b2.form_submit_button("취소", width="stretch", on_click=cancel_edit)
    if st.session_state.get("edit_error"):
        st.error(st.session_state["edit_error"])


def render_schedule_row(s: dict, overlaps: set[str], days: list[date], scope: str, show_date: bool = False) -> None:
    """scope: 행이 놓이는 부모(날짜 문자열 또는 "out"). 컨테이너 키에 넣어 부모가 바뀌면 다른 요소로 취급되게 한다."""
    editing = st.session_state.get("editing_id")
    if editing == s["id"]:
        render_edit_form(s, days, scope)
        return
    overlap = s["id"] in overlaps
    date_html = f'<span class="t-date">{esc(utils.format_date_ko(s["date"]))}</span>' if show_date else ""
    end_html = f'<span class="t-end">~ {esc(s["end_time"])}</span>' if s.get("end_time") else ""
    warn_html = ('<span class="t-warn" title="같은 날 다른 일정과 시간이 겹칩니다">⚠️ 겹침</span>'
                 if overlap else "")
    category = s.get("category") if s.get("category") in utils.CATEGORIES else utils.DEFAULT_CATEGORY
    cls = CAT_CLASS[category]
    memo_html = (f'<div class="t-memo">{esc(s["memo"]).replace(chr(10), "<br>")}</div>'
                 if s.get("memo") else "")
    row_html = (
        f'<div class="t-row"><div class="t-time-wrap">{date_html}<span class="t-time">{esc(s["start_time"])}</span>'
        f'{end_html}{warn_html}</div>'
        f'<div class="t-body item"><div class="ic {cls}">{utils.CATEGORIES[category]}</div><div class="txt">'
        f'<div class="t-title">{esc(s["title"])}<span class="chip {cls}">{esc(category)}</span></div>'
        f"{schedule_location_html(s)}{memo_html}</div></div></div>"
    )
    # 컬럼 대신 가로 컨테이너 하나 + 요소 3개로 그린다. help 툴팁은 버튼마다 숨은 복제 요소를 만들어
    # 일정이 많을 때 느려지므로, 수정 잠금 안내가 필요할 때만 붙인다 (QA 성능 측정 근거: QA_REPORT.md)
    with st.container(key=f"srow_{scope}_{s['id']}", horizontal=True, vertical_alignment="center", gap="small"):
        st.markdown(row_html, unsafe_allow_html=True, width="stretch")
        # 다른 일정을 수정하는 중이면 저장 안 한 변경이 사라지지 않도록 ✏️를 막는다
        st.button("수정", icon="✏️", key=f"edit_{s['id']}", type="tertiary", disabled=editing is not None,
                  help="다른 일정을 수정 중입니다. 먼저 저장하거나 취소하세요." if editing else None,
                  on_click=start_edit, args=(s["id"],))
        st.button("삭제", icon="🗑️", key=f"del_s_{s['id']}", type="tertiary",
                  on_click=delete_item, args=("schedules", s["id"]))


def render_lodging_line(l: dict, scope: str, show_date: bool = False) -> None:
    with st.container(key=f"lodg_{scope}_{l['id']}", horizontal=True, vertical_alignment="center", gap="small"):
        url = utils.gmaps_search_url(utils.location_query(l))
        sub = ["📍 " + (link(l["address"], url) if l.get("address") else link("지도에서 보기", url))]
        if l.get("memo"):
            sub.append(esc(l["memo"]))
        prefix = f"{esc(utils.format_date_ko(l['date']))} 밤 · " if show_date else ""
        st.markdown(
            f'<div class="lodge"><div class="ic sm lodge-ic">🏨</div><div class="txt">'
            f'<div>{prefix}<span class="lodge-label">숙박</span>{esc(l["name"])}</div>'
            f'<div class="t-loc">{" · ".join(sub)}</div></div></div>',
            unsafe_allow_html=True, width="stretch",
        )
        st.button("숙박 삭제", icon="🗑️", key=f"del_l_{l['id']}", type="tertiary",
                  on_click=delete_item, args=("lodgings", l["id"]))


def day_header_html(index: int, d: date, count: int) -> str:
    wk = {5: " sat", 6: " sun"}.get(d.weekday(), "")
    date_text = f"{d.month}월 {d.day}일 ({utils.WEEKDAYS_KO[d.weekday()]})"
    count_text = f"일정 {count}개" if count else ""
    return (f'<div class="day-head"><span class="day-no">Day {index + 1}</span>'
            f'<span class="day-date{wk}">{esc(date_text)}</span><span class="day-count">{count_text}</span></div>')


def hero_html(trip: dict, start: date, end: date, period: tuple[int, int] | None) -> str:
    title = esc(trip["title"] or "여행 일정표")
    if period:
        same_year = start.year == end.year
        period_text = f"{start:%Y.%m.%d} ~ {end:%m.%d}" if same_year else f"{start:%Y.%m.%d} ~ {end:%Y.%m.%d}"
        period_text = f"{period_text} · {period[0]}박 {period[1]}일"
    else:
        period_text = "여행 기간을 확인해 주세요"
    s_iso, e_iso = start.isoformat(), end.isoformat()
    in_range = [s for s in trip["schedules"] if s_iso <= s["date"] <= e_iso]
    nights = [l for l in trip["lodgings"] if s_iso <= l["date"] <= e_iso]
    places = {utils.location_query(i) for i in in_range + nights} - {""}
    stats = [("sight", "📅", f"{len(in_range)}개", "일정"), ("lodge-ic", "🏨", f"{len(nights)}박", "숙박"),
             ("move", "📍", f"{len(places)}곳", "장소")]
    stats_html = "".join(
        f'<div class="sum"><div class="ic {c}">{i}</div><div><div class="sum-num">{esc(n)}</div>'
        f'<div class="sum-label">{esc(lbl)}</div></div></div>'
        for c, i, n, lbl in stats
    )
    return (f'<div class="hero"><div class="hero-eyebrow">여행 일정표</div><h1>{title}</h1>'
            f'<div class="period">{esc(period_text)}</div></div><div class="summary">{stats_html}</div>')


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "trip"


def section_label(text: str) -> None:
    st.markdown(f'<div class="side-section">{esc(text)}</div>', unsafe_allow_html=True)


# ---------------- 사이드바: 입력 ----------------
with st.sidebar:
    st.markdown('<div class="side-title">여행 플래너</div>'
                '<div class="side-desc">일정을 입력하면 오른쪽 일정표에 바로 정리됩니다.</div>',
                unsafe_allow_html=True)

    section_label("여행 정보")
    with st.container(key="side_info"):
        trip["title"] = st.text_input("여행 제목", key="w_title", placeholder="예: 도쿄 가족여행")
        col_start, col_end = st.columns(2)
        start = col_start.date_input("시작일", key="w_start", format="YYYY.MM.DD")
        end = col_end.date_input("종료일", key="w_end", format="YYYY.MM.DD")
        trip["start_date"], trip["end_date"] = start.isoformat(), end.isoformat()

        period = utils.nights_days(start, end)
        if period is None:
            st.warning("종료일이 시작일보다 앞설 수 없습니다.")
        else:
            st.markdown(f'<span class="pill">{period[0]}박 {period[1]}일</span>', unsafe_allow_html=True)

    days = utils.date_range(start, end)

    section_label("입력")
    tab_schedule, tab_lodging = st.tabs(["📝 일정", "🏨 숙박"])

    with tab_schedule:
        if not days:
            st.info("여행 기간을 올바르게 설정하면 일정을 추가할 수 있습니다.")
        else:
            with st.form("schedule_form", clear_on_submit=True, border=False):
                day = st.selectbox(
                    "날짜",
                    options=days,
                    format_func=lambda d: utils.format_day_label(days.index(d), d),
                )
                col_t1, col_t2 = st.columns(2)
                start_time = col_t1.time_input("시작 시간 *", value=time(9, 0), step=600)
                end_time = col_t2.time_input("종료 시간", value=None, step=600)
                category = st.selectbox(
                    "분류", list(utils.CATEGORIES), index=list(utils.CATEGORIES).index(utils.DEFAULT_CATEGORY),
                    format_func=lambda c: f"{utils.CATEGORIES[c]} {c}",
                )
                title = st.text_input("일정명 *", placeholder="예: 도쿄타워 전망대")
                place = st.text_input("장소명", placeholder="예: 도쿄타워")
                address = st.text_input("주소", placeholder="예: 서울 중구 세종대로 110",
                                        help="입력하면 구글 지도 링크가 만들어집니다.")
                memo = st.text_area("메모", height=80, placeholder="예: 입장권 사전 예매")
                submitted = st.form_submit_button("일정 추가", type="primary", width="stretch")

            if submitted:
                start_str = start_time.strftime("%H:%M")
                end_str = end_time.strftime("%H:%M") if end_time else ""
                if not title.strip():
                    st.error("일정명을 입력해 주세요.")
                elif not utils.is_valid_time_range(start_str, end_str):
                    st.error("종료 시간이 시작 시간보다 빠릅니다.")
                else:
                    trip["schedules"].append(
                        utils.make_schedule(
                            date_str=day.isoformat(),
                            start_time=start_str,
                            end_time=end_str,
                            title=title,
                            place=place,
                            address=address,
                            memo=memo,
                            category=category,
                        )
                    )
                    st.success("일정을 추가했습니다.")

    with tab_lodging:
        if not days:
            st.info("여행 기간을 올바르게 설정하면 숙박을 추가할 수 있습니다.")
        else:
            with st.form("lodging_form", clear_on_submit=True, border=False):
                st.caption("숙박은 일정이 아니라, 일정표의 해당 날짜 하단에 글로 표시됩니다.")
                col_in, col_out = st.columns(2)
                check_in = col_in.date_input("체크인 *", value=start, min_value=start, max_value=end,
                                             format="YYYY.MM.DD")
                check_out = col_out.date_input(
                    "체크아웃 *", value=max(end, start + timedelta(days=1)),
                    min_value=start + timedelta(days=1), max_value=end + timedelta(days=1), format="YYYY.MM.DD",
                )
                lodging_name = st.text_input("숙소명 *", placeholder="예: 신주쿠 그레이스리 호텔")
                lodging_address = st.text_input("주소", key="lodging_address", placeholder="예: 東京都新宿区歌舞伎町1-19-1")
                lodging_memo = st.text_input("메모", placeholder="예: 체크인 15:00")
                lodging_submitted = st.form_submit_button("숙박 추가", type="primary", width="stretch")

            if lodging_submitted:
                st.session_state.pop("pending_lodging", None)
                if not lodging_name.strip():
                    st.error("숙소명을 입력해 주세요.")
                elif check_out <= check_in:
                    st.error("체크아웃은 체크인 다음 날 이후여야 합니다.")
                else:
                    new = utils.make_lodgings(check_in, check_out - timedelta(days=1),
                                              lodging_name, lodging_address, lodging_memo)
                    if utils.lodging_conflicts(trip["lodgings"], [l["date"] for l in new]):
                        # 폼은 제출 시 비워지므로 입력값을 보관해 두고 확인을 받는다
                        st.session_state["pending_lodging"] = new
                    else:
                        trip["lodgings"].extend(new)
                        st.success(f"숙박 {len(new)}박을 추가했습니다.")

            pending = st.session_state.get("pending_lodging")
            if pending:
                conflicts = utils.lodging_conflicts(trip["lodgings"], [l["date"] for l in pending])
                listed = ", ".join(f"{utils.format_date_ko(c['date'])} 밤({c['name']})" for c in conflicts[:3])
                more = f" 외 {len(conflicts) - 3}건" if len(conflicts) > 3 else ""
                st.warning(f"이미 숙박이 등록된 날이 있습니다: {esc(listed)}{more}. "
                           f"'{esc(pending[0]['name'])}' {len(pending)}박을 그래도 추가할까요?")
                cp1, cp2 = st.columns(2)
                cp1.button("그래도 추가", key="pending_add", type="primary", width="stretch", on_click=add_pending_lodging)
                cp2.button("취소", key="pending_discard", width="stretch", on_click=discard_pending_lodging)
            lodging_msg = st.session_state.pop("lodging_msg", None)
            if lodging_msg:
                st.success(lodging_msg)

    section_label("데이터 저장 · 불러오기")
    with st.container(key="side_data"):
        st.download_button("💾 JSON으로 저장", utils.to_json(trip).encode("utf-8"),
                           file_name=f"{safe_filename(trip['title'])}.json", mime="application/json",
                           width="stretch", on_click="ignore")
        st.file_uploader("📂 JSON 불러오기 (현재 내용을 덮어씁니다)", type=["json"],
                         key=f"uploader_{st.session_state['uploader_n']}", on_change=load_json)

# ---------------- 메인: 일정표 ----------------
# 알림·경고는 항상 존재하는 칸 안에 넣어, 나타나거나 사라질 때 아래 요소들의 위치가 바뀌지 않게 한다
flash = st.session_state.pop("flash", None)
with st.container(key="flash_slot"):
    if flash:
        getattr(st, flash[0])(flash[1])

st.markdown(hero_html(trip, start, end, period), unsafe_allow_html=True)
st.markdown('<div class="notice">ⓘ 새로고침하면 입력 내용이 사라집니다. 사이드바의 <b>JSON으로 저장</b>으로 보관하세요.</div>',
            unsafe_allow_html=True)

with st.container(key="period_warning_slot"):
    if not days:
        st.warning("종료일이 시작일보다 앞서 있어 일정표를 표시할 수 없습니다.")

overlaps = utils.find_overlaps(trip["schedules"])

for i, d in enumerate(days):
    d_str = d.isoformat()
    items = utils.schedules_by_date(trip["schedules"], d_str)
    st.markdown(day_header_html(i, d, len(items)), unsafe_allow_html=True)
    with st.container(key=f"day_{d_str}"):
        if not items:
            st.markdown('<div class="empty-day">일정 없음</div>', unsafe_allow_html=True)
        for s in items:
            render_schedule_row(s, overlaps, days, scope=d_str)
        route = utils.day_route_url(items)
        if route:
            st.markdown(f'<div class="route">{link("🗺️ 이 날 경로 보기", route)} ›</div>',
                        unsafe_allow_html=True)
        for l in utils.lodgings_by_date(trip["lodgings"], d_str):
            render_lodging_line(l, scope=d_str)

if days:
    outside_s = utils.out_of_range(trip["schedules"], start, end)
    outside_l = utils.out_of_range(trip["lodgings"], start, end)
    if outside_s or outside_l:
        with st.container(key="outside"):
            st.subheader("📦 기간 외 항목")
            st.markdown('<div class="card-sub">여행 기간 밖 날짜의 항목입니다. 기간을 다시 늘리거나, ✏️로 날짜를 옮기거나, '
                        '삭제할 수 있습니다.</div>', unsafe_allow_html=True)
            for s in outside_s:
                render_schedule_row(s, overlaps, days, scope="out", show_date=True)
            for l in outside_l:
                render_lodging_line(l, scope="out", show_date=True)

# ---------------- 내보내기 ----------------
with st.container(key="toolbar"):
    st.markdown('<div class="card-title">내보내기</div>'
                '<div class="card-sub">구글 내 지도에 장소를 올리거나 엑셀로 일정표를 열 수 있습니다.</div>',
                unsafe_allow_html=True)
    base = safe_filename(trip["title"])
    c1, c2 = st.columns(2)
    c1.download_button("🗺️ 구글 내 지도(My Maps)용 CSV", utils.to_mymaps_csv(trip), file_name=f"{base}_mymaps.csv",
                       mime="text/csv", width="stretch", type="primary", on_click="ignore",
                       help="주소 또는 장소명이 있는 일정·숙박만 포함됩니다.")
    c2.download_button("📊 일정표 CSV (엑셀)", utils.to_table_csv(trip), file_name=f"{base}_일정표.csv",
                       mime="text/csv", width="stretch", on_click="ignore")
    with st.expander("구글 내 지도에 올리는 방법"):
        st.markdown(
            "1. [Google My Maps](https://www.google.com/mymaps)에서 **새 지도 만들기** → 레이어의 **가져오기**를 누릅니다.\n"
            "2. 내려받은 `_mymaps.csv` 파일을 올리고, 위치 열로 **Address**, 제목 열로 **Name**을 선택합니다.\n"
            "3. **스타일 → 그룹화 기준: Day 또는 Type**으로 날짜별·숙박별 색을 나눌 수 있습니다."
        )
    st.caption("🖨️ 브라우저 인쇄(Ctrl+P)를 하면 사이드바와 버튼 없이 일정표만 인쇄됩니다.")
