# main.py - AP News App (Final Stable Version)
# Features: Translation (DeepTranslator + GoogleTrans Fallback), Word Analysis, Custom Font Support
# Fixes: Font Crash, Square Characters in Bold Text, Translation Failures

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
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.text import LabelBase

import os
import threading
import re
import sys

# Android Permissions
def request_permissions():
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.ACCESS_NETWORK_STATE])
        except Exception as e:
            print(f"⚠️ Permission Error: {e}")

class NewsCard(MDCard):
    def __init__(self, title, content, index, app_instance, font_name='Roboto', **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.content_text = content
        self.index = index
        self.app = app_instance
        self.target_font = font_name
        self.show_translation = False
        
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(180)
        self.padding = dp(10)
        self.spacing = dp(5)
        self.md_bg_color = (1, 1, 1, 1)
        self.elevation = 2
        self.radius = [10]
        
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title_label = MDLabel(
            text=f"[b]{self.title_text}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(25),
            font_size='14sp',
            font_name=self.target_font
        )
        self.add_widget(title_label)
        
        # Content
        self.content_label = MDLabel(
            text=self.content_text,
            size_hint_y=None,
            font_size='12sp',
            font_name=self.target_font
        )
        self.content_label.bind(texture_size=self.content_label.setter('size'))
        self.add_widget(self.content_label)
        
        # Buttons
        button_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        
        translate_btn = MDRaisedButton(
            text="번역",
            font_size='11sp',
            font_name=self.target_font,
            md_bg_color=(0.2, 0.6, 1, 1),
            on_release=self.toggle_translation
        )
        button_layout.add_widget(translate_btn)
        
        analyze_btn = MDRaisedButton(
            text="단어분석",
            font_size='11sp',
            font_name=self.target_font,
            md_bg_color=(0.9, 0.5, 0.2, 1),
            on_release=self.show_word_analysis
        )
        button_layout.add_widget(analyze_btn)
        
        self.add_widget(button_layout)
        
        # Translation Result Label
        self.translation_label = MDLabel(
            text="",
            size_hint_y=None,
            height=0,
            font_size='12sp',
            font_name=self.target_font,
            markup=True,
            color=(0, 0, 0.8, 1)
        )
        self.add_widget(self.translation_label)
    
    def toggle_translation(self, instance):
        self.show_translation = not self.show_translation
        if self.show_translation:
            self.app.show_loading("번역 중...")
            threading.Thread(target=self._translate, daemon=True).start()
        else:
            self.translation_label.text = ""
            self.translation_label.height = 0
            self.height = dp(180)
    
    def _translate(self):
        try:
            translated = self.app.translate_text(self.content_text)
            Clock.schedule_once(lambda dt: self._show_translation(translated), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            print(f"Translation Error: {e}")
    
    def _show_translation(self, text):
        # Remove [b] tag from label prefix to avoid bold font issues if bold font is missing
        # Or ensure bold font is registered. We registered bold to regular, so it should be fine.
        self.translation_label.text = f"[b]번역:[/b] {text}"
        self.translation_label.height = dp(60)
        self.height = dp(240)
        self.app.hide_loading()
    
    def show_word_analysis(self, instance):
        self.app.show_loading("단어 분석 중...")
        threading.Thread(target=self._analyze_words, daemon=True).start()
    
    def _analyze_words(self):
        try:
            word_info = self.app.analyze_words(self.content_text)
            Clock.schedule_once(lambda dt: self.app.show_word_dialog(word_info), 0)
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_error(f"Analysis Error: {str(e)}"), 0)

class APNewsApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.news_data = []
        self.dialog = None
        self.loading_dialog = None
        self.font_name = 'Roboto'
        
    def build(self):
        self.register_font()
        
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        
        layout = BoxLayout(orientation='vertical')
        
        toolbar = MDTopAppBar(
            title="AP News",
            md_bg_color=(0.2, 0.6, 1, 1),
            right_action_items=[
                ["refresh", self.load_news],
                ["close", self.exit_app]
            ]
        )
        layout.add_widget(toolbar)
        
        scroll = ScrollView()
        self.news_list = GridLayout(
            cols=1,
            spacing=dp(10),
            padding=dp(10),
            size_hint_y=None
        )
        self.news_list.bind(minimum_height=self.news_list.setter('height'))
        scroll.add_widget(self.news_list)
        layout.add_widget(scroll)
        
        Clock.schedule_once(lambda dt: self.load_news(), 0.5)
        return layout
    
    def register_font(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(base_dir, 'NanumGothic.ttf')
            
            if os.path.exists(font_path):
                # IMPORTANT: Register the same font for ALL variants to prevent squares in bold/italic text
                LabelBase.register(
                    name='Korean', 
                    fn_regular=font_path,
                    fn_bold=font_path,
                    fn_italic=font_path,
                    fn_bolditalic=font_path
                )
                self.font_name = 'Korean'
                print(f"✅ Local Font Registered: {font_path}")
                return

            if platform == 'android':
                system_fonts = [
                    '/system/fonts/NanumGothic.ttf',
                    '/system/fonts/DroidSansFallback.ttf',
                    '/system/fonts/NotoSansKR-Regular.otf',
                ]
                for sys_font in system_fonts:
                    if os.path.exists(sys_font):
                        LabelBase.register(
                            name='Korean', 
                            fn_regular=sys_font,
                            fn_bold=sys_font, # Fallback to regular if bold not found
                            fn_italic=sys_font,
                            fn_bolditalic=sys_font
                        )
                        self.font_name = 'Korean'
                        print(f"✅ System Font Registered: {sys_font}")
                        return
            
            self.font_name = 'Roboto'
            
        except Exception as e:
            print(f"❌ Font Registration Error: {e}")
            self.font_name = 'Roboto'

    def on_start(self):
        request_permissions()
    
    def exit_app(self, instance=None):
        if platform == 'android':
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            PythonActivity.mActivity.finish()
        else:
            self.stop()
    
    def load_news(self, instance=None):
        threading.Thread(target=self._fetch_news, daemon=True).start()
    
    def _fetch_news(self):
        try:
            self.news_data = self._get_sample_news()
            try:
                real_news = self._crawl_ap_news()
                if real_news:
                    self.news_data = real_news
            except Exception as e:
                print(f"⚠️ Crawl Error: {e}")
            Clock.schedule_once(lambda dt: self._update_ui(), 0)
        except Exception as e:
            print(f"❌ Load Error: {e}")
    
    def _get_sample_news(self):
        return [
            {'title': 'Sample News 1', 'content': 'Trump says he will meet with Putin very quickly to end Ukraine war'},
            {'title': 'Sample News 2', 'content': 'Stock market rallies as investors await Fed decision on interest rates'},
            {'title': 'Sample News 3', 'content': 'New AI breakthrough promises to revolutionize healthcare industry'}
        ]
    
    def _crawl_ap_news(self):
        try:
            import requests
            from bs4 import BeautifulSoup
            url = "https://apnews.com/"
            headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10)'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            news_list = []
            for i, element in enumerate(soup.select('h2, h3')[:5], 1):
                text = element.get_text(strip=True)
                if len(text) > 20:
                    news_list.append({'title': f'News {i}', 'content': text})
            return news_list if news_list else None
        except: return None
    
    def _update_ui(self):
        self.news_list.clear_widgets()
        for idx, news in enumerate(self.news_data, 1):
            card = NewsCard(
                title=news['title'],
                content=news['content'],
                index=idx,
                app_instance=self,
                font_name=self.font_name
            )
            self.news_list.add_widget(card)
    
    # ========== Translation Logic ==========
    def translate_text(self, text):
        # 1. Try Deep Translator (Google)
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='en', target='ko')
            result = translator.translate(text)
            if result and result != text:
                return result
        except Exception as e:
            print(f"DeepTranslator Error: {e}")
        
        # 2. Try GoogleTrans (Fallback)
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(text, src='en', dest='ko')
            if result and result.text:
                return result.text
        except Exception as e:
            print(f"GoogleTrans Error: {e}")
            
        # 3. Simple Dictionary Fallback
        return self._simple_translate(text)
    
    def _simple_translate(self, text):
        translations = {
            'Trump': '트럼프', 'Putin': '푸틴', 'Ukraine': '우크라이나', 'war': '전쟁',
            'Stock': '주식', 'market': '시장', 'AI': '인공지능', 'healthcare': '의료',
            'says': '말하다', 'will': '할 것이다', 'meet': '만나다', 'with': '와 함께',
            'very': '매우', 'quickly': '빠르게', 'end': '끝내다'
        }
        result = text
        for en, ko in translations.items():
            # Case insensitive replacement for better matching
            pattern = re.compile(re.escape(en), re.IGNORECASE)
            result = pattern.sub(ko, result)
        return result
    
    # ========== Word Analysis Logic ==========
    def analyze_words(self, text):
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        unique_words = sorted(set(words))
        word_info = []
        for word in unique_words[:10]:
            if len(word) > 3:
                word_info.append(self._get_word_info(word))
        return word_info

    def _get_word_info(self, word):
        simple_dict = {
            'trump': '트럼프 (미국 전 대통령)', 'putin': '푸틴 (러시아 대통령)',
            'ukraine': '우크라이나', 'stock': '주식', 'market': '시장',
            'investors': '투자자', 'interest': '이자/관심', 'rates': '비율/금리'
        }
        meaning = simple_dict.get(word, f'{word} (영어 단어)')
        return {'단어': word.capitalize(), '뜻': meaning}
    
    # ========== Dialogs ==========
    def show_loading(self, message):
        try:
            if not self.loading_dialog:
                self.loading_dialog = MDDialog(text=message, size_hint=(0.7, None), height=dp(100))
            else:
                self.loading_dialog.text = message
            self.loading_dialog.open()
        except: pass
    
    def hide_loading(self):
        try:
            if self.loading_dialog: self.loading_dialog.dismiss()
        except: pass
    
    def show_error(self, message):
        try:
            if self.dialog: self.dialog.dismiss()
            self.dialog = MDDialog(title="오류", text=message, buttons=[MDFlatButton(text="확인", on_release=lambda x: self.dialog.dismiss())])
            self.dialog.open()
        except: pass
    
    def show_word_dialog(self, word_info):
        try:
            content_text = "\n\n".join([f"• {info['단어']}\n  {info['뜻']}" for info in word_info])
            if self.dialog: self.dialog.dismiss()
            self.dialog = MDDialog(title="단어 분석 결과", text=content_text, size_hint=(0.9, None), height=dp(400), buttons=[MDFlatButton(text="닫기", on_release=lambda x: self.dialog.dismiss())])
            self.dialog.open()
        except: pass

if __name__ == '__main__':
    try:
        APNewsApp().run()
    except Exception as e:
        print(f"❌ App Error: {e}")
