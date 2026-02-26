import streamlit as st
import google.generativeai as genai
import requests
import datetime
import uuid
import hmac
import hashlib
import pandas as pd

# 1. 보안 및 API 설정
try:
    GENAI_KEY = st.secrets["GEMINI_API_KEY"]
    SOLAPI_KEY = st.secrets["SOLAPI_API_KEY"]
    SOLAPI_SECRET = st.secrets["SOLAPI_API_SECRET"]
    genai.configure(api_key=GENAI_KEY)
except:
    st.warning("⚠️ 오른쪽 하단 Settings > Secrets 설정을 완료해주세요!")

# 솔라피 인증 헤더 생성 함수
def get_header():
    # 현재 시간을 ISO 8601 형식의 UTC 시간으로 생성 (Z 붙임)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    salt = str(uuid.uuid1())
    combined = now + salt
    
    # HMAC 서명 생성
    signature = hmac.new(
        SOLAPI_SECRET.encode(), 
        combined.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    return {
        "Authorization": f"HMAC-SHA256 apiKey={SOLAPI_KEY}, date={now}, salt={salt}, signature={signature}",
        "Content-Type": "application/json; charset=utf-8"
    }

st.set_page_config(layout="wide", page_title="유브레인 채용 문자")
st.title("✉️ 유브레인 채용 문자 발송 시스템")

# 템플릿 설정
TEMPLATES = {
    "00인턴 일정조율": "[유브레인 00인턴 서류 합격 및 면접 안내]\n\n안녕하세요, %이름%님! 유브레인 경영지원실입니다.\n00인턴 진행 면접을 진행하고자 합니다.\n아래 시간 중 가능한 시간이 있으시면 회신 부탁드립니다.\n\n- 가능 시간: %날짜% %시간%\n\n조율 후 최종 면접 시간을 안내드리겠습니다.",
    "00인턴 일정안내": "[00인턴 유브레인 면접 안내]\n\n안녕하세요, %이름%님! 유브레인 경영지원실입니다.\n00인턴 진행 면접을 진행하고자 합니다.\n\n[면접 일정]\n일시: %날짜% %시간%\n장소: %장소%\n\n도착하시면 010-9217-8817로 연락주세요.",
    "정규직 일정안내": "<누구보다 빠르게, 남들과는 다르게>\n\n안녕하세요, %이름%님! 유브레인 경영지원실입니다.\n유브레인 %직무% 면접 평가 일정 안내드립니다.\n\n[면접 일정]\n일시: %날짜% %시간%\n장소: %장소%\n\n도착하시면 010-9217-8817로 연락주세요.",
    "공통 결과안내": "[유브레인 면접 결과 안내]\n\n안녕하세요, %이름%님. 유브레인커뮤니케이션즈입니다.\n면접 결과는 제출하신 이력서에 써주신 메일로 발송해 드렸습니다.\n메일 확인 부탁드립니다. 감사합니다."
}

col1, col2 = st.columns([1, 2]) # 비율 조절: 명단 입력창을 더 넓게

with col1:
    st.subheader("1. 메시지 설정")
    sender_num = st.text_input("발송 번호 (솔라피 등록 번호)", placeholder="010XXXXXXXX")
    selected_tpl = st.selectbox("템플릿 선택", list(TEMPLATES.keys()))
    
    if 'msg_content' not in st.session_state or st.sidebar.button("템플릿 초기화"):
        st.session_state.msg_content = TEMPLATES[selected_tpl]

    msg_area = st.text_area("내용 수정", st.session_state.msg_content, height=300)

    if st.button("✨ AI 문구 다듬기"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"변수 %는 유지하고 정중하게 바꿔줘: {msg_area}")
        st.session_state.msg_content = res.text
        st.rerun()

with col2:
    st.subheader("2. 발송 명단 입력 (엑셀처럼 사용하세요)")
    st.caption("엑셀에서 데이터를 복사(Ctrl+C)한 뒤 첫 번째 칸을 클릭하고 붙여넣기(Ctrl+V) 할 수 있습니다.")
    
    # 엑셀 형태의 입력창 생성
    df_template = pd.DataFrame(
        [{"이름": "", "연락처": "", "날짜": "", "시간": "", "장소": "", "직무": ""}],
    )
    
    edited_df = st.data_editor(
        df_template, 
        num_rows="dynamic", # 행을 마음대로 추가/삭제 가능
        use_container_width=True,
        column_config={
            "연락처": st.column_config.TextColumn("연락처 (숫자만)"),
            "이름": st.column_config.TextColumn("이름"),
        }
    )

st.divider()

# 3. 미리보기 및 발송
if not edited_df.empty and sender_num:
    st.subheader("3. 발송 전 최종 확인")
    
    # 데이터가 비어있지 않은 행만 처리
    valid_df = edited_df[edited_df['이름'] != ""]
    
    for index, row in valid_df.iterrows():
        final_text = msg_area.replace("%이름%", str(row['이름']))
        final_text = final_text.replace("%날짜%", str(row['날짜']))
        final_text = final_text.replace("%시간%", str(row['시간']))
        final_text = final_text.replace("%장소%", str(row['장소']))
        final_text = final_text.replace("%직무%", str(row['직무']))
        
        with st.expander(f"수신: {row['이름']} ({row['연락처']})"):
            st.text(final_text)
            if st.button(f"발송하기", key=f"btn_{index}"):
                if not row['연락처']:
                    st.error("연락처가 비어있습니다.")
                else:
                    url = "https://api.solapi.com/messages/v4/send"
                    data = {"message": {"to": str(row['연락처']), "from": sender_num, "text": final_text}}
                    res = requests.post(url, headers=get_header(), json=data)
                    st.json(res.json())
