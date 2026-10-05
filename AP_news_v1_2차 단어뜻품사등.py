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
    nltk.download('wordnet')
    nltk.download('omw-1.4')

st.set_page_config(page_title="AP News 영어 학습", page_icon="📰", layout="wide")

# 제목
st.title("📰 AP News 영어 학습 앱")
st.markdown("---")

# AP News 기사 크롤링 함수
@st.cache_data(ttl=3600)
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
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        st.error(f"TTS 오류: {str(e)}")
        return None

# 발음기호 가져오기 (IPA)
def get_pronunciation(word):
    try:
        if ipa:
            pronunciation = ipa.convert(word.lower())
            # IPA 형식으로 반환 (슬래시로 감싸기)
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

# 단어 뜻 및 품사 가져오기 (WordNet 사용)
def get_word_info(word):
    try:
        synsets = wordnet.synsets(word)
        if synsets:
            # 가장 일반적인 의미 (첫 번째)
            synset = synsets[0]
            definition = synset.definition()
            pos = synset.pos()
            
            # 한글 번역
            translator = Translator()
            meaning_kr = translator.translate(definition, src='en', dest='ko').text
            pos_kr = pos_to_korean(pos)
            
            return meaning_kr, pos_kr
        else:
            # WordNet에 없으면 직접 번역 시도
            translator = Translator()
            meaning_kr = translator.translate(word, src='en', dest='ko').text
            return meaning_kr, '-'
    except Exception as e:
        return "조회 실패", '-'

# 문장에서 단어 추출 및 분석
def analyze_words(sentence):
    # 특수문자 제거 및 소문자 변환
    words = re.findall(r'\b[a-zA-Z]+\b', sentence.lower())
    # 중복 제거 및 정렬
    unique_words = sorted(set(words))
    
    word_info = []
    for word in unique_words:
        if len(word) > 2:  # 2글자 이하 단어는 제외
            pronunciation = get_pronunciation(word)
            meaning, pos = get_word_info(word)
            word_info.append({
                'word': word.capitalize(),
                'pronunciation': pronunciation,
                'pos': pos,
                'meaning': meaning
            })
    
    return word_info

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
        # 상자 디자인 (글씨 크기 증가)
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
        
        col1, col2, col3 = st.columns([1, 1, 4])
        
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
            if st.button(f"🇰🇷 번역", key=f"trans_{idx}"):
                with st.spinner("번역 중..."):
                    translation = translate_to_korean(headline)
                    st.info(f"**한글 번역:** {translation}")
        
        # 단어 분석은 자동으로 표시
        st.markdown("---")
        st.markdown("#### 📖 단어별 발음 및 뜻")
        
        with st.spinner("단어 분석 중..."):
            word_info = analyze_words(headline)
            
            if word_info:
                # DataFrame 생성
                df_data = []
                for info in word_info:
                    df_data.append({
                        '단어': info['word'],
                        '발음기호 (IPA)': info['pronunciation'],
                        '품사': info['pos'],
                        '뜻': info['meaning']
                    })
                
                df = pd.DataFrame(df_data)
                
                # Streamlit 데이터프레임 표시 (스타일 적용)
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "단어": st.column_config.TextColumn(
                            "단어",
                            width="small",
                            help="영어 단어"
                        ),
                        "발음기호 (IPA)": st.column_config.TextColumn(
                            "발음기호 (IPA)",
                            width="medium",
                            help="국제 음성 기호"
                        ),
                        "품사": st.column_config.TextColumn(
                            "품사",
                            width="small",
                            help="단어의 품사"
                        ),
                        "뜻": st.column_config.TextColumn(
                            "뜻",
                            width="large",
                            help="한글 의미"
                        )
                    }
                )
                
                # 추가: 확장 가능한 상세 정보
                with st.expander("🔍 상세 단어 정보 보기"):
                    for info in word_info:
                        col_a, col_b, col_c, col_d = st.columns([2, 3, 1, 4])
                        with col_a:
                            st.markdown(f"**{info['word']}**")
                        with col_b:
                            st.markdown(f"<span style='color: #e74c3c; font-family: Times New Roman; font-size: 16px;'>{info['pronunciation']}</span>", unsafe_allow_html=True)
                        with col_c:
                            st.markdown(f"<span style='color: #3498db; font-weight: bold;'>[{info['pos']}]</span>", unsafe_allow_html=True)
                        with col_d:
                            st.markdown(f"*{info['meaning']}*")
                        st.markdown("---")
            else:
                st.warning("분석할 단어가 없습니다.")
        
        st.markdown("---")

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 앱 정보")
    st.markdown("""
    ### 사용 방법
    1. **새로고침** 버튼으로 최신 기사 로드
    2. **🔊 읽기** 버튼으로 영어 발음 듣기
    3. **🇰🇷 번역** 버튼으로 한글 번역 보기
    4. 각 기사 아래 **단어 분석** 자동 표시
    
    ### 기능
    - AP News 실시간 헤드라인
    - 영어 TTS (Text-to-Speech)
    - 한글 번역
    - 단어별 IPA 발음기호
    - 단어별 품사 표시
    - 단어별 한글 뜻
    - 확장 가능한 상세 정보
    
    ### 품사 안내
    - **명사**: 사람, 사물, 장소 등의 이름
    - **동사**: 동작이나 상태를 나타냄
    - **형용사**: 명사를 수식
    - **부사**: 동사, 형용사 등을 수식
    
    ### 발음기호 안내
    IPA (International Phonetic Alphabet)
    - `/ə/` : 약한 모음 (schwa)
    - `/θ/` : 'th' 무성음 (thin)
    - `/ð/` : 'th' 유성음 (this)
    - `/ʃ/` : 'sh' 소리 (she)
    - `/ʒ/` : 'zh' 소리 (measure)
    
    ### 필요 라이브러리
    ```
    streamlit
    requests
    beautifulsoup4
    gtts
    googletrans==4.0.0-rc1
    nltk
    eng-to-ipa
    pandas
    ```
    
    ### 설치 명령어
    ```bash
    pip install streamlit requests beautifulsoup4 
    gtts googletrans==4.0.0-rc1 nltk 
    eng-to-ipa pandas
    ```
    """)
    
    st.markdown("---")
    st.caption("© 2025 ChatHK - 영어 학습 앱")

# 초기 설정 안내
st.sidebar.markdown("---")
st.sidebar.info("💡 첫 실행 시 NLTK 데이터가 자동으로 다운로드됩니다.")