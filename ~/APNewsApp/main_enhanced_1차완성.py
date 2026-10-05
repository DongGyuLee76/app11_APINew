# main.py - AP News 앱 (기능 추가 버전)
# 종료 버튼 + 번역 + 단어 분석

from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.dialog import MDDialog
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform

import os
import json
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
    """뉴스 카드 (번역/단어분석 버튼 포함)"""
    
    def __init__(self, title, content, index, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.content_text = content
        self.index = index
        self.app = app_instance
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
            font_size='14sp'
        )
        self.add_widget(title_label)
        
        # 내용
        self.content_label = MDLabel(
            text=self.content_text,
            size_hint_y=None,
            font_size='12sp'
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
            md_bg_color=(0.2, 0.6, 1, 1),
            on_release=self.toggle_translation
        )
        button_layout.add_widget(translate_btn)
        
        # 단어 분석 버튼
        analyze_btn = MDRaisedButton(
            text="단어분석",
            font_size='11sp',
            md_bg_color=(0.9, 0.5, 0.2, 1),
            on_release=self.show_word_analysis
        )
        button_layout.add_widget(analyze_btn)
        
        self.add_widget(button_layout)
        
        # 번역 결과 라벨 (초기 숨김)
        self.translation_label = MDLabel(
            text="",
            size_hint_y=None,
            height=0,
            font_size='12sp',
            markup=True,
            color=(0, 0, 0.8, 1)
        )
        self.add_widget(self.translation_label)
    
    def toggle_translation(self, instance):
        """번역 토글"""
        self.show_translation = not self.show_translation
        
        if self.show_translation:
            self.app.show_loading("번역 중...")
            threading.Thread(target=self._translate, daemon=True).start()
        else:
            self.translation_label.text = ""
            self.translation_label.height = 0
            self.height = dp(180)
    
    def _translate(self):
        """번역 수행"""
        try:
            translated = self.app.translate_text(self.content_text)
            Clock.schedule_once(lambda dt: self._show_translation(translated), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            print(f"⚠️ 번역 오류: {e}")
    
    def _show_translation(self, text):
        """번역 결과 표시"""
        self.translation_label.text = f"[b]번역:[/b] {text}"
        self.translation_label.height = dp(60)
        self.height = dp(240)
        self.app.hide_loading()
    
    def show_word_analysis(self, instance):
        """단어 분석 다이얼로그 표시"""
        self.app.show_loading("단어 분석 중...")
        threading.Thread(target=self._analyze_words, daemon=True).start()
    
    def _analyze_words(self):
        """단어 분석 수행"""
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
        self.translator = None
        
    def build(self):
        """UI 빌드"""
        print("🚀 앱 시작")
        
        # 테마
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        
        # 메인 레이아웃
        layout = BoxLayout(orientation='vertical')
        
        # 툴바 (종료 버튼 추가)
        toolbar = MDTopAppBar(
            title="AP News",
            md_bg_color=(0.2, 0.6, 1, 1),
            right_action_items=[
                ["refresh", self.load_news],
                ["close", self.exit_app]  # 종료 버튼
            ]
        )
        layout.add_widget(toolbar)
        
        # 뉴스 리스트
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
        
        # 초기 데이터 로드
        Clock.schedule_once(lambda dt: self.load_news(), 0.5)
        
        print("✅ 빌드 완료")
        return layout
    
    def on_start(self):
        """앱 시작"""
        print("🚀 on_start")
        request_permissions()
    
    def exit_app(self, instance=None):
        """앱 종료"""
        print("👋 앱 종료")
        if platform == 'android':
            # 안드로이드에서는 액티비티 종료
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            PythonActivity.mActivity.finish()
        else:
            # PC에서는 앱 중지
            self.stop()
    
    def load_news(self, instance=None):
        """뉴스 로드"""
        print("📰 뉴스 로드 중")
        threading.Thread(target=self._fetch_news, daemon=True).start()
    
    def _fetch_news(self):
        """뉴스 가져오기"""
        try:
            # 샘플 데이터 사용
            self.news_data = self._get_sample_news()
            
            # 실제 크롤링 시도
            try:
                real_news = self._crawl_ap_news()
                if real_news:
                    self.news_data = real_news
            except Exception as e:
                print(f"⚠️ 크롤링 실패, 샘플 사용: {e}")
            
            Clock.schedule_once(lambda dt: self._update_ui(), 0)
            
        except Exception as e:
            print(f"❌ 뉴스 로드 오류: {e}")
    
    def _get_sample_news(self):
        """샘플 뉴스 데이터"""
        return [
            {
                'title': 'Sample News 1',
                'content': 'Trump says he will meet with Putin very quickly to end Ukraine war'
            },
            {
                'title': 'Sample News 2', 
                'content': 'Stock market rallies as investors await Fed decision on interest rates'
            },
            {
                'title': 'Sample News 3',
                'content': 'New AI breakthrough promises to revolutionize healthcare industry'
            },
            {
                'title': 'Sample News 4',
                'content': 'Climate conference reaches historic agreement on carbon emissions'
            },
            {
                'title': 'Sample News 5',
                'content': 'Tech giant announces major layoffs affecting thousands of employees'
            }
        ]
    
    def _crawl_ap_news(self):
        """실제 AP News 크롤링"""
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
                    news_list.append({
                        'title': f'News {i}',
                        'content': text
                    })
            
            return news_list if news_list else None
            
        except Exception as e:
            print(f"⚠️ 크롤링 오류: {e}")
            return None
    
    def _update_ui(self):
        """UI 업데이트"""
        try:
            self.news_list.clear_widgets()
            
            for idx, news in enumerate(self.news_data, 1):
                card = NewsCard(
                    title=news['title'],
                    content=news['content'],
                    index=idx,
                    app_instance=self
                )
                self.news_list.add_widget(card)
            
            print(f"✅ UI 업데이트: {len(self.news_data)}개")
            
        except Exception as e:
            print(f"❌ UI 업데이트 오류: {e}")
    
    # ========== 번역 기능 ==========
    
    def translate_text(self, text):
        """텍스트 번역 (간단한 사전 기반)"""
        try:
            # deep-translator 시도 (googletrans 대신)
            try:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='en', target='ko')
                return translator.translate(text)
            except:
                pass
            
            # 간단한 단어 사전 (fallback)
            simple_dict = {
                'Trump': '트럼프',
                'Putin': '푸틴',
                'Ukraine': '우크라이나',
                'war': '전쟁',
                'Stock': '주식',
                'market': '시장',
                'AI': '인공지능',
                'healthcare': '의료',
                'Climate': '기후',
                'Tech': '기술',
                'giant': '거대',
            }
            
            result = text
            for en, ko in simple_dict.items():
                result = result.replace(en, ko)
            
            return result
            
        except Exception as e:
            print(f"⚠️ 번역 오류: {e}")
            return f"[번역 불가: {text[:30]}...]"
    
    # ========== 단어 분석 기능 ==========
    
    def analyze_words(self, text):
        """단어 분석"""
        try:
            # 단어 추출
            words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
            unique_words = sorted(set(words))
            
            word_info = []
            for word in unique_words[:10]:  # 상위 10개만
                if len(word) > 3:  # 3글자 이상만
                    info = self._get_word_info(word)
                    word_info.append(info)
            
            return word_info
            
        except Exception as e:
            print(f"❌ 단어 분석 오류: {e}")
            return []
    
    def _get_word_info(self, word):
        """개별 단어 정보 조회"""
        try:
            # NLTK 시도 (설치되어 있으면)
            try:
                from nltk.corpus import wordnet
                synsets = wordnet.synsets(word)
                if synsets:
                    definition = synsets[0].definition()
                    return {
                        '단어': word.capitalize(),
                        '뜻': definition[:50] + '...' if len(definition) > 50 else definition
                    }
            except:
                pass
            
            # 간단한 사전 (fallback)
            simple_dict = {
                'trump': '트럼프 (미국 정치인)',
                'putin': '푸틴 (러시아 대통령)',
                'ukraine': '우크라이나 (동유럽 국가)',
                'stock': '주식 (증권)',
                'market': '시장',
                'climate': '기후',
                'tech': '기술',
            }
            
            meaning = simple_dict.get(word, f'{word} (영어 단어)')
            
            return {
                '단어': word.capitalize(),
                '뜻': meaning
            }
            
        except Exception as e:
            return {
                '단어': word.capitalize(),
                '뜻': '정보 없음'
            }
    
    # ========== UI 다이얼로그 ==========
    
    def show_loading(self, message):
        """로딩 다이얼로그"""
        try:
            if not self.loading_dialog:
                self.loading_dialog = MDDialog(
                    text=message,
                    size_hint=(0.7, None),
                    height=dp(100)
                )
            else:
                self.loading_dialog.text = message
            self.loading_dialog.open()
        except Exception as e:
            print(f"⚠️ 로딩 다이얼로그 오류: {e}")
    
    def hide_loading(self):
        """로딩 다이얼로그 숨김"""
        try:
            if self.loading_dialog:
                self.loading_dialog.dismiss()
        except Exception as e:
            print(f"⚠️ 로딩 숨김 오류: {e}")
    
    def show_error(self, message):
        """에러 다이얼로그"""
        try:
            if self.dialog:
                self.dialog.dismiss()
            
            self.dialog = MDDialog(
                title="오류",
                text=message,
                buttons=[
                    MDFlatButton(
                        text="확인",
                        on_release=lambda x: self.dialog.dismiss()
                    )
                ]
            )
            self.dialog.open()
        except Exception as e:
            print(f"⚠️ 에러 다이얼로그 오류: {e}")
    
    def show_word_dialog(self, word_info):
        """단어 분석 다이얼로그"""
        try:
            if not word_info:
                self.show_error("분석할 단어가 없습니다")
                return
            
            # 단어 정보를 텍스트로 변환
            content_text = "\n\n".join([
                f"• {info['단어']}\n  {info['뜻']}"
                for info in word_info
            ])
            
            if self.dialog:
                self.dialog.dismiss()
            
            self.dialog = MDDialog(
                title="단어 분석 결과",
                text=content_text,
                size_hint=(0.9, None),
                height=dp(400),
                buttons=[
                    MDFlatButton(
                        text="닫기",
                        on_release=lambda x: self.dialog.dismiss()
                    )
                ]
            )
            self.dialog.open()
            
        except Exception as e:
            print(f"❌ 단어 다이얼로그 오류: {e}")


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 AP News App 시작 (v2.1 - 기능 추가)")
    print("=" * 50)
    try:
        APNewsApp().run()
    except Exception as e:
        print(f"❌ 앱 오류: {e}")
        import traceback
        traceback.print_exc()
