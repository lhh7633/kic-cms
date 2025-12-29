import streamlit as st
import pandas as pd
import json
from google.oauth2.credentials import Credentials  # OAuth용 인증 모듈
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# 1. 설정 (확인된 정확한 ID 값들)
SPREADSHEET_ID = "1q1GuRNow4naFj87WmznVTT00SSH4yhuiLQykVEjKww"
FOLDER_ID = "1xk5ERGG6qEHQoVcCvOtJbbiAq35ITVFc"

# 2. 구글 서비스 인증 함수 (OAuth 방식 - 개인 계정 권한 사용)
def get_gcp_credentials():
    # Secrets에 저장된 토큰 정보를 가져옴
    token_info = json.loads(st.secrets["google_token"]["token_json"])
    
    # 토큰 정보를 이용해 인증 객체 생성
    creds = Credentials.from_authorized_user_info(token_info)
    return creds

# 3. 메인 앱 화면 설정
st.set_page_config(page_title="KIC 교정관리시스템", layout="wide")
st.title("📟 KIC 교정관리시스템 (CMS)")

# 서비스 연결 상태 확인
try:
    creds = get_gcp_credentials()
    sheet_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    st.sidebar.success("✅ 구글 서비스 연결 성공")
except Exception as e:
    st.sidebar.error(f"❌ 연결 실패: {e}")

# 4. 신규 접수 입력 폼
st.subheader("📥 신규 접수 및 성적서 등록")
with st.form("registration_form"):
    col1, col2 = st.columns(2)
    with col1:
        reg_num = st.text_input("A. 접수번호", placeholder="예: 25031380")
        company = st.text_input("B. 업체명")
        device_name = st.text_input("C. 계측기명")
    with col2:
        device_id = st.text_input("D. 기기번호")
        status = st.selectbox("E. 상태", ["접수대기", "교정중", "교정완료", "발송완료"])
        uploaded_file = st.file_uploader("F. 성적서 파일 업로드", type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'csv'])

    submit_button = st.form_submit_button("데이터 저장 및 파일 업로드")

# 5. 버튼 클릭 시 작동 로직
if submit_button:
    if not reg_num or not company:
        st.warning("접수번호와 업체명은 필수 입력 사항입니다.")
    else:
        try:
            with st.spinner("처리 중..."):
                file_link = "파일 없음"
                
                # (1) 구글 드라이브 파일 업로드
                if uploaded_file is not None:
                    file_metadata = {
                        'name': uploaded_file.name,
                        'parents': [FOLDER_ID]
                    }
                    media = MediaIoBaseUpload(
                        io.BytesIO(uploaded_file.getvalue()), 
                        mimetype=uploaded_file.type, 
                        resumable=True
                    )
                    
                    # OAuth 방식은 별도 옵션 없이도 개인 권한으로 업로드됩니다.
                    file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink'
                    ).execute()
                    file_link = file.get('webViewLink')

                # (2) 구글 시트에 데이터 기록
                new_row = [reg_num, company, device_name, device_id, status, file_link]
                sheet_service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID,
                    range="시트1!A2",
                    valueInputOption="USER_ENTERED",
                    body={"values": [new_row]}
                ).execute()

                st.success(f"✅ 완료! 접수번호 {reg_num} 데이터가 저장되었습니다.")
                st.balloons()
        
        except Exception as e:
            st.error(f"❌ 작업 중 오류 발생: {e}")

# 6. 실시간 현황판
st.divider()
st.subheader("📊 실시간 접수 현황 (구글 시트)")
try:
    result = sheet_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="시트1!A:F"
    ).execute()
    values = result.get('values', [])

    if not values:
        st.info("표시할 데이터가 없습니다.")
    else:
        df = pd.DataFrame(values[1:], columns=values[0])
        st.dataframe(df, use_container_width=True)
except Exception as e:
    st.info("데이터를 불러오는 중입니다...")
