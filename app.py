    # -*- coding: utf-8 -*-
"""
AP News English Learning Web App (Flask Migration)
- AP News Real-time Scraping with Cloudflare bypass (curl_cffi) & RSS fallback
- URL Health Check & Verification
- Google Translation
- Google Text-to-Speech (gTTS) streaming
- Vocabulary Analysis: IPA Pronunciation & WordNet Part-of-Speech / Definitions
"""

import sys
import io
import re
import time
import tempfile
import threading
from functools import lru_cache
from urllib.parse import urlparse

# Windows console encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Python 3.13 NumPy/SciPy compatibility patch for NLTK
try:
    import numpy as np
    if not hasattr(np, 'long'):
        np.long = int
    if not hasattr(np, 'ulong'):
        np.ulong = int
except Exception:
    pass

from flask import Flask, render_template, request, jsonify, send_file, Response
from bs4 import BeautifulSoup
from gtts import gTTS
from googletrans import Translator

# Optional/Fallback Libraries
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
    print(f"[Warning] NLTK WordNet not available: {e}")

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Translator instance with lock for thread-safety
translator_lock = threading.Lock()
translator = Translator()

# In-memory caches
NEWS_CACHE = {
    'data': [],
    'category': 'top',
    'source': '',
    'url': '',
    'timestamp': 0
}
CACHE_TTL = 900  # 15 minutes

TRANSLATION_CACHE = {}
WORD_ANALYSIS_CACHE = {}

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

COMMON_STOPWORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
    'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
    'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
    'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
    'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
    'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
    'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also'
}


def check_url_health(url):
    """
    Check if the specified AP News URL is reachable and extract health stats.
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
    
    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        result['message'] = "잘못된 URL 형식입니다. (예: https://apnews.com/)"
        return result

    # Check via curl_cffi or requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        if HAS_CURL_CFFI:
            res = c_requests.get(url, headers=headers, impersonate='chrome120', timeout=12)
            result['method'] = 'curl_cffi (Chrome Impersonation)'
        else:
            import requests
            res = requests.get(url, headers=headers, timeout=10)
            result['method'] = 'Standard requests'

        result['status_code'] = res.status_code
        result['latency_ms'] = int((time.time() - start_time) * 1000)

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            page_promos = soup.select('.PagePromo, div[data-key="feed-card"], .CardHeadline, h2, h3')
            count = 0
            for el in page_promos:
                txt = el.get_text(strip=True)
                if len(txt) > 25:
                    count += 1
            result['headlines_found'] = count
            result['status'] = 'success'
            result['message'] = f"정상 연결 성공! ({count}개 기사 탐지됨)"
        elif res.status_code == 403:
            result['status'] = 'warning'
            result['message'] = "403 Forbidden (Cloudflare 방어 활성화됨 - RSS 대체 모드로 자동 연결됩니다)"
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
    Directly crawl AP News webpage using curl_cffi Chrome impersonation
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    if not HAS_CURL_CFFI:
        raise Exception("curl_cffi is required for direct AP News scraping")

    res = c_requests.get(target_url, headers=headers, impersonate='chrome120', timeout=15)
    if res.status_code != 200:
        raise Exception(f"HTTP Status {res.status_code}")

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

        # Filter out short or duplicate titles
        if title and len(title) > 20 and title not in seen_titles:
            # Check for English content (avoid non-English stories like Spanish edition)
            ascii_chars = sum(1 for c in title if ord(c) < 128)
            if ascii_chars / len(title) < 0.7:
                continue

            full_link = link if link.startswith('http') else ('https://apnews.com' + link if link else '')
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
    Fallback method using Google News AP News RSS Feed
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
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(rss_url)
    items = []
    seen_titles = set()

    for entry in feed.entries:
        title = entry.title
        # Clean title - AP News suffix
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


def get_ap_news(category='top', custom_url=None, force_refresh=False):
    """
    Combined news fetching logic with cache and fallback
    """
    global NEWS_CACHE
    now = time.time()
    
    target_url = custom_url.strip() if custom_url else CATEGORY_URLS.get(category, CATEGORY_URLS['top'])
    cache_key = target_url

    if not force_refresh and NEWS_CACHE['url'] == cache_key and (now - NEWS_CACHE['timestamp']) < CACHE_TTL:
        if NEWS_CACHE['data']:
            return NEWS_CACHE['data'], NEWS_CACHE['source']

    items = []
    source = ''

    # 1. Try direct crawl
    try:
        items = fetch_ap_news_direct(target_url)
        if items:
            source = 'AP News 웹 직접 수집 (Direct Web)'
    except Exception as e:
        print(f"[Direct Crawl Notice] {e}")

    # 2. Try RSS Fallback if direct crawl failed or returned no items
    if not items:
        try:
            items = fetch_ap_news_rss(category)
            if items:
                source = 'AP News RSS 피드 수집 (RSS Fallback)'
        except Exception as e:
            print(f"[RSS Fallback Notice] {e}")

    # 3. Fallback dummy if both fail (guarantee app works even offline)
    if not items:
        items = [
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
        source = '샘플 데이터 (네트워크 상태 확인 필요)'

    # Update cache
    NEWS_CACHE['data'] = items
    NEWS_CACHE['category'] = category
    NEWS_CACHE['url'] = cache_key
    NEWS_CACHE['source'] = source
    NEWS_CACHE['timestamp'] = now

    return items, source


def translate_text(text):
    """
    Translate English text to Korean with caching
    """
    clean_text = text.strip()
    if not clean_text:
        return ""
    if clean_text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[clean_text]

    try:
        with translator_lock:
            res = translator.translate(clean_text, src='en', dest='ko')
            translated = res.text
            TRANSLATION_CACHE[clean_text] = translated
            return translated
    except Exception as e:
        return f"번역 오류: {str(e)}"


def get_pronunciation(word):
    """
    Get IPA pronunciation using eng_to_ipa
    """
    w_lower = word.lower()
    try:
        if ipa:
            p = ipa.convert(w_lower)
            if p and p != w_lower and not p.endswith('*'):
                return f"/{p}/"
            elif p and p.endswith('*'):
                # Partially converted
                return f"/{p.replace('*', '')}/"
        return f"/{w_lower}/"
    except Exception:
        return f"/{w_lower}/"


def get_word_info(word):
    """
    Extract POS and definition translated to Korean
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

            # Translate definition
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
    Analyze words in a headline: extraction, IPA, POS, and definition
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

    # Sort results: uncommon/important words first, then alphabetical
    results.sort(key=lambda x: (x['is_common'], x['word'].lower()))

    WORD_ANALYSIS_CACHE[sentence] = results
    return results


# ===================== Flask Routes =====================

@app.route('/')
def index():
    """Main Application Page"""
    return render_template('index.html', categories=CATEGORY_URLS)


@app.route('/api/news', methods=['GET'])
def api_get_news():
    """Get AP News headlines"""
    category = request.args.get('category', 'top')
    custom_url = request.args.get('url', '').strip()
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    items, source = get_ap_news(category=category, custom_url=custom_url or None, force_refresh=force_refresh)
    return jsonify({
        'status': 'success',
        'category': category,
        'source': source,
        'count': len(items),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'articles': items
    })


@app.route('/api/check_url', methods=['GET'])
def api_check_url():
    """Verify and benchmark an AP News URL"""
    url = request.args.get('url', 'https://apnews.com/').strip()
    res = check_url_health(url)
    return jsonify(res)


@app.route('/api/translate', methods=['POST'])
def api_translate():
    """Translate headline or text to Korean"""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400

    translation = translate_text(text)
    return jsonify({
        'status': 'success',
        'original': text,
        'translation': translation
    })


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Analyze words in a sentence"""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400

    analysis = analyze_sentence(text)
    return jsonify({
        'status': 'success',
        'original': text,
        'word_count': len(analysis),
        'words': analysis
    })


@app.route('/api/tts', methods=['GET'])
def api_tts():
    """Stream Google Text-to-Speech audio for the given text"""
    text = request.args.get('text', '').strip()
    if not text:
        return "No text provided", 400

    # Limit max text length for safety
    if len(text) > 500:
        text = text[:500]

    try:
        tts = gTTS(text=text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return send_file(fp, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def api_status():
    """Return backend status and stats"""
    return jsonify({
        'status': 'healthy',
        'cached_articles': len(NEWS_CACHE['data']),
        'cached_translations': len(TRANSLATION_CACHE),
        'cached_analyses': len(WORD_ANALYSIS_CACHE),
        'has_curl_cffi': HAS_CURL_CFFI,
        'has_wordnet': HAS_WORDNET,
        'has_ipa': ipa is not None
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AP News English Learning App (Flask Server)")
    print("👉 Local URL: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
