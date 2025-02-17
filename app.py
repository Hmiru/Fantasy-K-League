import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import gspread
import urllib.parse
import json
import pandas as pd

secrets_json = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]  # ✅ TOML에서 가져옴
creds_dict = json.loads(secrets_json)  # JSON 문자열을 Python 딕셔너리로 변환

# 📌 Google Sheets API 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)  # ✅ 파일 대신 딕셔너리 사용
client = gspread.authorize(creds)  # ✅ Google Sheets 접근

# 📌 Google Sheets 연결
spreadsheet = client.open("팀_raw_data")  # Google Sheets 제목

sheets = spreadsheet.worksheets()  # 모든 팀별 시트 가져오기

# 📌 모든 팀 데이터를 하나의 DataFrame으로 합치기
all_data = []
for sheet in sheets:
    team_name = sheet.title  # 시트 이름이 팀명
    team_data = sheet.get_all_records()
    df_team = pd.DataFrame(team_data)
    df_team["소속팀"] = team_name  # 팀 컬럼 추가
    all_data.append(df_team)


df_all = pd.concat(all_data, ignore_index=True)

# ✅ 데이터 정리: 빈 값을 0으로 변환하고 정수형(int)으로 변환
numeric_cols = ["출전시간", "FKL 포인트", "득점", "도움", "클린시트", "선방", "보너스 포인트", "경고", "퇴장"]
for col in numeric_cols:
    df_all[col] = pd.to_numeric(df_all[col], errors="coerce").fillna(0).astype(int)


# 📌 선수별 포인트 합산
df_ranking = df_all.groupby(["이름", "소속팀", "포지션"], as_index=False).agg({
    "출전시간": "sum",  # 모든 라운드 출전시간 합산
    "FKL 포인트": "sum",  # 모든 라운드 포인트 합산
    "득점": "sum",  
    "도움": "sum",
    "클린시트": "sum",
    "선방": "sum",  
    "보너스 포인트": "sum",
    "경고": "sum",
    "퇴장": "sum"
})

# 📌 포인트 기준으로 정렬 (내림차순)
df_ranking = df_ranking.sort_values(by="FKL 포인트", ascending=False)

def make_clickable(name):
    return f'<a href="?player={name}" target="_self">{name}</a>'
df_ranking["이름"] = df_ranking["이름"].apply(make_clickable)

# 📌 Streamlit UI
st.title("🏆 K리그 판타지 리그 - 포인트 순위표")
st.markdown(
    """
    <style>
        table {
            width: 100%; /* 테이블을 가득 채움 */
        }
        th, td {
            white-space: nowrap; /* 글자가 자동 줄바꿈되지 않게 설정 */
            padding: 10px;
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

selected_team = st.sidebar.selectbox("📌 팀을 선택하세요", ["전체"] + df_ranking["소속팀"].unique().tolist(), key="team_selectbox")

if selected_team != "전체":
    df_ranking = df_ranking[df_ranking["소속팀"] == selected_team]

if "selected_player" not in st.session_state:
    st.session_state["selected_player"] = None  # 기본값 설정

query_params = st.query_params
selected_player = query_params.get("player", [])

if selected_player:
    print(selected_player)
    st.session_state["selected_player"] = selected_player  # URL에서 가져온 값으로 갱신

if st.session_state["selected_player"] is None:
    # ✅ 선수 선택이 안 된 경우 → 기본 포인트 순위표 표시
    st.write("### 선수 포인트 랭킹")
    st.markdown(df_ranking.to_html(escape=False, index=False), unsafe_allow_html=True)

else:
    # ✅ 선수 선택된 경우 → 히스토리 테이블로 전환
    selected_player = st.session_state["selected_player"]
    
    st.write(f"## {selected_player} 경기별 히스토리")

    # 선택한 선수의 경기별 히스토리 필터링
    player_history = df_all[df_all["이름"] == selected_player]

    # 선수 경기 기록 출력
    st.table(player_history[["소속팀", "라운드","상대팀","출전시간", "FKL 포인트", "득점", "도움", "클린시트", "선방", "보너스 포인트", "경고", "퇴장"]].reset_index(drop=True))

    # 뒤로 가기 버튼
    if st.button("🔙 뒤로 가기"):
        st.session_state.update({"selected_player": None})  # 값 초기화
        st.rerun()  # 페이지 새로고침 (순위표 다시 표시)