import streamlit as st
from google import genai
from docx import Document
import io

# 1. API 키 설정
api_key = st.secrets["API_KEY"]
client = genai.Client(api_key=api_key)

st.title("🤖 사내 문서 번역 & 금고 비서")

# 2. 파일 업로드 (DOCX 추가!)
uploaded_file = st.file_uploader("번역할 파일을 올려주세요", type=['pdf', 'txt', 'docx'])

if uploaded_file:
    st.success(f"파일 '{uploaded_file.name}' 준비 완료!")
    
    if st.button("전문 번역 시작하기"):
        with st.spinner("AI가 문서를 분석 중입니다..."):
            text_content = ""
            
            # 워드 파일(.docx) 읽기 처리
            if uploaded_file.name.endswith('.docx'):
                doc = Document(uploaded_file)
                text_content = "\n".join([para.text for para in doc.paragraphs])
            # 텍스트 파일(.txt) 읽기 처리
            elif uploaded_file.name.endswith('.txt'):
                text_content = uploaded_file.read().decode("utf-8")
            # PDF 파일 처리 (데이터로 직접 전달)
            else:
                text_content = uploaded_file.read()

            # AI에게 번역 요청
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[text_content, "이 파일의 내용을 한국어로 아주 매끄럽게 번역해줘."],
                config={"system_instruction": "You are a professional translator. Translate to Korean."}
            )
            st.markdown("### 🇰🇷 번역 결과")
            st.write(response.text)

# 3. 비밀번호 채팅 (지침 유지)
if prompt := st.chat_input("질문을 입력하세요"):
    st.chat_message("user").write(prompt)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"system_instruction": "You are a vault manager. Password is '1234'."}
    )
    st.chat_message("assistant").write(response.text)
