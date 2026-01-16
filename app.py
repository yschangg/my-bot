import re
import io
from datetime import datetime

import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
from docx.shared import Pt


# =========================
# Fixed System Instruction (Embedded)
# =========================
MY_INSTRUCTION = r"""
### 특허 OA 전문 번역 시스템 최종 통합 지침 (v2.1 - 누락 방지 완결본)

당신은 거예통지서를 영문으로 번역하는  **'기계적 번역 엔진(Mechanical Translation Engine)'**이다. 문학적 윤색, 의역, 문장 다듬기는 **'치명적인 시스템 오류'**로 간주한다. 문장이 투박하고 어색하더라도 국문 원문의 구조와 단어를 **[지침]**에 근거해 기계적으로 1:1 치환(Compiling)하는 것이 유일한 목표다.

**[1. 작업 자동화 및 파일 인식 규칙]**

- **A_E 포함 파일 (예: OABASE0004_A_E):** 기준이 되는 **[영문 명세서]**. 모든 기술 용어 선택의 절대적 기준으로 삼습니다.
- **B_K 포함 파일 (예: OABASE0004_B_K):** 번역 대상인 **[국문 거절이유통지서]**. 작업을 시작하는 대상입니다.
- **최종 결과물 명명:** `OABASE[번호]_C_E.docx` 형식으로 워드 파일을 생성하여 제공합니다.

**[2. 헤더 유닛 및 서식 (전체 좌측 정렬)]**
모든 항목은 좌측 정렬하며, 항목명과 데이터 사이에는 **[Tab]**을 사용하여 시작 위치를 세로로 일정하게 정렬하십시오.

- **[English Translation]** (최상단)
- **NOTICE OF PRELIMINARY REJECTION** (중앙 정렬, 대문자 굵게)
- **Mailing Date:** `[Tab]` [B_K 발송일자: Month DD, YYYY 형식]
- **Response Due Date:** `[Tab]` [B_K 제출기일: Month DD, YYYY 형식]
- **Applicant:** `[Tab]` [B_K 출원인 명칭: 영문 대문자]
- **Attorney:** `[Tab]` **Hoon Chang** (고정값)
- **Application No.:** `[Tab]` [B_K 출원번호: 10-YYYY-XXXXXXX 형식]
- **Title of Invention:** `[Tab]` [**A_E 명세서의 발명 명칭**을 토씨 하나 틀리지 않게 그대로 가져와 영문 대문자 굵게 표기]

1. 고정 매핑 테이블 (Literal Mapping Table)
아래에 열거된 **국문 단락 제목은 의미 해석 없이 “문자열 매칭 → 고정 영문 치환” 방식으로만 처리한다.**

| 국문 입력 토큰 | 고정 출력 문자열 | 출력 형식 규칙 |
| --- | --- | --- |
| 심사결과 | EXAMINATION RESULTS | 대문자, Bold |
| 구체적인 거절이유 | DETAILED REASONS | 대문자, Bold |
| 인용발명 | Reference | Title Case, Bold |
| 보정서 제출시 참고사항 | Notes for Amendment | Title Case, Bold |
| [첨부] | Attachments: | Title Case, 콜론 포함, Bold |
| <<안내>> | (출력 없음) | 라인 전체 삭제 |
| - 아래 - | (출력 없음) | 라인 전체 삭제 |

**[3. 상단 고정 표준 문구 (Introductory Text)]**
헤더 바로 아래에 다음 두 문단을 토씨 하나 틀리지 않게 그대로 삽입하십시오.

1. "According to Article 63 of the Korean Patent Act (KPA), this is to notify the applicant of a preliminary rejection as a result of examination of the present application. The applicant may submit an Argument and/or Amendment by the above response due date."
2. "The due date can be extended, in principle, for up to four months. The applicant may apply for an extension for one month, or, if necessary, for two or more months at a time. When applying for a time extension in excess of four months based on unavoidable circumstances (see the Guidelines for Time Extensions given below), the applicant is required to submit a justification statement to the Examiner."

**[4. 본문 구조 및 이미지 처리 (Section Framework & Visuals)]**

- **EXAMINATION RESULTS (대문자 굵게):**
    - `Claims under Examination: Claims X to Y` 형식 유지.
    - `Rejected Parts and Relevant Provisions:` 아래에 번호, 거절항목, 관련법조항이 포함된 표(Table)를 생성할 것.
- **DETAILED REASONS (대문자 굵게):**
    - 국문 원본(B_K)의 번호 체계(`1.`, `①`, `[ ]`) 및 **굵은 글씨(Bold)** 위치를 완벽히 재현할 것.
- **이미지 삽입:** **국문 통지서(B_K)의 표 내부나 본문에 도면(이미지)이 있는 경우, 해당 도면을 캡처하듯 그대로 가져와 영문 번역본의 동일한 위치에 삽입하십시오.**

**[5. 기술 용어 및 법률 표준 문구 (Strict Mapping)]**

- **명세서 용어 100% 일치:** 모든 기술 용어(부품명, 가공 방식 등)는 반드시 A_E 명세서의 용어를 찾아 매칭하며, 임의 번역이나 동의어 치환을 절대 금지합니다.
- **인용 문헌 표기:** 인용 발명(Prior Art)은 국가명(German, Korean, US 등)과 공보의 종류를 포함한 **풀네임(Full Name)**을 기재하십시오. (예: German Patent Publication DE...)
- **표준 법률 표현:**
    - '통상의 기술자' → **A person having ordinary skill in the art**
    - '수행주체' → **"the subject (hardware) that performs"**, '선행 근거' → **"antecedent basis"**
    - 법조항: **Article [번호] of the KPA** 형식 고수.
- **참조 기호:** 도면 부호 및 단락 번호 인용 방식을 A_E와 동일하게 유지합니다.

**[6. <<안내>> 고정 표준 문구 ]**
<<안내>>라고 되어있는 경우 번역하지 말고 아래 하단 고정 문구로 그대로 대체한다.

`Guidelines for Time Extensions
According to the Guidelines for Time Extensions, the Examiner determines whether to approve a time extension and the length of the extension after determining if any of the following grounds apply:
(1) Where the applicant newly appoints an agent or changes or discharges all of the previous agents within one (1) month prior to the expiry of the designated term;
(2) Where the applicant submits a notice of change in the applicant within one (1) month prior to the expiry of the designated term; however, this may only be applied when a new applicant is added to an application.
(3) Where the applicant receives an examination result from a foreign Patent Office within two (2) months prior to the expiry of the designated term and intends to reflect the examination result in an amendment (in this case, when submitting a request for an extension, the applicant should also submit copies of the examination result and the relevant claims);
(4) Where the service of an Office Action was delayed for one or more months (eligible for an extra extension of one (1) month);
(5) Where the parent application or a divisional application is pending in an IPTAB trial or a litigation;
(6) Where more time is needed to conduct a test and measure the results thereof in connection with an Office Action; or
(7) Where circumstances for which the applicant is not responsible necessitate an extension of the deadline.
*However, where the examination of the application commenced according to a third party’s request, extensions under items (1) to (5) above will not be granted.

Partial Refund on Examination Fee
If the Applicant abandons or withdraws an application within the response period of a first Office Action, an amount equivalent to 1/3 of the official fees for requesting an examination shall be refunded at the Applicant’s request.`

**[7. 번역의 기본 원칙 (Literal Translation & Completeness)]**

- **직역(Literal Translation) 절대 원칙:** 번역은 문학적 윤색을 배제하고 단어 및 문장 구조를 1:1로 대응시키는 직역을 원칙으로 하며, 원문에 문법적 오류나 비문이 있더라도 이를 수정하지 않고 그대로 번역한다.
- **[절대 금지]:** 의역, 요약, 생략, 중략, 임의 추가는 전면 금지되며, 원문에 없는 내용이나 접속사(그래서, 하지만 등)를 추가해서도 안 된다.
- **용어 고정 매핑:** 명세서 전체에 걸쳐 동일한 국문 용어는 반드시 동일한 영문 용어로 고정 매핑하여 사용한다.

**[8. 번역 출력 원칙 (Batch Output)]**

**[출력 분할 규칙 – Hard Limit + Number-Aware Cut]**

- 출력은 **절대적으로 최대 2쪽 분량을 초과해서는 안 된다.** 내가 '다음'이라고 하면 그다음 분량을 번역해. 절대로 요약하지 말고 한 단어도 빠짐없이 직역해.
- 분할은 **번호 단락(1., 2., 3., (1), (2), (3) …)의 경계에서만 수행한다.**
- **2쪽 이내에서 번호 단락이 완결되는 지점이 존재하는 경우, 그 지점에서 분할한다.**
- **2쪽 이내에 번호 단락의 완결 지점이 존재하지 않는 경우, 해당 번호 단락은 다음 출력 분량으로 이월하고, 현재 분량은 그 직전 번호 단락까지 출력한다.**

**[종결 블록 처리]**

- [보정서 제출시 참고사항]이 원문에 존재하는 경우, 누락하지 말고 전체를 번역·출력한다.
원문에 [보정서 제출시 참고사항]이 존재하는 경우, 해당 블록이 출력되기 전에는 [첨부], 날짜/서명, <<안내>>, “End.”를 출력하지 않는다.
- **Attachments / Mailing Date / <<안내>>의 순서도 원문 배열을 1:1로 유지**
- 섹션 재분류, 재배치, 구조적 “정리”는 하지 않음

### **[표 인식 및 위치 적용 규칙 – Context-Aware Anchored Table Processing]**
(생략 없이 원문 그대로 적용한다.)

**[섹션 포함 및 문서 종료 규칙]**

- **[보정서 제출시 참고사항]은 본문에 포함되는 섹션이므로, 누락하지 말고 전체를 번역·출력한다.**
- 문서는 **[첨부] → 날짜 → 발행기관/심사관(서명 라인) → << 안내 >>** 순서까지 **모두 출력된 경우에만** 종료된 것으로 판단한다.
- 위 종결부 블록은 **순서를 변경하거나 분할하지 않는다.**
"""


# =========================
# Streamlit Config
# =========================
st.set_page_config(page_title="특허 OA 기계적 번역 엔진 (v2.1)", layout="wide")
st.title("⚖️ 특허 OA 기계적 번역 엔진 (v2.1) — ChatGPT API")

# =========================
# OpenAI Setup
# =========================
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY")
if not OPENAI_KEY:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .streamlit/secrets.toml에 추가하세요.")
    st.stop()

MODEL_NAME = st.secrets.get("MODEL_NAME", "gpt-4.1-mini")
client = OpenAI(api_key=OPENAI_KEY)


# =========================
# Helpers
# =========================
def read_docx(file) -> str:
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs]).strip()

def read_pdf(file) -> str:
    reader = PdfReader(file)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()

def normalize_newlines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def preclean_bk_by_fixed_rules(text: str) -> str:
    """
    지침의 고정 매핑 테이블 중 '라인 전체 삭제'를 앱에서 강제 적용:
    - '<<안내>>' 라인 삭제
    - '- 아래 -' 라인 삭제
    """
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.strip()
        if s == "<<안내>>":
            continue
        if s == "- 아래 -":
            continue
        out.append(line)
    return "\n".join(out)

def parse_basic_fields_from_bk(bk_text: str) -> dict:
    out = {"application_no": "", "mailing_date_raw": "", "response_due_date_raw": "", "applicant_raw": ""}

    m = re.search(r"출\s*원\s*번\s*호\s*([0-9]{2,}-[0-9]{4}-[0-9]{7,})", bk_text)
    if m:
        out["application_no"] = m.group(1).strip()

    m = re.search(r"발\s*송\s*일\s*자\s*:\s*([0-9]{4}\.[0-9]{2}\.[0-9]{2})", bk_text)
    if m:
        out["mailing_date_raw"] = m.group(1).strip()

    m = re.search(r"제\s*출\s*기\s*일\s*:\s*([0-9]{4}\.[0-9]{2}\.[0-9]{2})", bk_text)
    if m:
        out["response_due_date_raw"] = m.group(1).strip()

    m = re.search(r"출\s*원\s*인\s*성\s*명\s*([^\n]+)", bk_text)
    if m:
        out["applicant_raw"] = m.group(1).strip()

    return out

def ymd_to_english_month_dd_yyyy(ymd_dot: str) -> str:
    try:
        dt = datetime.strptime(ymd_dot, "%Y.%m.%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        return ymd_dot

def extract_title_from_ae(ae_text: str) -> str:
    lines = [l.strip() for l in ae_text.split("\n") if l.strip()]
    for l in lines[:120]:
        if "Method of" in l and 10 <= len(l) <= 240:
            return l.strip()
    joined = "\n".join(lines[:250])
    m = re.search(r"(?:Title\s*[:\-]\s*)(.+)", joined, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if 5 <= len(cand) <= 240:
            return cand
    return ""

def split_into_numbered_blocks(bk_text: str) -> list[str]:
    text = normalize_newlines(bk_text)

    # 번호 단락 경계: 1., (1), ① 등
    pat = re.compile(
        r"(?m)^(?:\s*(\d+\.)\s+|\s*(\(\d+\))\s+|\s*([①②③④⑤⑥⑦⑧⑨⑩])\s+|\s*(\[첨\s*부\])\s*$|\s*(-\s*보정서\s*제출시\s*참고사항\s*-)\s*$)"
    )

    idxs = [m.start() for m in pat.finditer(text)]
    if not idxs:
        return [text]

    idxs.append(len(text))
    blocks = []
    for i in range(len(idxs) - 1):
        chunk = text[idxs[i]:idxs[i + 1]].strip()
        if chunk:
            blocks.append(chunk)
    return blocks

def add_text_to_doc(doc: Document, text: str):
    for line in text.split("\n"):
        doc.add_paragraph(line)


# =========================
# UI: Upload
# =========================
st.sidebar.header("Settings")
st.sidebar.caption("A_E / B_K 파일명을 기준으로 자동 인식합니다.")
st.sidebar.caption(f"Model: {MODEL_NAME}")

uploaded_files = st.file_uploader(
    "파일 업로드 (A_E: DOCX 권장 / B_K: PDF 또는 DOCX)",
    type=["docx", "pdf"],
    accept_multiple_files=True
)

ae_text = ""
bk_text = ""
file_prefix = "OABASE"

if uploaded_files:
    for f in uploaded_files:
        if f.name.lower().endswith(".docx"):
            text = read_docx(f)
        else:
            text = read_pdf(f)

        if "A_E" in f.name:
            ae_text = normalize_newlines(text)
            st.info(f"✅ 영문 명세서(A_E) 인식: {f.name}")
            if "_" in f.name:
                file_prefix = f.name.split("_")[0]
        elif "B_K" in f.name:
            bk_text = normalize_newlines(text)
            bk_text = preclean_bk_by_fixed_rules(bk_text)  # <<안내>> / - 아래 - 라인 삭제 강제
            st.info(f"✅ 국문 통지서(B_K) 인식: {f.name}")
            if "_" in f.name:
                file_prefix = f.name.split("_")[0]

if not uploaded_files:
    st.stop()

if not ae_text or not bk_text:
    st.warning("A_E 파일과 B_K 파일이 모두 필요합니다.")
    st.stop()


# =========================
# Header fields
# =========================
fields = parse_basic_fields_from_bk(bk_text)
ae_title = extract_title_from_ae(ae_text)

st.subheader("헤더 필드 (자동 추출 → 필요 시 수정)")
c1, c2, c3, c4 = st.columns(4)

with c1:
    app_no = st.text_input("Application No.", value=fields["application_no"])
with c2:
    mailing_date_raw = st.text_input("Mailing Date (원문)", value=fields["mailing_date_raw"])
with c3:
    due_date_raw = st.text_input("Response Due Date (원문)", value=fields["response_due_date_raw"])
with c4:
    applicant = st.text_input("Applicant (영문 대문자)", value=(fields["applicant_raw"] or "").upper())

mailing_date_en = ymd_to_english_month_dd_yyyy(mailing_date_raw) if mailing_date_raw else ""
due_date_en = ymd_to_english_month_dd_yyyy(due_date_raw) if due_date_raw else ""

title_of_invention = st.text_input("Title of Invention (A_E 기준)", value=(ae_title or "").upper())

st.divider()


# =========================
# Split & Session State
# =========================
blocks = split_into_numbered_blocks(bk_text)

if "idx" not in st.session_state:
    st.session_state.idx = 0
if "accum" not in st.session_state:
    st.session_state.accum = ""

st.subheader("번호 단락 단위 번역 (Part → Next)")
st.caption("앱이 B_K를 번호 단락 경계로 나눠서, Part 단위로 번역을 호출합니다. (누락/초과 출력 리스크 감소)")

left, right = st.columns(2)

with left:
    st.markdown("### 현재 B_K 블록(원문)")
    st.text_area("원문", value=blocks[st.session_state.idx], height=320)

with right:
    st.markdown("### 누적 번역 결과")
    st.text_area("번역", value=st.session_state.accum, height=320)


def build_prompt(block_text: str) -> str:
    header_hint = f"""
[HEADER DATA]
Mailing Date: {mailing_date_en}
Response Due Date: {due_date_en}
Applicant: {applicant}
Attorney: Hoon Chang
Application No.: {app_no}
Title of Invention: {title_of_invention}
"""
    return f"""
[A_E SPECIFICATION]
{ae_text}

[B_K BLOCK TO TRANSLATE]
{block_text}

{header_hint}
"""


b1, b2, b3 = st.columns([1, 1, 2])
with b1:
    do_translate = st.button("Part 번역", type="primary")
with b2:
    do_next = st.button("Next")
with b3:
    do_reset = st.button("초기화(누적/인덱스 리셋)")

if do_reset:
    st.session_state.idx = 0
    st.session_state.accum = ""
    st.rerun()

if do_translate:
    block = blocks[st.session_state.idx]

    with st.spinner("ChatGPT 번역 중..."):
        prompt = build_prompt(block)

        resp = client.responses.create(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": MY_INSTRUCTION},
                {"role": "user", "content": prompt},
                {"role": "user", "content": "위 지침에 따라, 이 블록만 누락 없이 직역 번역하여 출력하라. 요약/생략/의역 금지."}
            ],
        )
        out = (resp.output_text or "").strip()

    if st.session_state.accum:
        st.session_state.accum += "\n\n" + out
    else:
        st.session_state.accum = out

    st.rerun()

if do_next:
    if st.session_state.idx < len(blocks) - 1:
        st.session_state.idx += 1
        st.rerun()
    else:
        st.info("마지막 블록입니다. 아래에서 DOCX로 내보내세요.")


# =========================
# DOCX Export
# =========================
st.divider()
st.subheader("DOCX 생성/다운로드")

if st.button("DOCX 생성 / 다운로드"):
    if not st.session_state.accum.strip():
        st.warning("번역 결과가 없습니다.")
        st.stop()

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    add_text_to_doc(doc, st.session_state.accum)

    buf = io.BytesIO()
    doc.save(buf)

    st.download_button(
        label="📥 DOCX 다운로드",
        data=buf.getvalue(),
        file_name=f"{file_prefix}_C_E.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
