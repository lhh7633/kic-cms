import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import datetime

# --- 1. 환경 설정 (전달해주신 ID 적용) ---
SERVICE_ACCOUNT_FILE = 'service_account.json'  # 서비스 계정 키 파일명
SPREADSHEET_ID = '1q1GuRNow4naFj87WMznVTT00SSH4yhyuiLQykVEjKww'
FOLDER_ID = '1xk5ERGG6qEHQoVcCvOtJbbiAq35ITVFc'

# 구글 API 권한 설정
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# API 연결 함수
def get_gspread_service():
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        sheet_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return sheet_service, drive_service
    except Exception as e:
        st.error(f"인증 파일 확인 실패: {e}")
        return None, None

sheet_service, drive_service = get_gspread_service()

# --- 2. 화면 구성 ---
st.set_page_config(page_title="KIC CMS 업로드 시스템", layout="wide")
st.title("📟 KIC 교정관리시스템 (CMS)")

# 사이드바 구성
with st.sidebar:
    st.header("관리 메뉴")
    st.info("현재 구글 시트 및 드라이브와 연결됨")

# 데이터 입력 폼
with st.form("upload_form", clear_on_submit=True):
    st.subheader("📥 신규 접수 및 성적서 등록")
    
    col1, col2 = st.columns(2)
    with col1:
        reg_num = st.text_input("A. 접수번호", placeholder="예: 25031380")
        company = st.text_input("B. 업체명")
        device = st.text_input("C. 계측기명")
    with col2:
        serial = st.text_input("D. 기기번호")
        status = st.selectbox("E. 상태", ["접수대기", "입고완료", "교정중", "교정완료"])
        # 파일 업로드 (성적서 링크용)
        uploaded_file = st.file_uploader("F. 성적서 파일 업로드 (PDF, 이미지 등)", type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'csv'])
    
    submit_button = st.form_submit_button("데이터 저장 및 파일 업로드")

# --- 3. 저장 로직 ---
if submit_button:
    if not reg_num or not company:
        st.error("접수번호와 업체명은 필수 입력 사항입니다.")
    elif sheet_service is None:
        st.error("구글 서비스 인증에 실패했습니다. service_account.json 파일을 확인하세요.")
    else:
        with st.spinner("구글 클라우드에 데이터를 기록 중입니다..."):
            try:
                file_link = ""
                
                # (1) 구글 드라이브에 파일 업로드
                if uploaded_file is not None:
                    file_metadata = {
                        'name': f"{reg_num}_{uploaded_file.name}", # 파일명 앞에 접수번호를 붙여 관리하기 편하게 함
                        'parents': [FOLDER_ID]
                    }
                    media = MediaIoBaseUpload(io.BytesIO(uploaded_file.read()), mimetype=uploaded_file.type)
                    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
                    file_link = file.get('webViewLink')

                # (2) 구글 시트에 데이터 기록 (A~F열 순서)
                # 시트에 적으신 순서: [접수번호, 업체명, 계측기명, 기기번호, 상태, 성적서링크]
                new_row = [reg_num, company, device, serial, status, file_link]
                
                body = {'values': [new_row]}
                sheet_service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID,
                    range="Sheet1!A2", # A1은 제목이므로 A2부터 추가
                    valueInputOption="USER_ENTERED",
                    body=body
                ).execute()
                
                st.success(f"✅ [{company}] 데이터가 성공적으로 저장되었습니다!")
                if file_link:
                    st.info(f"🔗 [업로드된 성적서 확인하기]({file_link})")
            
            except Exception as e:
                st.error(f"오류 발생: {e}")

# --- 4. 시트 데이터 실시간 조회 ---
st.divider()
st.subheader("📊 실시간 접수 현황 (구글 시트)")

try:
    if sheet_service:
        # 데이터 가져오기
        result = sheet_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:F").execute()
        values = result.get('values', [])
        
        if len(values) > 1:
            # 첫 번째 줄은 헤더(제목), 그 다음부터는 데이터
            df_display = pd.DataFrame(values[1:], columns=values[0])
            st.dataframe(df_display, use_container_width=True)
        else:
            st.write("현재 등록된 데이터가 없습니다. 첫 행에 제목을 적으셨는지 확인하세요.")
except Exception as e:
    st.info("시트 데이터를 불러오는 중입니다. 잠시만 기다려주세요.")