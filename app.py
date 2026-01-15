import streamlit as st
from google import genai
from docx import Document
from pypdf import PdfReader
import io

# API 설정
api_key = st.secrets["API_KEY"]
client = genai.Client(api_key=api_key)

st.title("⚖️ 특허 OA 전문 번역 시스템 (PDF/DOCX 지원)")

# [지침] 사용자님의 지침 유지
MY_INSTRUCTION = """
당신은 특허 전문 번역가입니다. 아래 지침을 엄격히 준수하십시오:
1. A_E 포함 파일은 [영문 명세서] 기준이며, B_K 포함 파일은 번역 대상인 [국문 통지서]입니다.
2. 국문 통지서의 기술 용어는 반드시 영문 명세서의 용어와 100% 일치시키십시오.
3. 법률 문구 표준화: '의견제출통지서' -> NOTICE OF PRELIMINARY REJECTION 등.
4. 원본의 서식(항목 번호, 굵은 글씨 등)을 최대한 복제하십시오.
"""

# PDF와 DOCX 모두 허용
uploaded_files = st.file_uploader("파일들을 올려주세요 (PDF 또는 DOCX)", type=['docx', 'pdf'], accept_multiple_files=True)

if uploaded_files:
    ae_content = ""
    bk_content = ""
    file_prefix = "OABASE"

    for file in uploaded_files:
        # 파일 형식에 따라 텍스트 추출 방식 결정
        if file.name.endswith('.docx'):
            doc = Document(file)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif file.name.endswith('.pdf'):
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        
        # 파일명 규칙에 따라 분류
        if "A_E" in file.name:
            ae_content = text
            st.info(f"✅ 영문 명세서 인식됨: {file.name}")
        elif "B_K" in file.name:
            bk_content = text
            st.info(f"✅ 국문 통지서 인식됨: {file.name}")
            if "_" in file.name:
                file_prefix = file.name.split("_")[0]

    if ae_content and bk_content:
        if st.button("지침에 따른 전문 번역 시작"):
            with st.spinner("명세서 용어를 분석하여 번역 중입니다..."):
                prompt = f"기준 명세서 내용:\n{ae_content}\n\n번역할 통지서 내용:\n{bk_content}"
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[prompt, "위 지침에 따라 B_K 문서를 번역하여 결과물을 출력하라."],
                    config={"system_instruction": MY_INSTRUCTION}
                )
                
                translated_text = response.text
                st.markdown("### 📄 번역 미리보기")
                st.write(translated_text)

                # 워드로 결과물 생성
                output_doc = Document()
                output_doc.add_paragraph(translated_text)
                target_stream = io.BytesIO()
                output_doc.save(target_stream)
                
                st.download_button(
                    label="📥 워드 파일 다운로드 (.docx)",
                    data=target_stream.getvalue(),
                    file_name=f"{file_prefix}_C_E.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    else:
        st.warning("기준이 되는 A_E 파일과 번역 대상인 B_K 파일이 모두 필요합니다.")
