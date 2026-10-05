import streamlit as st
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import os
from googletrans import Translator
import tempfile
import re
from nltk.corpus import wordnet
import nltk
import pandas as pd

# eng_to_ipa 라이브러리
try:
    import eng_to_ipa as ipa
except:
    ipa = None

# NLTK 데이터 다운로드
try:
    nltk.data.find('corpora/wordnet.zip')
except LookupError:
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)

st.set_page_config(page_title="AP News", page_icon="📰", layout="wide")

# 세션 상태 초기화
if 'headlines' not in st.session_state:
    st.session_state.headlines = []
if 'show_translation' not in st.session_state:
    st.session_state.show_translation = {}
if 'show_analysis' not in st.session_state:
    st.session_state.show_analysis = {}
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = {}

# 제목
st.title("📰 AP News")
st.markdown("---")

# AP News 기사 크롤링 함수 (캐싱)
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ap_news():
    try:
        url = "https://apnews.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        headlines = []
        
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
        return [f"Error: {str(e)}"]

# 번역 함수 (캐싱)
@st.cache_data(show_spinner=False)
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
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        st.error(f"TTS 오류: {str(e)}")
        return None

# 발음기호 가져오기 (캐싱)
@st.cache_data(show_spinner=False)
def get_pronunciation(word):
    try:
        if ipa:
            pronunciation = ipa.convert(word.lower())
            if pronunciation and pronunciation != word.lower():
                return f"/{pronunciation}/"
        return f"/{word.lower()}/"
    except:
        return f"/{word.lower()}/"

# 품사를 한글로 변환
def pos_to_korean(pos):
    pos_dict = {
        'n': '명사',
        'v': '동사',
        'a': '형용사',
        's': '형용사',
        'r': '부사',
        'j': '형용사'
    }
    return pos_dict.get(pos, '기타')

# 단어 뜻 및 품사 가져오기 (캐싱)
@st.cache_data(show_spinner=False)
def get_word_info(word):
    try:
        synsets = wordnet.synsets(word)
        if synsets:
            synset = synsets[0]
            definition = synset.definition()
            pos = synset.pos()
            
            translator = Translator()
            meaning_kr = translator.translate(definition, src='en', dest='ko').text
            pos_kr = pos_to_korean(pos)
            
            return meaning_kr, pos_kr
        else:
            translator = Translator()
            meaning_kr = translator.translate(word, src='en', dest='ko').text
            return meaning_kr, '-'
    except Exception as e:
        return "조회 실패", '-'

# 문장에서 단어 추출 및 분석 (캐싱)
@st.cache_data(show_spinner=False)
def analyze_words(sentence):
    words = re.findall(r'\b[a-zA-Z]+\b', sentence.lower())
    unique_words = sorted(set(words))
    
    word_info = []
    for word in unique_words:
        if len(word) > 2:
            pronunciation = get_pronunciation(word)
            meaning, pos = get_word_info(word)
            word_info.append({
                '단어': word.capitalize(),
                '발음기호 (IPA)': pronunciation,
                '품사': pos,
                '뜻': meaning
            })
    
    return word_info

# 새로고침 버튼
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.session_state.headlines = []
        st.session_state.show_translation = {}
        st.session_state.show_analysis = {}
        st.session_state.analyzed_data = {}
        st.rerun()

st.markdown("### 📌 주요 기사 헤드라인")

# 기사 가져오기 (최초 1회만)
if not st.session_state.headlines:
    with st.spinner("AP News에서 기사를 가져오는 중..."):
        st.session_state.headlines = fetch_ap_news()

headlines = st.session_state.headlines

# 각 헤드라인을 상자로 출력
for idx, headline in enumerate(headlines, 1):
    with st.container():
        # 상자 디자인
        st.markdown(f"""
        <div style="
            border: 2px solid #4CAF50;
            border-radius: 10px;
            padding: 25px;
            margin: 15px 0;
            background-color: #f9f9f9;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <h4 style="color: #2c3e50; margin-bottom: 15px; font-size: 18px;">📄 기사 {idx}</h4>
            <p style="
                font-size: 22px;
                line-height: 1.8;
                color: #2c3e50;
                font-weight: 500;
                letter-spacing: 0.5px;
            ">
                {headline}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        # TTS 버튼
        with col1:
            if st.button(f"🔊 읽기", key=f"tts_{idx}"):
                with st.spinner("음성 생성 중..."):
                    audio_file = text_to_speech(headline, idx)
                    if audio_file:
                        audio_bytes = open(audio_file, 'rb').read()
                        st.audio(audio_bytes, format='audio/mp3')
                        os.unlink(audio_file)
        
        # 번역 버튼
        with col2:
            if st.button(f"🇰🇷 번역", key=f"trans_btn_{idx}"):
                st.session_state.show_translation[idx] = not st.session_state.show_translation.get(idx, False)
        
        # 단어 분석 버튼
        with col3:
            if st.button(f"📚 단어 분석", key=f"analyze_btn_{idx}"):
                st.session_state.show_analysis[idx] = not st.session_state.show_analysis.get(idx, False)
                
                # 분석 데이터가 없으면 생성
                if idx not in st.session_state.analyzed_data:
                    with st.spinner("단어 분석 중..."):
                        st.session_state.analyzed_data[idx] = analyze_words(headline)
        
        # 번역 표시
        if st.session_state.show_translation.get(idx, False):
            translation = translate_to_korean(headline)
            st.info(f"**한글 번역:** {translation}")
        
        # 단어 분석 표시
        if st.session_state.show_analysis.get(idx, False):
            if idx in st.session_state.analyzed_data:
                word_info = st.session_state.analyzed_data[idx]
                
                if word_info:
                    st.markdown("---")
                    st.markdown("#### 📖 단어별 발음 및 뜻")
                    
                    # DataFrame 생성
                    df = pd.DataFrame(word_info)
                    
                    # Streamlit 데이터프레임 표시
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "단어": st.column_config.TextColumn(
                                "단어",
                                width="small"
                            ),
                            "발음기호 (IPA)": st.column_config.TextColumn(
                                "발음기호 (IPA)",
                                width="medium"
                            ),
                            "품사": st.column_config.TextColumn(
                                "품사",
                                width="small"
                            ),
                            "뜻": st.column_config.TextColumn(
                                "뜻",
                                width="large"
                            )
                        }
                    )
                    
                    # 상세 정보 패널
                    with st.expander("🔍 상세 단어 정보 보기"):
                        for info in word_info:
                            col_a, col_b, col_c, col_d = st.columns([2, 3, 1, 4])
                            with col_a:
                                st.markdown(f"**{info['단어']}**")
                            with col_b:
                                st.markdown(f":red[{info['발음기호 (IPA)']}]")
                            with col_c:
                                st.markdown(f":blue[**[{info['품사']}]**]")
                            with col_d:
                                st.markdown(f"*{info['뜻']}*")
                            st.markdown("---")
                else:
                    st.warning("분석할 단어가 없습니다.")
        
        st.markdown("---")

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 앱 정보")
    st.markdown("""
    ### 사용 방법
    1. **🔄 새로고침** 최신 기사 로드
    2. **🔊 읽기** 영어 발음 듣기
    3. **🇰🇷 번역** 한글 번역 토글
    4. **📚 단어 분석** 단어 정보 토글
    
    ### 주요 특징
    - ⚡ **빠른 처리**: 캐싱으로 속도 최적화
    - 🎯 **개별 작동**: 클릭한 버튼만 반응
    - 💾 **메모리 효율**: 한 번 분석한 데이터 재사용
    - 🔄 **토글 방식**: 버튼 클릭으로 켜고 끄기
    
    ### 기능
    - AP News 실시간 헤드라인
    - 영어 TTS (Text-to-Speech)
    - 한글 번역 (토글)
    - 단어별 IPA 발음기호
    - 단어별 품사 표시
    - 단어별 한글 뜻
    - 확장 가능한 상세 정보
    
    ### 품사 안내
    - **명사**: 사람, 사물, 장소 등
    - **동사**: 동작이나 상태
    - **형용사**: 명사를 수식
    - **부사**: 동사, 형용사 수식
    
    ### 발음기호 안내 (IPA)
    - `/ə/` : schwa (약한 모음)
    - `/θ/` : thin (무성 th)
    - `/ð/` : this (유성 th)
    - `/ʃ/` : she (sh 소리)
    - `/ʒ/` : measure (zh 소리)
    
    ### 필요 라이브러리
    ```bash
    pip install streamlit requests 
    beautifulsoup4 gtts 
    googletrans==4.0.0-rc1 
    nltk eng-to-ipa pandas
    ```
    """)
    
    st.markdown("---")
    
    # 성능 정보
    st.markdown("### 📊 성능 정보")
    st.metric("캐시된 데이터", f"{len(st.session_state.analyzed_data)}개")
    st.metric("로드된 기사", f"{len(headlines)}개")
    
    st.markdown("---")
    st.caption("© 2025 ChatHK - 영어 학습 앱")

st.sidebar.markdown("---")
st.sidebar.success("💡 캐싱으로 빠른 응답 제공!")