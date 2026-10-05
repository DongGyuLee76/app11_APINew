import os
import sys
import threading
import re
import random
from datetime import datetime

# Kivy / KivyMD Imports
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast
from kivymd.uix.toolbar import MDTopAppBar

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.properties import StringProperty, BooleanProperty

# External Libraries (with safe imports)
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

try:
    from googletrans import Translator
except ImportError:
    Translator = None

# --- Android Permission Handling ---
def request_permissions():
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET, 
                Permission.ACCESS_NETWORK_STATE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        except Exception as e:
            print(f"Permission request failed: {e}")

# --- Logic Functions with Fallbacks ---

def fetch_ap_news_safe():
    """Safely fetch news with a fallback to sample data."""
    if not requests or not BeautifulSoup:
        return get_sample_news()

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
            'h2.PagePromo-title', 'h3.PagePromo-title',
            'span.PagePromoContentIcons-text', 'div.CardHeadline',
            'h2', 'h3'
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
        
        return headlines if headlines else get_sample_news()
    except Exception as e:
        print(f"News fetch error: {e}")
        return get_sample_news()

def get_sample_news():
    """Fallback sample news data."""
    return [
        "Global markets rally as inflation shows signs of cooling",
        "Tech giant unveils new AI-powered smartphone features",
        "Historic peace treaty signed in Geneva today",
        "Scientists discover potential cure for rare disease",
        "World Cup finals set to begin next week in major upset",
        "SpaceX successfully launches new satellite constellation",
        "Major city announces plans for 100% renewable energy",
        "New archaeological find rewrites history of ancient civilization",
        "Electric vehicle sales surpass traditional cars in key markets",
        "International film festival opens with record attendance"
    ]

def translate_safe(text):
    """Safely translate text with fallback."""
    if not Translator:
        return "[Translation Library Missing]"
    
    try:
        translator = Translator()
        result = translator.translate(text, src='en', dest='ko')
        return result.text
    except Exception as e:
        print(f"Translation error: {e}")
        return "번역 서비스를 사용할 수 없습니다."

def analyze_words_safe(text):
    """Simple word analysis without heavy NLTK dependency."""
    try:
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        unique_words = sorted(set([w for w in words if len(w) > 3]))[:10]
        
        results = []
        for word in unique_words:
            results.append({
                'word': word.capitalize(),
                'meaning': get_simple_meaning(word)
            })
        return results
    except Exception as e:
        print(f"Analysis error: {e}")
        return []

def get_simple_meaning(word):
    """Fallback dictionary for common words to avoid NLTK crash."""
    # This is a tiny fallback dictionary. In a real app, you might use a local DB or API.
    common_dict = {
        'market': '시장', 'inflation': '인플레이션', 'cooling': '냉각/진정',
        'giant': '거대 기업', 'unveils': '공개하다', 'features': '특징',
        'treaty': '조약', 'signed': '서명된', 'geneva': '제네바',
        'discover': '발견하다', 'disease': '질병', 'launch': '발사하다',
        'energy': '에너지', 'sales': '판매', 'record': '기록적인'
    }
    return common_dict.get(word.lower(), "단어 정보 없음")

# --- UI Components ---

KV = '''
<NewsCard>:
    orientation: "vertical"
    padding: "12dp"
    size_hint_y: None
    height: self.minimum_height
    elevation: 1
    radius: [10, 10, 10, 10]
    md_bg_color: 1, 1, 1, 1
    spacing: "8dp"

    MDLabel:
        text: root.headline_text
        font_style: "H6"
        theme_text_color: "Primary"
        adaptive_height: True
        markup: True
        font_size: "16sp"

    MDBoxLayout:
        orientation: "horizontal"
        adaptive_height: True
        spacing: "10dp"

        MDRaisedButton:
            text: "🇰🇷 번역"
            on_release: root.toggle_translation()
            size_hint_x: 0.5
            md_bg_color: app.theme_cls.primary_color

        MDRaisedButton:
            text: "📚 분석"
            on_release: root.analyze()
            size_hint_x: 0.5
            md_bg_color: 0.3, 0.3, 0.3, 1

    MDLabel:
        text: root.translation_text
        theme_text_color: "Secondary"
        adaptive_height: True
        opacity: 1 if root.is_translated else 0
        height: self.texture_size[1] if root.is_translated else 0
        color: 0, 0.5, 0, 1

<APNewsScreen>:
    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "AP News (Lite)"
            right_action_items: [["refresh", lambda x: root.refresh_news()], ["close", lambda x: app.exit_app()]]
            elevation: 2

        MDBoxLayout:
            id: content_area
            orientation: "vertical"
            
            MDSpinner:
                id: spinner
                size_hint: None, None
                size: dp(46), dp(46)
                pos_hint: {'center_x': .5, 'center_y': .5}
                active: False

            MDScrollView:
                id: scroll_view
                MDBoxLayout:
                    id: news_list
                    orientation: "vertical"
                    adaptive_height: True
                    padding: "10dp"
                    spacing: "15dp"
'''

class NewsCard(MDCard):
    headline_text = StringProperty("")
    translation_text = StringProperty("")
    is_translated = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None

    def toggle_translation(self):
        if not self.translation_text:
            toast("번역 중...")
            threading.Thread(target=self._translate_thread).start()
        else:
            self.is_translated = not self.is_translated

    def _translate_thread(self):
        result = translate_safe(self.headline_text)
        Clock.schedule_once(lambda dt: self._update_translation(result))

    def _update_translation(self, text):
        self.translation_text = text
        self.is_translated = True

    def analyze(self):
        toast("분석 중...")
        threading.Thread(target=self._analyze_thread).start()

    def _analyze_thread(self):
        data = analyze_words_safe(self.headline_text)
        Clock.schedule_once(lambda dt: self._show_analysis_dialog(data))

    def _show_analysis_dialog(self, data):
        if not data:
            toast("분석할 단어가 없습니다.")
            return

        content_text = ""
        for item in data:
            content_text += f"[b]{item['word']}[/b]\n{item['meaning']}\n\n"

        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title="단어 분석 (Lite)",
            text=content_text,
            size_hint=(0.8, None),
            height=dp(300),
            buttons=[
                MDFlatButton(
                    text="닫기",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()

class APNewsScreen(MDScreen):
    def refresh_news(self):
        self.ids.news_list.clear_widgets()
        self.ids.spinner.active = True
        threading.Thread(target=self._fetch_news_thread).start()

    def _fetch_news_thread(self):
        headlines = fetch_ap_news_safe()
        Clock.schedule_once(lambda dt: self._update_news_list(headlines))

    def _update_news_list(self, headlines):
        self.ids.spinner.active = False
        for headline in headlines:
            card = NewsCard(headline_text=headline)
            self.ids.news_list.add_widget(card)
        toast("뉴스 업데이트 완료")

class APNewsApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        Builder.load_string(KV)
        return APNewsScreen()

    def on_start(self):
        request_permissions()
        self.root.refresh_news()

    def exit_app(self):
        if platform == 'android':
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            PythonActivity.mActivity.finish()
        else:
            self.stop()

if __name__ == "__main__":
    from kivy.lang import Builder
    try:
        APNewsApp().run()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
