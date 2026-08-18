import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="作業日別進捗＆csv判定ツール", layout="wide"
)

# ------------------------------------------------------------------
# 🔗 参照用Googleスプレッドシート（シフト表）のURL
# ------------------------------------------------------------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit"

# --- スタイル調整CSS ---
st.markdown(
    """
    <style>
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.8rem !important;
    }
    div[data-testid="stPills"], div[data-testid="stSegmentedControl"] {
        width: 100% !important;
        margin-top: 4px !important;
    }
    .stSelectbox label, .stNumberInput label, div[data-testid="stWidgetLabel"] p {
        font-weight: bold !important;
        font-size: 0.95rem !important;
        color: #333333 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- ヘッダー部分 ＆ シフト表リンクボタン ---
head_col1, head_col2 = st.columns([3, 1.2])
with head_col1:
  st.title("📦 作業日別 完了日 ＆ csv判定ツール")
  st.write(
      "作業日ごとにポイント数とcsvの日付を設定し、出勤シフトから期日に間に合うかを判定します。"
  )

with head_col2:
  st.write("")
  st.link_button(
      "📊 シフト表を開く",
      SPREADSHEET_URL,
      type="primary",
      use_container_width=True,
  )

st.divider()

# --- メンバー基本能力の設定 ---
MEMBERS_DATA = {
    "須原": 2.0,
    "福原": 2.0,
    "龍": 2.0,
    "西村風": 2.0,
    "高杉": 2.0,
    "中山佳": 2.0,
    "中山将": 3.0,
    "黒田": 2.0,
    "中尾": 2.5,
    "調整用（ヘルプ・任意）": 0.0,
}

today = datetime.date.today()
sim_days = 14

# --- 1. セッション状態の初期化 ---
if "projects" not in st.session_state:
  st.session_state.projects = [
      {
          "name": "8/10作",
          "tasks": 30,
          "deadline": today + datetime.timedelta(days=2),
      },
      {
          "name": "8/12作",
          "tasks": 25,
          "deadline": today + datetime.timedelta(days=4),
      },
  ]

if "shift_data" not in st.session_state:
  st.session_state.shift_data = {}
  for d in range(sim_days):
    for m_name in MEMBERS_DATA.keys():
      if m_name == "調整用（ヘルプ・任意）":
        st.session_state.shift_data[f"custom_{d}"] = 0.0
      else:
        st.session_state.shift_data[f"seg_{d}_{m_name}"] = "休み"

for key, val in st.session_state.shift_data.items():
  if key not in st.session_state:
    st.session_state[key] = val

col_left, col_right = st.columns([1, 1.2])

# --- 2. 作業日の登録（左側） ---
with col_left:
  st.subheader("1. 作業日の登録")
  st.caption("作業日名・ポイント数・csvの日付を設定してください。")

  with st.form("add_project_form"):
    f_col1, f_col2, f_col3 = st.columns([2, 1.5, 2])
    p_name = f_col1.text_input("作業日名", value="8/14作")
    p_tasks = f_col2.number_input("ポイント数", min_value=1, value=20)
    p_deadline = f_col3.date_input(
        "csvの日付", value=today + datetime.timedelta(days=6)
    )

    submitted = st.form_submit_button(
        "＋ 作業日を追加", use_container_width=True
    )
    if submitted:
      st.session_state.projects.append(
          {"name": p_name, "tasks": p_tasks, "deadline": p_deadline}
      )
      st.rerun()

  st.write("📋 **登録中の作業日一覧**")
  updated_projects = []
  for i, p in enumerate(st.session_state.projects):
    c1, c2, c3, c4 = st.columns([2, 1.5, 2, 1])
    name = c1.text_input(f"作業日{i+1}", value=p["name"], key=f"p_name_{i}")
    tasks = c2.number_input(
        f"pt数{i+1}", min_value=0, value=p["tasks"], key=f"p_task_{i}"
    )

    default_dl = p.get("deadline", today + datetime.timedelta(days=3))
    deadline = c3.date_input(f"csv{i+1}", value=default_dl, key=f"p_dl_{i}")

    delete = c4.button("削除", key=f"del_{i}")

    if not delete and tasks > 0:
      updated_projects.append(
          {"name": name, "tasks": tasks, "deadline": deadline}
      )

  if len(updated_projects) != len(st.session_state.projects):
    st.session_state.projects = updated_projects
    st.rerun()

# --- 3. 日別の出勤シフト設定（右側） ---
with col_right:
  st.subheader("2. 日別の出勤シフト設定")
  st.caption("向こう2週間程度の出勤予定を設定してください。")

  if st.button(
      "🔄 シフトを全日リセット（全員休みにする）", type="secondary"
  ):
    for d in range(sim_days):
      for m_name in MEMBERS_DATA.keys():
        if m_name == "調整用（ヘルプ・任意）":
          k = f"custom_{d}"
          st.session_state[k] = 0.0
          st.session_state.shift_data[k] = 0.0
        else:
          k = f"seg_{d}_{m_name}"
          st.session_state[k] = "休み"
          st.session_state.shift_data[k] = "休み"
    st.rerun()

  shift_schedule = {}

  for d in range(sim_days):
    target_date = today + datetime.timedelta(days=d)
    date_str = (
        target_date.strftime("%m/%d")
        + f"({['月','火','水','木','金','土','日'][target_date.weekday()]})"
    )

    day_capacity = 0.0
    active_count = 0

    for m_name, m_cap in MEMBERS_DATA.items():
      key_name = f"seg_{d}_{m_name}"
      if m_name == "調整用（ヘルプ・任意）":
        custom_cap = st.session_state.get(f"custom_{d}", 0.0)
        day_capacity += custom_cap
      else:
        status = st.session_state.get(key_name, "休み")
        if status == "全日":
          day_capacity += m_cap * 1.0
          active_count += 1
        elif status == "半日":
          day_capacity += m_cap * 0.5
          active_count += 0.5

    with st.container(border=True):
      col_header, col_btn = st.columns([3, 1.2])

      with col_header:
        st.markdown(
            f"### 📅 **{date_str}** ｜ <span"
            f' style="color:#0083B8;">能力:**{day_capacity:.1f}pt**</span>'
            f" <small>({active_count:g}名)</small>",
            unsafe_allow_html=True,
        )

      def set_all_work(day_idx):
        for m in MEMBERS_DATA.keys():
          if m != "調整用（ヘルプ・任意）":
            k = f"seg_{day_idx}_{m}"
            st.session_state[k] = "全日"
            st.session_state.shift_data[k] = "全日"

      with col_btn:
        st.button(
            "👥 全員全日",
            key=f"btn_all_{d}",
            on_click=set_all_work,
            args=(d,),
            use_container_width=True,
        )

      c1, c2 = st.columns(2)
      for idx, (m_name, m_cap) in enumerate(MEMBERS_DATA.items()):
        target_col = c1 if idx % 2 == 0 else c2

        with target_col:
          if m_name == "調整用（ヘルプ・任意）":
            k = f"custom_{d}"

            def update_custom(key_str=k):
              st.session_state.shift_data[key_str] = st.session_state[key_str]

            st.number_input(
                f"⚙️ {m_name}",
                min_value=0.0,
                step=0.5,
                key=k,
                on_change=update_custom,
            )
          else:
            k = f"seg_{d}_{m_name}"

            def update_seg(key_str=k):
              st.session_state.shift_data[key_str] = st.session_state[key_str]

            options_list = ["全日", "半日", "休み"]
            label_text = f"{m_name} ({m_cap}pt)"

            if hasattr(st, "segmented_control"):
              st.segmented_control(
                  label_text,
                  options=options_list,
                  key=k,
                  on_change=update_seg,
              )
            elif hasattr(st, "pills"):
              st.pills(
                  label_text,
                  options=options_list,
                  key=k,
                  on_change=update_seg,
              )
            else:
              st.selectbox(label_text, options=options_list, key=k)

    shift_schedule[target_date] = day_capacity

# --- 4. 消化シミュレーション実行 ---
st.divider()
st.subheader("🏁 作業日ごとの完了予定 ＆ csv判定")

if not st.session_state.projects:
  st.info("左側のフォームから作業日を追加してください。")
else:
  project_queue = [dict(p) for p in st.session_state.projects]
  completion_results = []
  weekdays_ja = ["月", "火", "水", "木", "金", "土", "日"]

  # 各作業日の詳細ログ保持用リスト
  for p in project_queue:
    p["remaining"] = p["tasks"]
    p["daily_breakdown"] = []  # {'date_str': '08/10(月)', 'pt': 10.0}
    p["start_date"] = None
    p["completed_date"] = None

  current_p_idx = 0

  # シミュレーションループ
  for target_date, day_cap in shift_schedule.items():
    work_left = day_cap

    while work_left > 0 and current_p_idx < len(project_queue):
      curr_p = project_queue[current_p_idx]

      if curr_p["start_date"] is None:
        curr_p["start_date"] = target_date

      w_str = weekdays_ja[target_date.weekday()]
      d_str = f"{target_date.strftime('%m/%d')}({w_str})"

      # この日に進めるポイント数
      work_done = min(work_left, curr_p["remaining"])
      curr_p["remaining"] -= work_done
      work_left -= work_done

      curr_p["daily_breakdown"].append({"date_str": d_str, "pt": work_done})

      # ポイント消化完了時
      if curr_p["remaining"] == 0:
        curr_p["completed_date"] = target_date
        current_p_idx += 1

  # 結果判定処理
  for p in project_queue:
    p_name = p["name"]
    p_deadline = p["deadline"]
    total_tasks = p["tasks"]
    dl_w_str = weekdays_ja[p_deadline.weekday()]
    dl_str = f"{p_deadline.strftime('%m/%d')}({dl_w_str})"

    # 必須条件：csvの日付の「前日」までに完了していること
    required_completion_limit = p_deadline - datetime.timedelta(days=1)

    start_str = "-"
    if p["start_date"]:
      s_w = weekdays_ja[p["start_date"].weekday()]
      start_str = f"{p["start_date"].strftime('%m/%d')}({s_w})"

    # 【判定条件】完了日が「csv前日以前」ならOK
    if p["completed_date"]:
      comp_w = weekdays_ja[p["completed_date"].weekday()]
      comp_str = f"{p["completed_date"].strftime('%m/%d')}({comp_w})"
      is_on_time = p["completed_date"] <= required_completion_limit
      delay_days = (p["completed_date"] - required_completion_limit).days
    else:
      comp_str = "期間内に完了せず"
      is_on_time = False
      delay_days = None

    # csv前日時点での消化状況・不足pt計算
    done_by_limit = sum(
        cap
        for d_date, cap in shift_schedule.items()
        if d_date <= required_completion_limit
    )
    p_idx = project_queue.index(p)
    prior_tasks = sum(project_queue[k]["tasks"] for k in range(p_idx))
    done_for_this = max(0.0, done_by_limit - prior_tasks)
    shortage_pt = max(0.0, total_tasks - done_for_this)

    completion_results.append({
        "name": p_name,
        "total_tasks": total_tasks,
        "start_date_str": start_str,
        "completed_date": p["completed_date"],
        "completed_date_str": comp_str,
        "deadline": p_deadline,
        "deadline_str": dl_str,
        "is_on_time": is_on_time,
        "delay_days": delay_days,
        "shortage_pt": shortage_pt,
        "daily_breakdown": p["daily_breakdown"],
    })

  # 全体サマリー
  total_p = len(completion_results)
  on_time_count = sum(1 for r in completion_results if r["is_on_time"])
  delayed_count = total_p - on_time_count

  if delayed_count == 0:
    st.success(
        f"🎉 **【完璧です！】全 {total_p} 件の作業がcsvの前日までに完了する予定です。**"
    )
  else:
    st.error(
        f"⚠️ **【注意】全 {total_p} 件中、{delayed_count}"
        " 件の作業がcsvの前日までに完了しません！**（当日完了も遅延扱いになります）"
    )

  st.write("")

  # 結果カード表示
  cols = st.columns(len(st.session_state.projects))

  for i, res in enumerate(completion_results):
    with cols[i % len(cols)]:
      start_info = f"🚀 着手: **{res['start_date_str']}**\n\n"

      if res["is_on_time"]:
        # csv前日までの余裕日数
        limit_date = res["deadline"] - datetime.timedelta(days=1)
        margin = (limit_date - res["completed_date"]).days
        st.success(
            f"🟢 **{res['name']}** ({res['total_tasks']}pt)\n\n"
            f"{start_info}"
            f"🏁 完了: **{res['completed_date_str']}**\n\n"
            f"📅 csv: {res['deadline_str']} （前日比 {margin}日余裕）"
        )
      elif res["completed_date"]:
        st.error(
            f"🔴 **{res['name']}** ({res['total_tasks']}pt)\n\n"
            f"{start_info}"
            f"🏁 完了: **{res['completed_date_str']}**\n\n"
            f"📅 csv: {res['deadline_str']}\n\n"
            f"⚠️ **csv前日より {res['delay_days']}日遅延！（前日時点: {res['shortage_pt']:g}pt 不足）**"
        )
      else:
        st.error(
            f"🔴 **{res['name']}** ({res['total_tasks']}pt)\n\n"
            f"{start_info}"
            "🏁 完了: **期間内に完了せず**\n\n"
            f"📅 csv: {res['deadline_str']}\n\n"
            f"⚠️ **未完了！（前日時点: {res['shortage_pt']:g}pt 不足）**"
        )

      # 日別の着手内訳を表示するアコーディオン
      with st.expander("📅 日別の着手内訳を見る"):
        if res["daily_breakdown"]:
          for b in res["daily_breakdown"]:
            st.write(f"・**{b['date_str']}**: `{b['pt']:g} pt` 進める")
        else:
          st.write("着手予定なし")

  # 詳細一覧テーブル
  with st.expander("詳細な判定一覧を見る"):
    table_data = []
    for r in completion_results:
      if r["is_on_time"]:
        status = "✅ 間に合う（前日完了）"
      elif r["completed_date"]:
        status = f"❌ {r['delay_days']}日遅れ（前日時点: {r['shortage_pt']:g}pt不足）"
      else:
        status = (
            f"❌ シフト期間内未完（前日時点: {r['shortage_pt']:g}pt不足）"
        )

      table_data.append({
          "作業日名": r["name"],
          "ポイント数": f"{r['total_tasks']}pt",
          "着手開始日": r["start_date_str"],
          "完了予定日": r["completed_date_str"],
          "csvの日付": r["deadline_str"],
          "判定結果": status,
      })
    if table_data:
      st.dataframe(pd.DataFrame(table_data), use_container_width=True)
