import streamlit as st
import pandas as pd

# 0. 구글 시트 연결 정보 (사용자님이 주신 ID 적용)
SHEET_ID = "1Rb5SLoJqjOw1G7sWrIwwq4SzqCmhu-Ng8SrkddtZvMs"
SHEET_NAME = "Sheet1"  # 만약 엑셀 시트 하단 이름이 'Sheet1'이 아니면 그 이름으로 바꿔주세요
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

st.set_page_config(page_title="KIC 실시간 클라우드 전산", layout="wide")

# 1. 실시간 데이터 로드 함수
@st.cache_data(ttl=60) # 1분마다 자동으로 새 데이터를 업데이트합니다.
def load_data():
    return pd.read_csv(URL)

try:
    df = load_data()

    # 2. 사이드바
    with st.sidebar:
        st.title("🌐 KIC CMS")
        st.success("구글 클라우드 연결됨")
        menu = st.radio("메뉴", ["📊 실시간 대시보드", "🔍 데이터 상세조회"])
        if st.button("🔄 데이터 강제 새로고침"):
            st.cache_data.clear()
            st.rerun()

    if menu == "📊 실시간 대시보드":
        st.title("📊 KIC 실시간 업무 현황 (Cloud)")
        
        # 지표 계산
        total = len(df)
        # 엑셀의 '교정상태' 컬럼을 기준으로 카운트
        status = df['교정상태'].value_counts() if '교정상태' in df.columns else {}
        
        c1, c2, c3 = st.columns(3)
        c1.metric("총 접수 건수", f"{total} 건")
        c2.metric("사외대기", f"{status.get('사외대기', 0)} 건")
        c3.metric("계산대기", f"{status.get('계산대기', 0)} 건")
        
        st.divider()
        st.subheader("🏢 업체별 접수 현황 (Top 10)")
        if '업체명' in df.columns:
            st.bar_chart(df['업체명'].value_counts().head(10))

    elif menu == "🔍 데이터 상세조회":
        st.title("🔍 데이터 실시간 검색")
        search = st.text_input("업체명 또는 계측기명을 입력하세요")
        
        if search:
            # 업체명 또는 계측기명에 검색어가 포함된 데이터 필터링
            mask = df.astype(str).apply(lambda x: x.str.contains(search, na=False)).any(axis=1)
            filtered_df = df[mask]
            st.write(f"검색 결과: {len(filtered_df)}건")
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("⚠️ 구글 시트 데이터를 불러올 수 없습니다.")
    st.info("체크리스트: 1. 구글 시트 공유 설정이 '링크가 있는 모든 사용자-뷰어'인가? 2. 시트 탭 이름이 'Sheet1'인가?")
    st.write(f"오류 내용: {e}")