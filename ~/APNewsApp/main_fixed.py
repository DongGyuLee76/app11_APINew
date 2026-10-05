# main.py - AP News 앱 (경로 수정 및 예외 처리 강화)
# 한글 폰트 경로 문제 해결 및 안정성 강화

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

# 안드로이드 권한 요청
def request_permissions():
    """안드로이드 권한 요청"""
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.ACCESS_NETWORK_STATE])
            print("✅ 권한 요청 완료")
        except Exception as e:
            print(f"⚠️ 권한 오류: {e}")

class NewsCard(MDCard):
    """뉴스 카드"""
    
    def __init__(self, title, content, index, app_instance, font_name='Roboto', **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.content_text = content
        self.index = index
        self.app = app_instance
        self.target_font = font_name # 사용할 폰트 이름
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
        """UI 구성"""
        # 제목
        title_label = MDLabel(
            text=f"[b]{self.title_text}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(25),
            font_size='14sp',
            font_name=self.target_font
        )
        self.add_widget(title_label)
        
        # 내용
        self.content_label = MDLabel(
            text=self.content_text,
            size_hint_y=None,
            font_size='12sp',
            font_name=self.target_font
        )
        self.content_label.bind(texture_size=self.content_label.setter('size'))
        self.add_widget(self.content_label)
        
        # 버튼 레이아웃
        button_layout = BoxLayout(
            size_hint_y=None,
            height=dp(40),
            spacing=dp(5)
        )
        
        # 번역 버튼
        translate_btn = MDRaisedButton(
            text="번역",
            font_size='11sp',
            font_name=self.target_font,
            md_bg_color=(0.2, 0.6, 1, 1),
            on_release=self.toggle_translation
        )
        button_layout.add_widget(translate_btn)
        
        # 단어 분석 버튼
        analyze_btn = MDRaisedButton(
            text="단어분석",
            font_size='11sp',
            font_name=self.target_font,
            md_bg_color=(0.9, 0.5, 0.2, 1),
            on_release=self.show_word_analysis
        )
        button_layout.add_widget(analyze_btn)
        
        self.add_widget(button_layout)
        
        # 번역 결과 라벨
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
    
    def _show_translation(self, text):
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
            Clock.schedule_once(lambda dt: self.app.show_error(f"분석 오류: {str(e)}"), 0)


class APNewsApp(MDApp):
    """메인 앱"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.news_data = []
        self.dialog = None
        self.loading_dialog = None
        self.font_name = 'Roboto' # 기본값
        
    def build(self):
        print("🚀 앱 시작")
        
        # 1. 폰트 등록 로직 개선
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
        
        print("✅ 빌드 완료")
        return layout
    
    def register_font(self):
        """폰트 등록 (절대 경로 및 Fallback 사용)"""
        try:
            # 1. 현재 파일이 있는 디렉토리 기준 절대 경로
            base_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(base_dir, 'NanumGothic.ttf')
            
            print(f"🔎 폰트 탐색 경로: {font_path}")
            
            if os.path.exists(font_path):
                LabelBase.register(name='Korean', fn_regular=font_path)
                self.font_name = 'Korean'
                print(f"✅ 로컬 폰트 등록 성공: {font_path}")
                return

            # 2. 안드로이드 시스템 폰트 Fallback
            if platform == 'android':
                system_fonts = [
                    '/system/fonts/DroidSansFallback.ttf',
                    '/system/fonts/NanumGothic.ttf',
                    '/system/fonts/NotoSansKR-Regular.otf',
                    '/system/fonts/Roboto-Regular.ttf'
                ]
                for sys_font in system_fonts:
                    if os.path.exists(sys_font):
                        LabelBase.register(name='Korean', fn_regular=sys_font)
                        self.font_name = 'Korean'
                        print(f"✅ 시스템 폰트 등록 성공: {sys_font}")
                        return
            
            print("⚠️ 사용 가능한 한글 폰트를 찾지 못했습니다. 기본 폰트를 사용합니다.")
            self.font_name = 'Roboto' # Kivy 기본 폰트
            
        except Exception as e:
            print(f"❌ 폰트 등록 중 치명적 오류: {e}")
            self.font_name = 'Roboto'

    def on_start(self):
        print("🚀 on_start")
        request_permissions()
    
    def exit_app(self, instance=None):
        print("👋 앱 종료")
        if platform == 'android':
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            PythonActivity.mActivity.finish()
        else:
            self.stop()
    
    def load_news(self, instance=None):
        print("📰 뉴스 로드 중")
        threading.Thread(target=self._fetch_news, daemon=True).start()
    
    def _fetch_news(self):
        try:
            self.news_data = self._get_sample_news()
            try:
                real_news = self._crawl_ap_news()
                if real_news:
                    self.news_data = real_news
            except Exception as e:
                print(f"⚠️ 크롤링 실패: {e}")
            
            Clock.schedule_once(lambda dt: self._update_ui(), 0)
        except Exception as e:
            print(f"❌ 뉴스 로드 오류: {e}")
    
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
        except Exception as e:
            print(f"⚠️ 크롤링 오류: {e}")
            return None
    
    def _update_ui(self):
        try:
            self.news_list.clear_widgets()
            for idx, news in enumerate(self.news_data, 1):
                # 여기서 self.font_name을 전달하여 등록된 폰트만 사용하도록 함
                card = NewsCard(
                    title=news['title'],
                    content=news['content'],
                    index=idx,
                    app_instance=self,
                    font_name=self.font_name 
                )
                self.news_list.add_widget(card)
            print(f"✅ UI 업데이트 완료 (폰트: {self.font_name})")
        except Exception as e:
            print(f"❌ UI 업데이트 오류: {e}")
    
    # ========== 번역 기능 ==========
    def translate_text(self, text):
        try:
            try:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='en', target='ko')
                result = translator.translate(text)
                if result: return result
            except: pass
            return self._simple_translate(text)
        except Exception as e:
            print(f"❌ 번역 오류: {e}")
            return "[번역 불가]"
    
    def _simple_translate(self, text):
        translations = {
            'Trump': '트럼프', 'Putin': '푸틴', 'Ukraine': '우크라이나', 'war': '전쟁',
            'Stock': '주식', 'market': '시장', 'AI': '인공지능', 'healthcare': '의료'
        }
        result = text
        for en, ko in translations.items():
            result = result.replace(en, ko)
        return result
    
    # ========== 단어 분석 기능 ==========
    def analyze_words(self, text):
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        unique_words = sorted(set(words))
        word_info = []
        for word in unique_words[:10]:
            if len(word) > 3:
                word_info.append({'단어': word.capitalize(), '뜻': f'{word} (영어 단어)'})
        return word_info
    
    # ========== UI 다이얼로그 ==========
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
        print(f"❌ 앱 오류: {e}")
