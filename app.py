import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import datetime

# --- 1. 환경 설정 ---
# 시트 ID와 폴더 ID는 사용자님의 것으로 유지합니다.
SPREADSHEET_ID = '1q1GuRNow4naFj87WmznVTT00SSH4yhyuiLQykVEjKww' 
FOLDER_ID = '1xk5ERGG6qEHqoVcCv0tJbbiAq3SITVFc'

# 구글 API 권한 설정
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# --- 2. 인증 및 서비스 연결 함수 ---
def get_gspread_service():
    try:
        # 1순위: Streamlit Cloud의 Secrets 확인 (배포용)
        if "gcp_service_account" in st.secrets:
            # TOML 데이터를 파이썬 딕셔너리로 변환
            creds_info = st.secrets["gcp_service_account"].to_dict()
            
            # private_key의 줄바꿈 문자(\n)가 텍스트로 인식될 경우를 대비해 치환
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            
        # 2순위: 로컬의 json 파일 확인 (내 컴퓨터 테스트용)
        else:
            creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        
        sheet_service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return sheet_service, drive_service
    except Exception as e:
        st.error(f"⚠️ 인증 실패: {e}")
        return None, None

# 서비스 초기화
sheet_service, drive_service = get_gspread_service()

# --- 3. 화면 구성 ---
st.set_page_config(page_title="KIC CMS 업로드 시스템", layout="wide")
st.title("📟 KIC 교정관리시스템 (CMS)")

# 사이드바 구성
with st.sidebar:
    st.header("관리 메뉴")
    if sheet_service:
        st.success("✅ 구글 서비스 연결 성공")
    else:
        st.error("❌ 연결 안 됨 (Secrets 확인 필요)")

# 데이터 입력 폼
with st.form("upload_form", clear_on_submit=True):
    st.subheader("📥 신규 접수 및 성적서 등록")
    
    col1, col2 = st.columns(2)
    with col1:
        reg_num = st.text_input("A. 접수번호", placeholder="예: 25031380")
        company = st.text_input("B. 업체명")
        device = st.text_input("C. 계측기명")
    with col2:
        device_num = st.text_input("D. 기기번호")
        status = st.selectbox("E. 상태", ["접수대기", "교정중", "교정완료", "발송완료"])
        uploaded_file = st.file_uploader("F. 성적서 파일 업로드", type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'csv'])

    submit_button = st.form_submit_button("데이터 저장 및 파일 업로드")

# --- 4. 저장 로직 ---
if submit_button:
    if not reg_num or not company:
        st.warning("접수번호와 업체명은 필수 입력 사항입니다.")
    elif not sheet_service:
        st.error("구글 서비스와 연결되지 않았습니다. Secrets 설정을 확인하세요.")
    else:
        try:
            file_link = "파일 없음"
            
            # 4-1. 파일이 있으면 구글 드라이브에 업로드
            if uploaded_file is not None:
                file_metadata = {
                    'name': f"[{reg_num}]_{uploaded_file.name}",
                    'parents': [FOLDER_ID]
                }
                media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getvalue()), mimetype=uploaded_file.type)
                file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
                file_link = file.get('webViewLink')

            # 4-2. 구글 시트에 데이터 추가
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            new_row = [now, reg_num, company, device, device_num, status, file_link]
            
            body = {'values': [new_row]}
            sheet_service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="시트1!A:G",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()

            st.balloons()
            st.success(f"✅ 저장 완료! (접수번호: {reg_num})")
            
        except Exception as e:
            st.error(f"❌ 작업 중 오류 발생: {e}")

# --- 5. 실시간 현황 ---
st.divider()
st.subheader("📊 실시간 접수 현황 (구글 시트)")
if sheet_service:
    try:
        result = sheet_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range="시트1!A:G").execute()
        values = result.get('values', [])
        if values:
            df = pd.DataFrame(values[1:], columns=values[0])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("시트에 데이터가 없습니다.")
    except Exception as e:
        st.info("데이터를 불러오는 중입니다...")