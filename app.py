"""쇼핑리스트 Streamlit 앱.

실행: streamlit run app.py
요구사항: prd.md 참고
"""

import html
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="쇼핑리스트", page_icon="🛒")

DATA_FILE = Path(__file__).parent / "shopping_list.json"


# ---------------------------------------------------------------------------
# 데이터 저장/불러오기 (F-6)
# ---------------------------------------------------------------------------
def load_items() -> list[dict]:
    """저장 파일에서 아이템 목록을 불러온다.

    파일이 없으면 빈 리스트를 반환한다.
    파일이 손상되었거나 형식이 올바르지 않으면 경고를 표시하고 빈 리스트를 반환한다.
    """
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        st.warning("저장 파일을 읽을 수 없어 빈 리스트로 시작합니다.")
        return []
    if not isinstance(data, list):
        st.warning("저장 파일 형식이 올바르지 않아 빈 리스트로 시작합니다.")
        return []
    return data


def save_items(items: list[dict]) -> None:
    """아이템 목록을 저장 파일에 JSON 형식(UTF-8)으로 저장한다."""
    DATA_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 아이템 조작
# ---------------------------------------------------------------------------
def add_item(name: str, quantity: int) -> None:
    """새 아이템을 리스트 끝에 추가하고 저장한다. (F-1)

    id는 uuid4, created_at은 현재 시각(ISO 8601)으로 생성하며
    checked는 False로 시작한다.
    """
    st.session_state["items"].append(
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "quantity": int(quantity),
            "checked": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_items(st.session_state["items"])


def update_item(item_id: str, name: str, quantity: int) -> None:
    """id에 해당하는 아이템의 이름과 수량을 수정하고 저장한다. (F-2)"""
    for item in st.session_state["items"]:
        if item["id"] == item_id:
            item["name"] = name
            item["quantity"] = int(quantity)
            break
    save_items(st.session_state["items"])


def delete_item(item_id: str) -> None:
    """id에 해당하는 아이템을 삭제하고 저장한다. (F-3)

    삭제한 아이템이 편집 중이었다면 편집 상태도 해제한다.
    """
    st.session_state["items"] = [
        item for item in st.session_state["items"] if item["id"] != item_id
    ]
    if st.session_state["editing_id"] == item_id:
        st.session_state["editing_id"] = None
    save_items(st.session_state["items"])


def toggle_item(item_id: str) -> None:
    """id에 해당하는 아이템의 체크(구매 완료) 상태를 반전하고 저장한다. (F-4)"""
    for item in st.session_state["items"]:
        if item["id"] == item_id:
            item["checked"] = not item["checked"]
            break
    save_items(st.session_state["items"])


def delete_checked_items() -> None:
    """체크된 아이템을 모두 삭제하고 저장한다. (F-3 일괄 삭제)"""
    editing_id = st.session_state["editing_id"]
    remaining = [item for item in st.session_state["items"] if not item["checked"]]
    if editing_id is not None and all(item["id"] != editing_id for item in remaining):
        st.session_state["editing_id"] = None
    st.session_state["items"] = remaining
    save_items(remaining)


# ---------------------------------------------------------------------------
# 위젯 콜백 (위젯이 다시 그려지기 전에 실행됨)
# ---------------------------------------------------------------------------
def on_add_submit() -> None:
    """추가 폼 제출 처리: 이름 검사 후 추가하고 입력칸을 비운다."""
    name = st.session_state["new_name"].strip()
    if not name:
        st.session_state["add_error"] = "아이템 이름을 입력해주세요."
        return
    add_item(name, st.session_state["new_qty"])
    st.session_state["add_error"] = None
    st.session_state["new_name"] = ""
    st.session_state["new_qty"] = 1
    st.session_state["toast"] = ("🛒", f"{escape_md(name)} 추가됨")


def on_delete(item_id: str) -> None:
    """아이템 한 개를 삭제하고 알림을 예약한다."""
    item = next(i for i in st.session_state["items"] if i["id"] == item_id)
    delete_item(item_id)
    st.session_state["toast"] = ("🗑️", f"{escape_md(item['name'])} 삭제됨")


def on_delete_checked() -> None:
    """체크된 아이템을 모두 삭제하고 알림을 예약한다."""
    count = sum(1 for item in st.session_state["items"] if item["checked"])
    delete_checked_items()
    st.session_state["toast"] = ("🗑️", f"구매 완료 항목 {count}개 삭제됨")


def on_start_edit(item_id: str) -> None:
    """편집 모드로 전환하고 입력칸을 현재 값으로 채운다. 다른 편집은 해제된다."""
    item = next(i for i in st.session_state["items"] if i["id"] == item_id)
    st.session_state["editing_id"] = item_id
    st.session_state["edit_error"] = None
    st.session_state[f"edit_name_{item_id}"] = item["name"]
    st.session_state[f"edit_qty_{item_id}"] = int(item["quantity"])


def on_save_edit(item_id: str) -> None:
    """편집 내용을 저장한다. 이름이 비어 있으면 편집 모드를 유지한다."""
    name = st.session_state[f"edit_name_{item_id}"].strip()
    if not name:
        st.session_state["edit_error"] = "아이템 이름을 입력해주세요."
        return
    update_item(item_id, name, st.session_state[f"edit_qty_{item_id}"])
    st.session_state["editing_id"] = None
    st.session_state["edit_error"] = None


def on_cancel_edit() -> None:
    """편집을 취소한다. 값은 바뀌지 않는다."""
    st.session_state["editing_id"] = None
    st.session_state["edit_error"] = None


# ---------------------------------------------------------------------------
# 상태 초기화
# ---------------------------------------------------------------------------
def init_state() -> None:
    """session_state를 초기화한다. 최초 실행 시 한 번만 파일에서 불러온다."""
    if "items" not in st.session_state:
        st.session_state["items"] = load_items()
    st.session_state.setdefault("editing_id", None)
    st.session_state.setdefault("add_error", None)
    st.session_state.setdefault("edit_error", None)
    st.session_state.setdefault("toast", None)


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------
def escape_md(text: str) -> str:
    """사용자 입력이 마크다운 서식으로 해석되지 않도록 특수문자를 이스케이프한다."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!~|>])", r"\\\1", text)


CSS = """
<style>
.item-name { font-size: 1.05rem; }
.item-qty { opacity: 0.6; font-size: 0.85rem; margin-left: 0.4rem; }
.item-done { text-decoration: line-through; opacity: 0.45; }
</style>
"""


def render_summary(items: list[dict]) -> None:
    """전체/남은/구매 완료 개수와 진행률을 표시한다. (F-5)"""
    total = len(items)
    if total == 0:
        st.info("쇼핑리스트가 비어 있습니다. 아래에서 첫 아이템을 추가해 보세요.")
        return
    done = sum(1 for item in items if item["checked"])
    col_total, col_left, col_done = st.columns(3)
    col_total.metric("전체", f"{total}개")
    col_left.metric("남은 항목", f"{total - done}개")
    col_done.metric("구매 완료", f"{done}개")
    st.progress(
        done / total,
        text=f"전체 {total}개 / 구매 완료 {done}개 ({round(done / total * 100)}%)",
    )


def render_add_form() -> None:
    """아이템 추가 폼을 한 줄로 표시한다. (F-1)"""
    with st.form("add_form", border=False):
        col_name, col_qty, col_btn = st.columns([6, 2, 2], vertical_alignment="bottom")
        col_name.text_input("아이템 이름", key="new_name", placeholder="예: 우유")
        col_qty.number_input("수량", min_value=1, step=1, key="new_qty")
        col_btn.form_submit_button("➕ 추가", on_click=on_add_submit, type="primary")
    if st.session_state["add_error"]:
        st.warning(st.session_state["add_error"])
        st.session_state["add_error"] = None


def render_item(item: dict) -> None:
    """아이템 한 행을 카드로 표시한다. 편집 중이면 입력칸을 보여준다. (F-2, F-3, F-4)"""
    item_id = item["id"]
    with st.container(border=True):
        col_check, col_body, col_btn1, col_btn2 = st.columns(
            [0.6, 6, 1.4, 1.4], vertical_alignment="center"
        )

        col_check.checkbox(
            "구매 완료",
            value=item["checked"],
            key=f"check_{item_id}",
            on_change=toggle_item,
            args=(item_id,),
            label_visibility="collapsed",
        )

        if st.session_state["editing_id"] == item_id:
            col_name, col_qty = col_body.columns([3, 1])
            col_name.text_input("이름", key=f"edit_name_{item_id}", label_visibility="collapsed")
            col_qty.number_input(
                "수량", min_value=1, step=1, key=f"edit_qty_{item_id}", label_visibility="collapsed"
            )
            if st.session_state["edit_error"]:
                col_body.warning(st.session_state["edit_error"])
            col_btn1.button(
                "💾", key=f"save_{item_id}", help="저장", on_click=on_save_edit, args=(item_id,)
            )
            col_btn2.button("↩️", key=f"cancel_{item_id}", help="취소", on_click=on_cancel_edit)
        else:
            name = escape_md(html.escape(item["name"], quote=False))
            done_class = " item-done" if item["checked"] else ""
            col_body.markdown(
                f'<span class="item-name{done_class}">{name}</span>'
                f'<span class="item-qty">x{item["quantity"]}</span>',
                unsafe_allow_html=True,
            )
            col_btn1.button(
                "✏️", key=f"edit_{item_id}", help="수정", on_click=on_start_edit, args=(item_id,)
            )
            col_btn2.button(
                "🗑️", key=f"del_{item_id}", help="삭제", on_click=on_delete, args=(item_id,)
            )


def main() -> None:
    """앱 화면을 구성한다."""
    init_state()
    items = st.session_state["items"]

    st.markdown(CSS, unsafe_allow_html=True)
    if st.session_state["toast"]:
        icon, message = st.session_state["toast"]
        st.toast(message, icon=icon)
        st.session_state["toast"] = None

    st.title("🛒 쇼핑리스트")
    st.caption("사야 할 것을 적고, 담았으면 체크하세요")

    # [요약 영역] 전체/남은/구매 완료 개수, 진행률 (F-5)
    render_summary(items)

    # [입력 영역] 아이템 추가 폼 (F-1)
    render_add_form()

    # [리스트 영역] 미체크 항목을 먼저 표시한다. 저장 순서는 바꾸지 않는다. (F-2, F-3, F-4)
    for item in sorted(items, key=lambda i: i["checked"]):
        render_item(item)

    # [하단 영역] 체크된 항목 일괄 삭제 (F-3)
    if items:
        _, col_bulk = st.columns([3, 2])
        col_bulk.button(
            "🧹 체크된 항목 일괄 삭제",
            on_click=on_delete_checked,
            disabled=not any(item["checked"] for item in items),
        )


# Streamlit은 스크립트를 위에서부터 매번 다시 실행하므로 모듈 최상단에서 호출한다.
main()
