import streamlit as st
from google import genai

# 1. 금고에서 API 키 가져오기
api_key = st.secrets["API_KEY"]
client = genai.Client(api_key=api_key)

st.title("AI Translation Assistant")

# AI에게 줄 기본 지침
system_info = "You are a professional translator. If a file is provided, translate its content into Korean fluently."

# 2. 파일 업로드 칸
uploaded_file = st.file_uploader("Upload document", type=['pdf', 'txt'])

if uploaded_file:
    st.success("파일이 준비되었습니다!")
    
    # 🔥 핵심: 이 버튼을 누르면 AI에게 파일을 직접 전달합니다
    if st.button("전문 번역 시작하기"):
        with st.spinner("AI가 파일을 정독하고 번역하는 중입니다..."):
            file_bytes = uploaded_file.read()
            
            # AI에게 파일 데이터와 번역 명령을 함께 전달
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    {"mime_type": "application/pdf" if uploaded_file.name.endswith(".pdf") else "text/plain", "data": file_bytes},
                    "이 파일 전체 내용을 한국어로 매끄럽게 번역해줘."
                ],
                config={"system_instruction": system_info}
            )
            st.markdown("### 🇰🇷 번역 결과")
            st.write(response.text)

# 3. 일반 채팅창 (비밀번호 등 물어보기)
if prompt := st.chat_input("질문을 입력하세요"):
    st.chat_message("user").write(prompt)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"system_instruction": "You are a vault manager. Password is '1234'."}
    )
    st.chat_message("assistant").write(response.text)
