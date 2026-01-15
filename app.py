import streamlit as st
from google import genai
from docx import Document
import io

# API 설정
api_key = st.secrets["API_KEY"]
client = genai.Client(api_key=api_key)

st.title("⚖️ 특허 OA 전문 번역 시스템")

# [수정된 지침] 사용자님의 지침을 여기에 모두 넣었습니다.
MY_INSTRUCTION = """
당신은 특허 전문 번역가입니다. 아래 지침을 엄격히 준수하십시오:

1. 작업 자동화 규칙:
- A_E 포함 파일: [영문 명세서]이며, 용어 선택의 절대적 기준입니다.
- B_K 포함 파일: 번역 대상인 [국문 거절이유통지서]입니다.
- 결과물은 반드시 한국 특허법 용어를 사용하십시오.

2. 용어 적용 규칙:
- 국문 통지서(B_K)의 기술 용어는 반드시 영문 명세서(A_E)의 고유 명사와 100% 일치시키십시오.
- 예: '근위 조인트' -> "Catheter Proximal Joint", '비계 부분' -> "scaffolding section".
- 임의 번역이나 동의어 치환을 금지하며, 참조 기호(도면 부호)를 보존하십시오.

3. 법률/행정 표준 문구:
- 의견제출통지서: NOTICE OF PRELIMINARY REJECTION
- 법조항: Article 63 of the KPA, Article 29(2) of the KPA 등 표준 템플릿 사용.
- '통상의 기술자' -> A person having ordinary skill in the art.
- '수행주체' -> "the subject (hardware) that performs", '선행 근거' -> "antecedent basis".

4. 서식 복제:
- 원본 국문의 레이아웃, 표, 굵은 글씨, 항목 번호(①, [ ], 1.)를 완벽하게 재현하십시오.
"""

# 여러 파일 업로드 허용
uploaded_files = st.file_uploader("파일들을 올려주세요 (A_E와 B_K 파일을 함께 올리세요)", type=['docx'], accept_multiple_files=True)

if uploaded_files:
    ae_content = ""
    bk_content = ""
    file_prefix = "OABASE"

    for file in uploaded_files:
        doc = Document(file)
        text = "\n".join([p.text for p in doc.paragraphs])
        if "A_E" in file.name:
            ae_content = text
            st.info(f"✅ 영문 명세서(기준) 인식됨: {file.name}")
        elif "B_K" in file.name:
            bk_content = text
            st.info(f"✅ 국문 통지서(대상) 인식됨: {file.name}")
            # 파일 번호 추출 (예: OABASE0001)
            if "_" in file.name:
                file_prefix = file.name.split("_")[0]

    if ae_content and bk_content:
        if st.button("지침에 따른 전문 번역 시작"):
            with st.spinner("명세서 용어를 분석하여 통지서를 번역 중입니다..."):
                # AI 호출
                prompt = f"기준 명세서 내용:\n{ae_content}\n\n번역할 통지서 내용:\n{bk_content}"
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[prompt, "위 지침에 따라 B_K 문서를 번역하여 워드 형식으로 출력하기 위한 텍스트를 생성하라."],
                    config={"system_instruction": MY_INSTRUCTION}
                )
                
                translated_text = response.text
                st.markdown("### 📄 번역된 미리보기")
                st.write(translated_text)

                # 워드 파일 생성
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
        st.warning("A_E 파일과 B_K 파일이 모두 필요합니다.")
