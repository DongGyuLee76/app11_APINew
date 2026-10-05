# main.py - AP News App (Fixed Origin Version)
# Based on main_origin.py with stability fixes:
# 1. Robust Font Handling (NanumGothic) to prevent crashes/squares
# 2. Improved Translation (DeepTranslator + GoogleTrans Fallback)
# 3. Safe NLTK Initialization

from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.dialog import MDDialog
from kivy.metrics import dp
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.text import LabelBase

import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import os
import tempfile
import re
import json
import threading

# Android Permissions
def request_android_permissions():
    """Request Android permissions safely"""
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission, check_permission
            perms = [
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.ACCESS_NETWORK_STATE
            ]
            needed_perms = [p for p in perms if not check_permission(p)]
            if needed_perms:
                request_permissions(needed_perms)
        except Exception as e:
            print(f"Permission Error: {e}")

# Safe NLTK Init
def init_nltk_safe():
    """Initialize NLTK safely"""
    try:
        import nltk
        try:
            nltk.data.find('corpora/wordnet.zip')
        except LookupError:
            try:
                nltk.download('wordnet', quiet=True)
                nltk.download('omw-1.4', quiet=True)
            except:
                print("NLTK Download Failed")
    except Exception as e:
        print(f"NLTK Init Error: {e}")

class NewsCard(MDCard):
    """News Card Component"""
    
    def __init__(self, headline, index, app_instance, font_name='Roboto', **kwargs):
        super().__init__(**kwargs)
        self.headline = headline
        self.index = index
        self.app = app_instance
        self.target_font = font_name
        self.show_translation = False
        
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(200)
        self.padding = dp(15)
        self.spacing = dp(10)
        self.md_bg_color = (0.98, 0.98, 0.98, 1)
        self.elevation = 3
        self.radius = [15]
        
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title_label = MDLabel(
            text=f"[b]📄 기사 {self.index}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Custom",
            text_color=(0.17, 0.24, 0.31, 1),
            font_name=self.target_font
        )
        self.add_widget(title_label)
        
        # Content
        self.content_label = MDLabel(
            text=self.headline,
            size_hint_y=None,
            font_style='Body1',
            theme_text_color="Custom",
            text_color=(0.2, 0.2, 0.2, 1),
            font_name=self.target_font
        )
        self.content_label.bind(texture_size=self.content_label.setter('size'))
        self.add_widget(self.content_label)
        
        # Buttons
        button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        tts_btn = MDRaisedButton(
            text="🔊 읽기",
            md_bg_color=(0.3, 0.7, 0.3, 1),
            font_name=self.target_font,
            on_release=self.play_tts
        )
        button_layout.add_widget(tts_btn)
        
        trans_btn = MDRaisedButton(
            text="🇰🇷 번역",
            md_bg_color=(0.2, 0.6, 0.9, 1),
            font_name=self.target_font,
            on_release=self.toggle_translation
        )
        button_layout.add_widget(trans_btn)
        
        analyze_btn = MDRaisedButton(
            text="📚 분석",
            md_bg_color=(0.9, 0.5, 0.2, 1),
            font_name=self.target_font,
            on_release=self.toggle_analysis
        )
        button_layout.add_widget(analyze_btn)
        
        self.add_widget(button_layout)
        
        # Translation Label
        self.translation_label = MDLabel(
            text="",
            size_hint_y=None,
            height=0,
            theme_text_color="Secondary",
            markup=True,
            font_name=self.target_font
        )
        self.add_widget(self.translation_label)
    
    def play_tts(self, instance):
        self.app.show_loading("음성 생성 중...")
        threading.Thread(target=self._play_tts_async, daemon=True).start()
    
    def _play_tts_async(self):
        try:
            audio_file = self.app.text_to_speech(self.headline, self.index)
            if audio_file and os.path.exists(audio_file):
                Clock.schedule_once(lambda dt: self._play_audio(audio_file), 0)
            else:
                Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
                Clock.schedule_once(lambda dt: self.app.show_error("음성 파일 생성 실패"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_error(f"TTS 오류: {str(e)}"), 0)
    
    def _play_audio(self, audio_file):
        try:
            sound = SoundLoader.load(audio_file)
            if sound:
                sound.play()
                Clock.schedule_once(lambda dt: self._cleanup_audio(audio_file), sound.length + 1)
            self.app.hide_loading()
        except Exception as e:
            self.app.hide_loading()
            self.app.show_error(f"재생 오류: {str(e)}")
    
    def _cleanup_audio(self, filepath):
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except: pass
    
    def toggle_translation(self, instance):
        self.show_translation = not self.show_translation
        if self.show_translation:
            self.app.show_loading("번역 중...")
            threading.Thread(target=self._show_translation, daemon=True).start()
        else:
            self.translation_label.text = ""
            self.translation_label.height = 0
            self.height = dp(200)
    
    def _show_translation(self):
        try:
            translation = self.app.translate_to_korean(self.headline)
            Clock.schedule_once(lambda dt: self._update_translation_ui(translation), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_error(f"번역 오류: {str(e)}"), 0)
    
    def _update_translation_ui(self, translation):
        self.translation_label.text = f"[b]한글 번역:[/b] {translation}"
        self.translation_label.height = dp(60)
        self.height = dp(260)
        self.app.hide_loading()
    
    def toggle_analysis(self, instance):
        self.app.show_loading("단어 분석 중...")
        threading.Thread(target=self._show_analysis, daemon=True).start()
    
    def _show_analysis(self):
        try:
            word_info = self.app.analyze_words(self.headline)
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_analysis_dialog(word_info), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_error(f"분석 오류: {str(e)}"), 0)


class APNewsApp(MDApp):
    """Main App Class"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headlines = []
        self.cache_file = None
        self.dialog = None
        self.loading_dialog = None
        self.nltk_available = False
        self.font_name = 'Roboto'
        
    def on_start(self):
        request_android_permissions()
        threading.Thread(target=self._init_nltk, daemon=True).start()
    
    def _init_nltk(self):
        try:
            init_nltk_safe()
            import nltk
            from nltk.corpus import wordnet
            wordnet.synsets('test')
            self.nltk_available = True
        except:
            self.nltk_available = False
            print("NLTK Unavailable")
        
    def build(self):
        # Font Registration
        self.register_font()
        
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.theme_style = "Light"
        
        # Cache Path
        if platform == 'android':
            try:
                from android.storage import app_storage_path
                self.cache_file = os.path.join(app_storage_path(), 'news_cache.json')
            except:
                self.cache_file = '/sdcard/news_cache.json'
        else:
            self.cache_file = 'news_cache.json'
        
        main_layout = BoxLayout(orientation='vertical')
        
        toolbar = MDTopAppBar(
            title="📰 AP News",
            md_bg_color=(0.3, 0.7, 0.3, 1),
            right_action_items=[["refresh", lambda x: self.refresh_news()]]
        )
        main_layout.add_widget(toolbar)
        
        scroll = ScrollView()
        self.news_layout = GridLayout(
            cols=1,
            spacing=dp(15),
            padding=dp(15),
            size_hint_y=None
        )
        self.news_layout.bind(minimum_height=self.news_layout.setter('height'))
        
        scroll.add_widget(self.news_layout)
        main_layout.add_widget(scroll)
        
        Clock.schedule_once(lambda dt: self.load_news(), 1.0)
        
        return main_layout

    def register_font(self):
        """Register NanumGothic font"""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(base_dir, 'NanumGothic.ttf')
            
            if os.path.exists(font_path):
                LabelBase.register(name='Korean', fn_regular=font_path, fn_bold=font_path, fn_italic=font_path, fn_bolditalic=font_path)
                self.font_name = 'Korean'
                print(f"✅ Local Font Registered: {font_path}")
                return

            if platform == 'android':
                system_fonts = ['/system/fonts/NanumGothic.ttf', '/system/fonts/DroidSansFallback.ttf', '/system/fonts/NotoSansKR-Regular.otf']
                for sys_font in system_fonts:
                    if os.path.exists(sys_font):
                        LabelBase.register(name='Korean', fn_regular=sys_font, fn_bold=sys_font)
                        self.font_name = 'Korean'
                        print(f"✅ System Font Registered: {sys_font}")
                        return
            
            self.font_name = 'Roboto'
        except Exception as e:
            print(f"❌ Font Error: {e}")
            self.font_name = 'Roboto'
    
    def load_news(self):
        self.show_loading("AP News에서 기사를 가져오는 중...")
        threading.Thread(target=self._load_news_async, daemon=True).start()
    
    def _load_news_async(self):
        try:
            cached_headlines = self.load_cache()
            if cached_headlines:
                self.headlines = cached_headlines
            else:
                self.headlines = self.fetch_ap_news()
                self.save_cache(self.headlines)
            
            Clock.schedule_once(lambda dt: self.update_news_ui(), 0)
            Clock.schedule_once(lambda dt: self.hide_loading(), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.show_error(f"뉴스 로드 오류: {str(e)}"), 0)
    
    def update_news_ui(self):
        self.news_layout.clear_widgets()
        if not self.headlines:
            self.headlines = ["뉴스를 불러올 수 없습니다. 새로고침을 시도하세요."]
        
        for idx, headline in enumerate(self.headlines, 1):
            card = NewsCard(headline, idx, self, font_name=self.font_name)
            self.news_layout.add_widget(card)
    
    def refresh_news(self):
        self.clear_cache()
        self.load_news()
    
    def fetch_ap_news(self):
        try:
            url = "https://apnews.com/"
            headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10)'}
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            headlines = []
            selectors = ['h2.PagePromo-title', 'h3.PagePromo-title', 'div.CardHeadline', 'h2', 'h3']
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 20 and text not in headlines:
                        headlines.append(text)
                    if len(headlines) >= 10: break
                if len(headlines) >= 10: break
            
            return headlines[:10] if headlines else ["기사를 가져올 수 없습니다."]
        except Exception as e:
            return [f"오류: {str(e)}"]
    
    def translate_to_korean(self, text):
        # 1. Deep Translator
        try:
            from deep_translator import GoogleTranslator
            return GoogleTranslator(source='en', target='ko').translate(text)
        except: pass
        
        # 2. GoogleTrans
        try:
            from googletrans import Translator
            return Translator().translate(text, src='en', dest='ko').text
        except: pass
        
        # 3. Fallback
        return self._simple_translate(text)

    def _simple_translate(self, text):
        # Simple dictionary fallback
        translations = {'Trump': '트럼프', 'Putin': '푸틴', 'Ukraine': '우크라이나', 'war': '전쟁', 'Stock': '주식', 'market': '시장'}
        result = text
        for en, ko in translations.items():
            result = result.replace(en, ko)
        return result
    
    def text_to_speech(self, text, index):
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            if platform == 'android':
                try:
                    from android.storage import app_storage_path
                    temp_dir = app_storage_path()
                except: temp_dir = '/sdcard'
            else:
                temp_dir = tempfile.gettempdir()
            
            filepath = os.path.join(temp_dir, f'tts_{index}.mp3')
            tts.save(filepath)
            return filepath
        except Exception as e:
            print(f"TTS Error: {e}")
            return None
    
    def analyze_words(self, sentence):
        words = re.findall(r'\b[a-zA-Z]+\b', sentence.lower())
        unique_words = sorted(set(words))
        word_info = []
        for word in unique_words[:15]:
            if len(word) > 2:
                word_info.append({
                    '단어': word.capitalize(),
                    '발음기호': f"/{word}/",
                    '품사': '-',
                    '뜻': self.translate_to_korean(word)
                })
        return word_info
    
    # Cache Methods
    def save_cache(self, data):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except: pass
    
    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return None
    
    def clear_cache(self):
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except: pass
    
    # Dialogs
    def show_loading(self, message):
        if not self.loading_dialog:
            self.loading_dialog = MDDialog(text=message, size_hint=(0.8, None), height=dp(200))
        else: self.loading_dialog.text = message
        try: self.loading_dialog.open()
        except: pass
    
    def hide_loading(self):
        if self.loading_dialog:
            try: self.loading_dialog.dismiss()
            except: pass
    
    def show_error(self, message):
        if self.dialog:
            try: self.dialog.dismiss()
            except: pass
        self.dialog = MDDialog(title="오류", text=message, buttons=[MDFlatButton(text="확인", on_release=lambda x: self.dialog.dismiss())])
        try: self.dialog.open()
        except: pass
    
    def show_analysis_dialog(self, word_info):
        if not word_info:
            self.show_error("분석할 단어가 없습니다.")
            return
        
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        for info in word_info:
            word_card = MDCard(orientation='vertical', size_hint_y=None, height=dp(100), padding=dp(10), spacing=dp(5), elevation=2, radius=[10])
            word_card.add_widget(MDLabel(text=f"[b]{info['단어']}[/b]  {info['발음기호']}", markup=True, size_hint_y=None, height=dp(30), font_name=self.font_name))
            word_card.add_widget(MDLabel(text=info['뜻'], size_hint_y=None, height=dp(35), font_style='Caption', font_name=self.font_name))
            content.add_widget(word_card)
        
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        
        if self.dialog:
            try: self.dialog.dismiss()
            except: pass
        
        self.dialog = MDDialog(title="📖 단어 분석 결과", type="custom", content_cls=scroll, size_hint=(0.9, 0.8), buttons=[MDFlatButton(text="닫기", on_release=lambda x: self.dialog.dismiss())])
        try: self.dialog.open()
        except: pass

if __name__ == '__main__':
    APNewsApp().run()
