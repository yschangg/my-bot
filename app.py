import streamlit as st
from google import genai

# Secrets 금고에서 열쇠(API 키) 가져오기
api_key = st.secrets["API_KEY"]
client = genai.Client(api_key=api_key)

st.title("AI Translation Assistant")

# 파일 업로드 버튼!
uploaded_file = st.file_uploader("Upload document", type=['txt', 'pdf'])

if uploaded_file:
    st.info("File uploaded successfully!")

# 채팅창
if prompt := st.chat_input("Enter message"):
    st.chat_message("user").markdown(prompt)
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )
    st.chat_message("assistant").markdown(response.text)
