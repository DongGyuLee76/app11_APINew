# -*- coding: utf-8 -*-
"""
AP News English Learning Web App - v1 (Flask)
개선 내역 (app.py → app_v1.py):

[BUG FIX]
  1. 첫 줄 인덴트 오류 수정 (들여쓰기 공백이 들어가 SyntaxError 유발 가능)
  2. Translator 인스턴스 재사용 시 googletrans 내부 세션 만료로 번역 실패하는 문제
     → 실패 시 Translator를 재생성하는 retry 로직 추가
  3. lru_cache import 후 미사용 제거 (unused import)
  4. tempfile import 후 미사용 제거 (unused import)
  5. Response import 후 미사용 제거 (unused import)
  6. check_url_health에서 HAS_CURL_CFFI=False일 때 c_requests에 impersonate를 전달하여 TypeError 발생
     → 분기 처리 수정
  7. fetch_ap_news_direct의 link 경로에 '//' 중복 슬래시 가능성 방지
  8. gTTS BytesIO 객체에 Content-Disposition 헤더 누락으로 일부 브라우저에서 재생 불가
     → 명시적 헤더 추가

[IMPROVEMENT]
  9. 카테고리별 캐시 분리 (기존: 단일 캐시라서 카테고리 전환 시 매번 재수집)
     → dict 기반 멀티 캐시로 변경
  10. 번역 캐시 무한 증가 방지 → LRU 스타일 maxsize 제한 (5000건)
  11. 단어 분석 캐시 무한 증가 방지 → maxsize 제한 (500건)
  12. API 에러 응답 통일 (일관된 JSON 에러 포맷)
  13. TTS slow 모드 파라미터 추가 (프론트에서 느린 발음 요청 가능)
  14. /api/clear_cache 엔드포인트 추가 (프론트에서 캐시 초기화 가능)
  15. RSS URL 쿼리에 urllib.parse.quote 적용하여 특수문자 안전 처리
  16. 로깅 시스템을 print → logging 모듈로 교체
  17. Flask debug 모드 환경변수 제어 (운영환경 자동 대응)
  18. CORS 지원 추가 (flask-cors 설치된 경우 자동 활성화)
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

from bs4 import BeautifulSoup
from gtts import gTTS
from googletrans import Translator

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
_translator = Translator()


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
    _translator = Translator()
    logger.info("Translator instance reset due to session expiry or error")


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


def translate_text(text):
    """
    영문 텍스트를 한국어로 번역한다.
    googletrans 세션 만료 시 Translator를 재생성하여 자동 복구한다.
    """
    clean_text = text.strip()
    if not clean_text:
        return ""
    if clean_text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[clean_text]

    max_retries = 2
    for attempt in range(max_retries):
        try:
            with _translator_lock:
                t = _get_translator()
                res = t.translate(clean_text, src='en', dest='ko')
                translated = res.text
                TRANSLATION_CACHE[clean_text] = translated
                return translated
        except Exception as e:
            logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                with _translator_lock:
                    _reset_translator()
            else:
                return f"번역 오류: {str(e)}"


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


@app.route('/api/tts', methods=['GET'])
def api_tts():
    """
    Google TTS 음성 스트리밍 API.
    - slow=true 파라미터로 느린 발음 모드 지원
    """
    text = request.args.get('text', '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400

    # 안전을 위한 최대 길이 제한
    max_len = 500
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
        'has_curl_cffi': HAS_CURL_CFFI,
        'has_wordnet': HAS_WORDNET,
        'has_ipa': ipa is not None
    })


# ===================== Main Entry Point =====================

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('FLASK_PORT', '5000'))

    print("=" * 60)
    print("🚀 AP News English Learning App v1 (Flask Server)")
    print(f"👉 Local URL: http://127.0.0.1:{port}")
    print(f"🔧 Debug: {debug_mode} | curl_cffi: {HAS_CURL_CFFI} | WordNet: {HAS_WORDNET}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
