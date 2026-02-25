import streamlit as st
import google.generativeai as genai
from solapi_python import solapi

# 1. 보안 설정 (Streamlit Secrets에서 가져오기)
try:
    GENAI_KEY = st.secrets["GEMINI_API_KEY"]
    SOLAPI_KEY = st.secrets["SOLAPI_API_KEY"]
    SOLAPI_SECRET = st.secrets["SOLAPI_API_SECRET"]
    
    genai.configure(api_key=GENAI_KEY)
    msg_service = solapi.MessageService(SOLAPI_KEY, SOLAPI_SECRET)
except Exception as e:
    st.warning("⚠️ 오른쪽 하단 Settings > Secrets에서 API 키 설정을 먼저 해주세요!")

st.set_page_config(layout="wide", page_title="유브레인 채용 문자 시스템")
st.title("✉️ 유브레인 채용 문자 발송 시스템")

# 2. 템플릿 데이터 설정
TEMPLATES = {
    "00인턴 일정조율": "[유브레인 00인턴 서류 합격 및 면접 안내]\n\n안녕하세요, %이름%님! 유브레인 경영지원실입니다.\n00인턴 진행 면접을 진행하고자 합니다.\n아래 시간 중 가능한 시간이 있으시면 회신 부탁드립니다.\n\n- 가능 시간: %날짜% %시간%\n\n조율 후 최종 면접 시간을 안내드리겠습니다.",
    "00인턴 일정안내": "[00인턴 유브레인 면접 안내]\n\n안녕하세요, %이름%님! 유브레인 경영지원실입니다.\n00인턴 진행 면접을 진행하고자 합니다.\n\n[면접 일정]\n일시: %날짜% %시간%\n장소: %장소%\n\n도착하시면 010-9217-8817로 연락주세요.",
    "정규직 일정안내": "<누구보다 빠르게, 남들과는 다르게>\n\n안녕하세요, %이름%님! 유브레인 경영지원실입니다.\n유브레인 %직무% 면접 평가 일정 안내드립니다.\n\n[면접 일정]\n일시: %날짜% %시간%\n장소: %장소%\n\n도착하시면 010-9217-8817로 연락주세요.",
    "공통 결과안내": "[유브레인 면접 결과 안내]\n\n안녕하세요, %이름%님. 유브레인커뮤니케이션즈입니다.\n면접 결과는 제출하신 이력서에 써주신 메일로 발송해 드렸습니다.\n메일 확인 부탁드립니다. 감사합니다."
}

col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader("1. 메시지 설정")
    sender_num = st.text_input("발송 번호 (솔라피 등록 번호)", placeholder="예: 01012345678")
    selected_tpl = st.selectbox("템플릿 선택", list(TEMPLATES.keys()))
    
    # 템플릿 내용을 텍스트 영역에 표시
    if 'current_msg' not in st.session_state or st.session_state.last_tpl != selected_tpl:
        st.session_state.current_msg = TEMPLATES[selected_tpl]
        st.session_state.last_tpl = selected_tpl

    current_msg = st.text_area("메시지 수정 (%변수% 유지)", st.session_state.current_msg, height=250)
    
    if st.button("✨ AI 문구 부드럽게 다듬기"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"다음 채용 문구에서 %로 된 변수는 유지하고, 전체 말투만 더 친절하게 바꿔줘:\n{current_msg}")
        st.session_state.current_msg = res.text
        st.rerun()

with col2:
    st.subheader("2. 명단 입력")
    st.caption("형식: %이름% / 연락처 / %날짜% / %시간% / %장소% / %직무%")
    user_input = st.text_area("명단을 한 줄씩 입력하세요", height=350, 
                             placeholder="홍길동 / 01012345678 / 3월 4일 / 14:00 / 3층 / 영상PD")

st.divider()

# 3. 미리보기 및 발송
if user_input and sender_num:
    st.subheader("3. 발송 전 최종 확인")
    lines = user_input.strip().split('\n')
    
    for line in lines:
        if '/' in line:
            p = [i.strip() for i in line.split('/')]
            if len(p) >= 2:
                final_msg = current_msg.replace("%이름%", p[0])
                keys = ["%이름%", "%연락처%", "%날짜%", "%시간%", "%장소%", "%직무%"]
                for i, key in enumerate(keys):
                    if i < len(p): final_msg = final_msg.replace(key, p[i])
                
                with st.expander(f"수신: {p[0]} ({p[1]})"):
                    st.text(final_msg)
                    if st.button(f"발송하기", key=p[1]):
                        # 솔라피 발송 로직
                        data = {'message': {'to': p[1], 'from': sender_num, 'text': final_msg}}
                        try:
                            res = msg_service.send_one(data)
                            st.success(f"발송 성공! (ID: {res.json()['messageId']})")
                        except Exception as e:
                            st.error(f"발송 실패: {e}")
