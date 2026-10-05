import streamlit as st
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import os
from googletrans import Translator
import tempfile

st.set_page_config(page_title="AP News 영어 학습", page_icon="📰", layout="wide")

# 제목
st.title("📰 AP News 영어 학습 앱")
st.markdown("---")

# AP News 기사 크롤링 함수
@st.cache_data(ttl=3600)  # 1시간 캐시
def fetch_ap_news():
    try:
        url = "https://apnews.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # AP News 제목 추출 (클래스명은 변경될 수 있음)
        headlines = []
        
        # 다양한 선택자 시도
        selectors = [
            'h2.PagePromo-title',
            'h3.PagePromo-title',
            'span.PagePromoContentIcons-text',
            'div.CardHeadline',
            'h2',
            'h3'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 20 and text not in headlines:
                    headlines.append(text)
                if len(headlines) >= 10:
                    break
            if len(headlines) >= 10:
                break
        
        return headlines[:10] if headlines else ["기사를 가져올 수 없습니다."]
    
    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
        return [f"Error: {str(e)}"]

# 번역 함수
def translate_to_korean(text):
    try:
        translator = Translator()
        result = translator.translate(text, src='en', dest='ko')
        return result.text
    except Exception as e:
        return f"번역 오류: {str(e)}"

# TTS 함수
def text_to_speech(text, index):
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        
        # 임시 파일 생성
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        
        return temp_file.name
    except Exception as e:
        st.error(f"TTS 오류: {str(e)}")
        return None

# 새로고침 버튼
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

st.markdown("### 📌 주요 기사 헤드라인")

# 기사 가져오기
with st.spinner("AP News에서 기사를 가져오는 중..."):
    headlines = fetch_ap_news()

# 각 헤드라인을 상자로 출력
for idx, headline in enumerate(headlines, 1):
    with st.container():
        st.markdown(f"""
        <div style="
            border: 2px solid #4CAF50;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background-color: #f9f9f9;
        ">
            <h4 style="color: #333; margin-bottom: 10px;">📄 기사 {idx}</h4>
            <p style="font-size: 16px; line-height: 1.6; color: #555;">
                {headline}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
        # TTS 버튼
        with col1:
            if st.button(f"🔊 읽기", key=f"tts_{idx}"):
                with st.spinner("음성 생성 중..."):
                    audio_file = text_to_speech(headline, idx)
                    if audio_file:
                        audio_bytes = open(audio_file, 'rb').read()
                        st.audio(audio_bytes, format='audio/mp3')
                        os.unlink(audio_file)  # 임시 파일 삭제
        
        # 번역 버튼
        with col2:
            if st.button(f"🇰🇷 번역", key=f"trans_{idx}"):
                with st.spinner("번역 중..."):
                    translation = translate_to_korean(headline)
                    st.info(f"**한글 번역:** {translation}")
        
        st.markdown("---")

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 앱 정보")
    st.markdown("""
    ### 사용 방법
    1. **새로고침** 버튼으로 최신 기사 로드
    2. **🔊 읽기** 버튼으로 영어 발음 듣기
    3. **🇰🇷 번역** 버튼으로 한글 번역 보기
    
    ### 기능
    - AP News 실시간 헤드라인
    - 영어 TTS (Text-to-Speech)
    - 한글 번역
    
    ### 필요 라이브러리
    ```
    streamlit
    requests
    beautifulsoup4
    gtts
    googletrans==4.0.0-rc1
    ```
    """)
    
    st.markdown("---")
    st.caption("© 2025 ChatHK - 영어 학습 앱")