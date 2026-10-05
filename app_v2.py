# -*- coding: utf-8 -*-
"""
AP News English Learning Web App - v2 (Flask)
추가 내역 (app_v1.py -> app_v2.py):
  1. SUMMARY_CACHE 및 get_article_summary 추가
  2. /api/summary 라우트 추가
  3. tts 길이 제한 500 -> 2000으로 증가
"""

import sys
import io
import re
import os
import time
import logging
import threading
from collections import OrderedDict
from urllib.parse import urlparse, quote

# Windows console encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Python 3.13+ NumPy/SciPy compatibility patch for NLTK
try:
    import numpy as np
    if not hasattr(np, 'long'):
        np.long = int
    if not hasattr(np, 'ulong'):
        np.ulong = int
except ImportError:
    pass

from flask import Flask, render_template, request, jsonify, send_file

import requests
from bs4 import BeautifulSoup
from gtts import gTTS

try:
    from googletrans import Translator
    HAS_GOOGLETRANS = True
except Exception as e:
    Translator = None
    HAS_GOOGLETRANS = False

# Optional Libraries with graceful fallback
try:
    from curl_cffi import requests as c_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as c_requests
    HAS_CURL_CFFI = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import eng_to_ipa as ipa
except ImportError:
    ipa = None

try:
    import nltk
    from nltk.corpus import wordnet
    try:
        nltk.data.find('corpora/wordnet.zip')
    except LookupError:
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
    HAS_WORDNET = True
except Exception as e:
    HAS_WORDNET = False
    logging.warning(f"NLTK WordNet not available: {e}")

# ===================== Logging Setup =====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ===================== Flask App =====================

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# CORS 지원 (flask-cors 설치 시 자동 활성화)
try:
    from flask_cors import CORS
    CORS(app)
    logger.info("CORS enabled via flask-cors")
except ImportError:
    pass

# ===================== Thread-safe Translator =====================

_translator_lock = threading.Lock()
_translator = Translator() if (HAS_GOOGLETRANS and Translator) else None


def _get_translator():
    """
    googletrans Translator 인스턴스를 반환하되,
    내부 httpx 세션 만료 시 재생성한다.
    """
    global _translator
    return _translator


def _reset_translator():
    """Translator 세션 만료/오류 시 인스턴스를 재생성한다."""
    global _translator
    if HAS_GOOGLETRANS and Translator:
        try:
            _translator = Translator()
            logger.info("Translator instance reset due to session expiry or error")
        except Exception:
            _translator = None


# ===================== LRU-style Bounded Cache =====================

class BoundedCache(OrderedDict):
    """
    OrderedDict 기반의 크기 제한 캐시.
    maxsize 초과 시 가장 오래된 항목을 자동 제거한다.
    """

    def __init__(self, maxsize=1000):
        super().__init__()
        self._maxsize = maxsize

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        while len(self) > self._maxsize:
            self.popitem(last=False)


# ===================== Caches =====================

# 카테고리별 뉴스 캐시 {cache_key: {data, source, timestamp}}
NEWS_CACHE = {}
CACHE_TTL = 900  # 15 minutes

TRANSLATION_CACHE = BoundedCache(maxsize=5000)
WORD_ANALYSIS_CACHE = BoundedCache(maxsize=500)
SUMMARY_CACHE = BoundedCache(maxsize=500)

# ===================== Constants =====================

CATEGORY_URLS = {
    'top': 'https://apnews.com/',
    'world': 'https://apnews.com/world-news',
    'us': 'https://apnews.com/us-news',
    'business': 'https://apnews.com/business',
    'technology': 'https://apnews.com/technology',
    'sports': 'https://apnews.com/sports',
    'entertainment': 'https://apnews.com/entertainment'
}

POS_DICT = {
    'n': '명사',
    'v': '동사',
    'a': '형용사',
    's': '형용사',
    'r': '부사',
    'j': '형용사'
}

COMMON_STOPWORDS = frozenset({
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
    'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
    'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
    'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
    'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
    'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
    'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
    'has', 'had', 'was', 'were', 'are', 'been', 'did', 'does',
    'how', 'new', 'old', 'big', 'own', 'too', 'any', 'may', 'way',
    'after', 'before', 'more', 'most', 'very', 'much', 'many'
})

# HTTP 헤더 (공통)
_DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# ===================== Core Functions =====================


def check_url_health(url):
    """
    AP News URL의 접근 가능 여부를 확인하고 헬스 정보를 반환한다.
    """
    start_time = time.time()
    result = {
        'url': url,
        'status_code': 0,
        'latency_ms': 0,
        'status': 'error',
        'method': '',
        'message': '',
        'headlines_found': 0
    }

    # URL 형식 검증
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        result['message'] = "잘못된 URL 형식입니다. (예: https://apnews.com/)"
        return result

    try:
        if HAS_CURL_CFFI:
            res = c_requests.get(
                url, headers=_DEFAULT_HEADERS,
                impersonate='chrome120', timeout=12
            )
            result['method'] = 'curl_cffi (Chrome Impersonation)'
        else:
            res = c_requests.get(url, headers=_DEFAULT_HEADERS, timeout=10)
            result['method'] = 'Standard requests'

        result['status_code'] = res.status_code
        result['latency_ms'] = int((time.time() - start_time) * 1000)

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            selectors = '.PagePromo, div[data-key="feed-card"], .CardHeadline, h2, h3'
            count = sum(
                1 for el in soup.select(selectors)
                if len(el.get_text(strip=True)) > 25
            )
            result['headlines_found'] = count
            result['status'] = 'success'
            result['message'] = f"정상 연결 성공! ({count}개 기사 탐지됨)"
        elif res.status_code == 403:
            result['status'] = 'warning'
            result['message'] = (
                "403 Forbidden (Cloudflare 방어 활성화됨 "
                "- RSS 대체 모드로 자동 연결됩니다)"
            )
        else:
            result['status'] = 'warning'
            result['message'] = f"상태 코드: {res.status_code}"

    except Exception as e:
        result['latency_ms'] = int((time.time() - start_time) * 1000)
        result['status'] = 'error'
        result['message'] = f"연결 실패: {str(e)}"

    return result


def fetch_ap_news_direct(target_url):
    """
    curl_cffi Chrome Impersonation으로 AP News 웹페이지를 직접 크롤링한다.
    """
    if not HAS_CURL_CFFI:
        raise RuntimeError("curl_cffi is required for direct AP News scraping")

    res = c_requests.get(
        target_url, headers=_DEFAULT_HEADERS,
        impersonate='chrome120', timeout=15
    )
    if res.status_code != 200:
        raise RuntimeError(f"HTTP Status {res.status_code}")

    soup = BeautifulSoup(res.text, 'html.parser')
    page_promos = soup.select('.PagePromo, div[data-key="feed-card"], .CardHeadline')

    items = []
    seen_titles = set()

    for p in page_promos:
        title_el = p.select_one('.PagePromo-title, h2, h3, .CardHeadline')
        link_el = p.select_one('a[href]')
        desc_el = p.select_one('.PagePromo-description, p')

        title = title_el.get_text(strip=True) if title_el else ''
        link = link_el['href'] if (link_el and link_el.has_attr('href')) else ''
        desc = desc_el.get_text(strip=True) if desc_el else ''

        if not title or len(title) <= 20 or title in seen_titles:
            continue

        # 비영어(스페인어 등) 기사 제외
        ascii_ratio = sum(1 for c in title if ord(c) < 128) / len(title)
        if ascii_ratio < 0.7:
            continue

        # 링크 정규화: 절대 경로 보장, 중복 슬래시 방지
        if link.startswith('http'):
            full_link = link
        elif link.startswith('/'):
            full_link = 'https://apnews.com' + link
        elif link:
            full_link = 'https://apnews.com/' + link
        else:
            full_link = ''

        seen_titles.add(title)
        items.append({
            'id': len(items) + 1,
            'title': title,
            'link': full_link,
            'description': desc,
            'source': 'AP News Direct'
        })
        if len(items) >= 20:
            break

    return items


def fetch_ap_news_rss(category='top'):
    """
    Google News RSS를 통해 AP News 기사를 수집한다 (Fallback).
    """
    if not HAS_FEEDPARSER:
        return []

    cat_query_map = {
        'top': 'site:apnews.com',
        'world': 'site:apnews.com world',
        'us': 'site:apnews.com US',
        'business': 'site:apnews.com business',
        'technology': 'site:apnews.com technology',
        'sports': 'site:apnews.com sports',
        'entertainment': 'site:apnews.com entertainment'
    }
    query = cat_query_map.get(category, 'site:apnews.com')
    # URL-safe 쿼리 인코딩
    rss_url = (
        f"https://news.google.com/rss/search"
        f"?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    )

    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        logger.warning(f"RSS parsing failed: {e}")
        return []

    items = []
    seen_titles = set()

    for entry in feed.entries:
        title = entry.title
        # 소스 접미사 제거
        if title.endswith(' - AP News'):
            title = title[:-10].strip()
        elif ' - ' in title:
            title = title.rsplit(' - ', 1)[0].strip()

        if title and len(title) > 20 and title not in seen_titles:
            seen_titles.add(title)
            items.append({
                'id': len(items) + 1,
                'title': title,
                'link': entry.link,
                'description': getattr(entry, 'summary', ''),
                'published': getattr(entry, 'published', ''),
                'source': 'AP News RSS Feed'
            })
            if len(items) >= 20:
                break

    return items


# 오프라인 폴백용 샘플 데이터
_SAMPLE_ARTICLES = [
    {
        'id': 1,
        'title': 'World leaders gather for annual summit to address climate change and economic growth',
        'link': 'https://apnews.com',
        'description': 'Discussions centered on global emissions targets and resilient renewable infrastructure.',
        'source': 'Demo Sample'
    },
    {
        'id': 2,
        'title': 'Tech giants announce new ethical framework for artificial intelligence safety and governance',
        'link': 'https://apnews.com',
        'description': 'Industry consortium establishes protocols to assess risk in frontier reasoning models.',
        'source': 'Demo Sample'
    },
    {
        'id': 3,
        'title': 'New space telescope reveals breathtaking observations of early galactic formations',
        'link': 'https://apnews.com',
        'description': 'Astronomers celebrate breakthrough imagery depicting cosmic dawn and ancient star clusters.',
        'source': 'Demo Sample'
    }
]


def get_ap_news(category='top', custom_url=None, force_refresh=False):
    """
    캐시와 폴백을 포함한 뉴스 수집 통합 로직.
    카테고리별로 캐시를 분리하여 전환 시 불필요한 재수집을 방지한다.
    """
    now = time.time()

    target_url = custom_url.strip() if custom_url else CATEGORY_URLS.get(category, CATEGORY_URLS['top'])
    cache_key = target_url

    # 캐시 확인
    if not force_refresh and cache_key in NEWS_CACHE:
        cached = NEWS_CACHE[cache_key]
        if cached['data'] and (now - cached['timestamp']) < CACHE_TTL:
            return cached['data'], cached['source']

    items = []
    source = ''

    # 1차: 직접 웹 크롤링
    try:
        items = fetch_ap_news_direct(target_url)
        if items:
            source = 'AP News 웹 직접 수집 (Direct Web)'
    except Exception as e:
        logger.info(f"Direct crawl fallback triggered: {e}")

    # 2차: RSS 피드 폴백
    if not items:
        try:
            items = fetch_ap_news_rss(category)
            if items:
                source = 'AP News RSS 피드 수집 (RSS Fallback)'
        except Exception as e:
            logger.info(f"RSS fallback also failed: {e}")

    # 3차: 오프라인 샘플
    if not items:
        import copy
        items = copy.deepcopy(_SAMPLE_ARTICLES)
        source = '샘플 데이터 (네트워크 상태 확인 필요)'

    # 캐시 갱신
    NEWS_CACHE[cache_key] = {
        'data': items,
        'source': source,
        'timestamp': now
    }

    return items, source


def get_article_summary(url):
    """
    기사 원문 링크에서 본문을 크롤링하여 앞부분 3~4개 문단을 요약본으로 추출한다.
    """
    if url in SUMMARY_CACHE:
        return SUMMARY_CACHE[url]

    if not url.startswith('http'):
        return "유효한 기사 링크가 없습니다."

    try:
        if HAS_CURL_CFFI:
            res = c_requests.get(url, headers=_DEFAULT_HEADERS, impersonate='chrome120', timeout=15)
        else:
            res = c_requests.get(url, headers=_DEFAULT_HEADERS, timeout=15)

        if res.status_code != 200:
            return f"기사 본문을 가져올 수 없습니다. (HTTP {res.status_code})"

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # AP News 본문 탐색
        paragraphs = soup.select('.RichTextStoryBody p, .StoryBody p, main p, article p')
        
        text_blocks = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            # 너무 짧은 텍스트(광고/메타) 제외
            if len(text) > 60:
                text_blocks.append(text)

        if not text_blocks:
            return "기사 본문 텍스트를 추출할 수 없습니다."

        # 처음 3~4개의 주요 문단을 합쳐 요약본으로 생성
        summary_text = " ".join(text_blocks[:3])
        
        SUMMARY_CACHE[url] = summary_text
        return summary_text
    except Exception as e:
        logger.error(f"Summary extraction failed for {url}: {e}")
        return f"요약 실패: {str(e)}"


def _translate_via_web(text):
    """Google Translate 무료 웹 API 직접 호출 (cgi/googletrans 의존성 없이 Python 3.13+ 완벽 호환)"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "ko",
            "dt": "t",
            "q": text
        }
        res = requests.get(url, params=params, timeout=7)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and data and isinstance(data[0], list):
                translated_parts = [part[0] for part in data[0] if part and len(part) > 0 and part[0]]
                if translated_parts:
                    return "".join(translated_parts)
    except Exception as e:
        logger.warning(f"Direct Google Translate Web API failed: {e}")
    return None


def translate_text(text):
    """
    영문 텍스트를 한국어로 번역한다.
    1) 캐시 확인
    2) googletrans 사용 시도
    3) 실패 또는 googletrans 미지원 시 직접 Web API로 자동 폴백
    """
    clean_text = text.strip()
    if not clean_text:
        return ""
    if clean_text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[clean_text]

    # 1순위: googletrans (설치 및 동작 가능한 환경)
    if HAS_GOOGLETRANS and _translator:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                with _translator_lock:
                    t = _get_translator()
                    if t:
                        res = t.translate(clean_text, src='en', dest='ko')
                        if res and res.text:
                            TRANSLATION_CACHE[clean_text] = res.text
                            return res.text
            except Exception as e:
                logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    with _translator_lock:
                        _reset_translator()

    # 2순위: Google Translate Web API 직접 호출 (Python 3.13/3.14 호환, cgi 불필요)
    web_res = _translate_via_web(clean_text)
    if web_res:
        TRANSLATION_CACHE[clean_text] = web_res
        return web_res

    return "번역 오류가 발생했습니다."


def get_pronunciation(word):
    """eng_to_ipa를 이용한 IPA 발음기호 조회."""
    w_lower = word.lower()
    try:
        if ipa:
            p = ipa.convert(w_lower)
            if p and p != w_lower:
                # 부분 변환 마커 '*' 제거
                return f"/{p.rstrip('*')}/"
        return f"/{w_lower}/"
    except Exception:
        return f"/{w_lower}/"


def get_word_info(word):
    """
    WordNet을 이용한 품사 및 한국어 정의 조회.
    Returns: (meaning_kr, pos_kr)
    """
    w_lower = word.lower()
    if not HAS_WORDNET:
        meaning = translate_text(w_lower)
        return meaning, '-'

    try:
        synsets = wordnet.synsets(w_lower)
        if synsets:
            syn = synsets[0]
            definition = syn.definition()
            pos_tag = syn.pos()
            pos_kr = POS_DICT.get(pos_tag, '기타')
            def_kr = translate_text(definition)
            return def_kr, pos_kr
        else:
            meaning = translate_text(w_lower)
            return meaning, '-'
    except Exception:
        meaning = translate_text(w_lower)
        return meaning, '-'


def analyze_sentence(sentence):
    """
    문장 내 주요 단어를 추출하여 IPA, 품사, 정의를 분석한다.
    불용어를 후순위로 정렬하여 학습 효율을 높인다.
    """
    if sentence in WORD_ANALYSIS_CACHE:
        return WORD_ANALYSIS_CACHE[sentence]

    words = re.findall(r'\b[a-zA-Z]+\b', sentence)
    unique_words = []
    seen = set()

    for w in words:
        w_lower = w.lower()
        if len(w) > 2 and w_lower not in seen:
            seen.add(w_lower)
            unique_words.append(w)

    results = []
    for word in unique_words:
        pron = get_pronunciation(word)
        meaning, pos = get_word_info(word)
        is_common = word.lower() in COMMON_STOPWORDS
        results.append({
            'word': word,
            'ipa': pron,
            'pos': pos,
            'meaning': meaning,
            'is_common': is_common
        })

    # 중요 단어(비불용어)를 우선 표시, 그 다음 알파벳 순
    results.sort(key=lambda x: (x['is_common'], x['word'].lower()))

    WORD_ANALYSIS_CACHE[sentence] = results
    return results


# ===================== Flask Routes =====================

@app.route('/')
def index():
    """메인 페이지 렌더링."""
    return render_template('index.html', categories=CATEGORY_URLS)


@app.route('/api/news', methods=['GET'])
def api_get_news():
    """AP News 헤드라인 API."""
    category = request.args.get('category', 'top')
    custom_url = request.args.get('url', '').strip()
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    try:
        items, source = get_ap_news(
            category=category,
            custom_url=custom_url or None,
            force_refresh=force_refresh
        )
        return jsonify({
            'status': 'success',
            'category': category,
            'source': source,
            'count': len(items),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'articles': items
        })
    except Exception as e:
        logger.error(f"API /api/news error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/check_url', methods=['GET'])
def api_check_url():
    """AP News URL 헬스 체크 API."""
    url = request.args.get('url', 'https://apnews.com/').strip()
    try:
        result = check_url_health(url)
        return jsonify(result)
    except Exception as e:
        logger.error(f"API /api/check_url error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/translate', methods=['POST'])
def api_translate():
    """한글 번역 API."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': '번역할 텍스트가 제공되지 않았습니다.'}), 400

    translation = translate_text(text)
    return jsonify({
        'status': 'success',
        'original': text,
        'translation': translation
    })


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """단어 분석 API."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': '분석할 텍스트가 제공되지 않았습니다.'}), 400

    try:
        analysis = analyze_sentence(text)
        return jsonify({
            'status': 'success',
            'original': text,
            'word_count': len(analysis),
            'words': analysis
        })
    except Exception as e:
        logger.error(f"API /api/analyze error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/summary', methods=['GET'])
def api_summary():
    """기사 원문 요약 API."""
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'status': 'error', 'message': 'No URL provided'}), 400

    try:
        summary = get_article_summary(url)
        return jsonify({
            'status': 'success',
            'url': url,
            'summary': summary
        })
    except Exception as e:
        logger.error(f"API /api/summary error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/tts', methods=['GET'])
def api_tts():
    """
    Google TTS 음성 스트리밍 API.
    - slow=true 파라미터로 느린 발음 모드 지원
    """
    text = request.args.get('text', '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400

    # 안전을 위한 최대 길이 제한 (요약본 읽기를 위해 2000으로 증가)
    max_len = 2000
    if len(text) > max_len:
        text = text[:max_len]

    slow_mode = request.args.get('slow', 'false').lower() == 'true'

    try:
        tts = gTTS(text=text, lang='en', slow=slow_mode)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return send_file(
            fp,
            mimetype='audio/mpeg',
            download_name='tts_audio.mp3',
            as_attachment=False
        )
    except Exception as e:
        logger.error(f"API /api/tts error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/clear_cache', methods=['POST'])
def api_clear_cache():
    """모든 서버 캐시를 초기화한다."""
    NEWS_CACHE.clear()
    TRANSLATION_CACHE.clear()
    WORD_ANALYSIS_CACHE.clear()
    SUMMARY_CACHE.clear()
    logger.info("All caches cleared by user request")
    return jsonify({
        'status': 'success',
        'message': '모든 캐시가 초기화되었습니다.'
    })


@app.route('/api/status', methods=['GET'])
def api_status():
    """서버 상태 및 캐시 통계 API."""
    total_cached_articles = sum(
        len(v.get('data', []))
        for v in NEWS_CACHE.values()
    )
    return jsonify({
        'status': 'healthy',
        'cached_articles': total_cached_articles,
        'cached_categories': len(NEWS_CACHE),
        'cached_translations': len(TRANSLATION_CACHE),
        'cached_analyses': len(WORD_ANALYSIS_CACHE),
        'cached_summaries': len(SUMMARY_CACHE),
        'has_curl_cffi': HAS_CURL_CFFI,
        'has_wordnet': HAS_WORDNET,
        'has_ipa': ipa is not None
    })


# ===================== Main Entry Point =====================

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('PORT', os.environ.get('FLASK_PORT', '5000')))

    print("=" * 60)
    print("🚀 AP News English Learning App v2 (Flask Server)")
    print(f"👉 Local URL: http://127.0.0.1:{port}")
    print(f"🔧 Debug: {debug_mode} | curl_cffi: {HAS_CURL_CFFI} | WordNet: {HAS_WORDNET}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
