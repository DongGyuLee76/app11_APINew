# main.py - 안드로이드용 AP News 앱 (최종 안정화 버전 v3.0)
# 한글 폰트 지원 + googletrans 제거

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
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase

import os
import json
import threading
import tempfile

# 안드로이드 권한 요청
def request_android_permissions():
    """안드로이드 권한 안전하게 요청"""
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE
            ])
            print("✅ Android 권한 요청 완료")
        except Exception as e:
            print(f"⚠️ 권한 요청 오류 (무시): {e}")


class NewsCard(MDCard):
    """각 뉴스 기사를 표시하는 카드"""
    
    def __init__(self, headline, index, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.headline = headline
        self.index = index
        self.app = app_instance
        
        # 카드 스타일
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(150)
        self.padding = dp(15)
        self.spacing = dp(10)
        self.md_bg_color = (0.98, 0.98, 0.98, 1)
        self.elevation = 3
        self.radius = [15]
        
        # 레이아웃 구성
        self.setup_ui()
    
    def setup_ui(self):
        """UI 구성"""
        # 제목 라벨
        title_label = MDLabel(
            text=f"[b]기사 {self.index}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(30),
            font_name='NanumGothic',  # 한글 폰트
            theme_text_color="Custom",
            text_color=(0.17, 0.24, 0.31, 1)
        )
        self.add_widget(title_label)
        
        # 기사 내용
        self.content_label = MDLabel(
            text=self.headline,
            size_hint_y=None,
            font_name='NanumGothic',  # 한글 폰트
            font_style='Body1',
            theme_text_color="Custom",
            text_color=(0.2, 0.2, 0.2, 1)
        )
        self.content_label.bind(texture_size=self.content_label.setter('size'))
        self.add_widget(self.content_label)
        
        # TTS 버튼만 표시
        button_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        # TTS 버튼
        tts_btn = MDRaisedButton(
            text="소리내어 읽기",
            font_name='NanumGothic',  # 한글 폰트
            md_bg_color=(0.3, 0.7, 0.3, 1),
            on_release=self.play_tts
        )
        button_layout.add_widget(tts_btn)
        
        self.add_widget(button_layout)
    
    def play_tts(self, instance):
        """TTS 재생"""
        self.app.show_loading("음성 생성 중...")
        threading.Thread(target=self._play_tts_async, daemon=True).start()
    
    def _play_tts_async(self):
        """비동기 TTS 생성 및 재생"""
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
        """오디오 파일 재생"""
        try:
            sound = SoundLoader.load(audio_file)
            if sound:
                sound.play()
                Clock.schedule_once(
                    lambda dt: self._cleanup_audio(audio_file), 
                    sound.length + 1
                )
            self.app.hide_loading()
        except Exception as e:
            self.app.hide_loading()
            self.app.show_error(f"재생 오류: {str(e)}")
    
    def _cleanup_audio(self, filepath):
        """오디오 파일 삭제"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except:
            pass


class APNewsApp(MDApp):
    """메인 앱 클래스"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headlines = []
        self.cache_file = None
        self.dialog = None
        self.loading_dialog = None
        
    def build(self):
        """앱 UI 빌드"""
        print("🚀 APNewsApp build() 시작")
        
        # 한글 폰트 등록
        try:
            # 나눔고딕 폰트 등록 (assets 폴더에 있어야 함)
            font_path = self.get_font_path()
            if font_path and os.path.exists(font_path):
                LabelBase.register(
                    name='NanumGothic',
                    fn_regular=font_path
                )
                print(f"✅ 한글 폰트 등록: {font_path}")
            else:
                print("⚠️ 한글 폰트 파일 없음 - 기본 폰트 사용")
        except Exception as e:
            print(f"⚠️ 폰트 등록 실패: {e}")
        
        try:
            self.theme_cls.primary_palette = "Green"
            self.theme_cls.theme_style = "Light"
            # 기본 폰트 설정
            self.theme_cls.font_styles["Body1"] = ["NanumGothic", 14, False, 0.15]
            print("✅ 테마 설정 완료")
        except Exception as e:
            print(f"⚠️ 테마 설정 실패: {e}")
        
        # 캐시 파일 경로 설정
        try:
            if platform == 'android':
                try:
                    from android.storage import app_storage_path
                    cache_dir = app_storage_path()
                    self.cache_file = os.path.join(cache_dir, 'news_cache.json')
                    print(f"✅ 캐시 경로: {self.cache_file}")
                except Exception as e:
                    self.cache_file = 'news_cache.json'
                    print(f"⚠️ 기본 캐시 경로 사용: {e}")
            else:
                self.cache_file = 'news_cache.json'
        except Exception as e:
            self.cache_file = 'news_cache.json'
            print(f"⚠️ 캐시 경로 설정 오류: {e}")
        
        # 메인 레이아웃
        try:
            main_layout = BoxLayout(orientation='vertical')
            
            # 상단 툴바
            toolbar = MDTopAppBar(
                title="AP 뉴스",
                md_bg_color=(0.3, 0.7, 0.3, 1),
                right_action_items=[["refresh", lambda x: self.refresh_news()]]
            )
            main_layout.add_widget(toolbar)
            
            # 스크롤 가능한 뉴스 리스트
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
            
            print("✅ UI 레이아웃 생성 완료")
            
            # 초기 뉴스 로드
            Clock.schedule_once(lambda dt: self.load_news(), 1.5)
            
            print("✅ build() 완료")
            return main_layout
            
        except Exception as e:
            print(f"❌ build() 오류: {e}")
            import traceback
            traceback.print_exc()
            return MDLabel(text=f"앱 초기화 오류:\n{str(e)}")
    
    def get_font_path(self):
        """한글 폰트 파일 경로 반환"""
        # 여러 가능한 경로 확인
        possible_paths = [
            'NanumGothic.ttf',
            'assets/NanumGothic.ttf',
            'fonts/NanumGothic.ttf',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 안드로이드에서는 시스템 폰트 사용 시도
        if platform == 'android':
            system_fonts = [
                '/system/fonts/NanumGothic.ttf',
                '/system/fonts/DroidSansFallback.ttf',  # 안드로이드 기본 한글 폰트
            ]
            for path in system_fonts:
                if os.path.exists(path):
                    return path
        
        return None
    
    def on_start(self):
        """앱 시작 시 실행"""
        print("🚀 on_start() 시작")
        
        try:
            request_android_permissions()
        except Exception as e:
            print(f"⚠️ 권한 요청 오류: {e}")
        
        print("✅ on_start() 완료")
    
    def load_news(self):
        """뉴스 로드"""
        print("📰 load_news() 시작")
        self.show_loading("AP News에서 기사를 가져오는 중...")
        threading.Thread(target=self._load_news_async, daemon=True).start()
    
    def _load_news_async(self):
        """비동기 뉴스 로드"""
        try:
            print("📡 뉴스 로드 시작")
            
            # 캐시 확인
            cached_headlines = self.load_cache()
            if cached_headlines:
                print(f"✅ 캐시에서 {len(cached_headlines)}개 기사 로드")
                self.headlines = cached_headlines
            else:
                print("🌐 AP News 크롤링 시작")
                self.headlines = self.fetch_ap_news()
                self.save_cache(self.headlines)
            
            # UI 업데이트
            Clock.schedule_once(lambda dt: self.update_news_ui(), 0)
            Clock.schedule_once(lambda dt: self.hide_loading(), 0)
            
        except Exception as e:
            print(f"❌ 뉴스 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.show_error(f"뉴스 로드 오류:\n{str(e)}"), 0)
    
    def update_news_ui(self):
        """뉴스 UI 업데이트"""
        try:
            self.news_layout.clear_widgets()
            
            if not self.headlines:
                self.headlines = ["뉴스를 불러올 수 없습니다. 새로고침을 시도하세요."]
            
            for idx, headline in enumerate(self.headlines, 1):
                card = NewsCard(headline, idx, self)
                self.news_layout.add_widget(card)
            
            print(f"✅ UI 업데이트 완료: {len(self.headlines)}개 기사")
        except Exception as e:
            print(f"❌ UI 업데이트 오류: {e}")
    
    def refresh_news(self):
        """뉴스 새로고침"""
        self.clear_cache()
        self.load_news()
    
    # ========== 핵심 기능 함수 ==========
    
    def fetch_ap_news(self):
        """AP News 크롤링"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            url = "https://apnews.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            headlines = []
            
            selectors = ['h2.PagePromo-title', 'h3.PagePromo-title', 'h2', 'h3']
            
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
            
            print(f"✅ {len(headlines)}개 기사 크롤링 완료")
            return headlines[:10] if headlines else ["기사를 가져올 수 없습니다."]
        
        except Exception as e:
            print(f"❌ 크롤링 오류: {e}")
            return [f"네트워크 오류: {str(e)[:50]}"]
    
    def text_to_speech(self, text, index):
        """TTS 생성"""
        try:
            from gtts import gTTS
            
            tts = gTTS(text=text, lang='en', slow=False)
            
            if platform == 'android':
                try:
                    from android.storage import app_storage_path
                    temp_dir = app_storage_path()
                except:
                    temp_dir = '.'
            else:
                temp_dir = tempfile.gettempdir()
            
            filepath = os.path.join(temp_dir, f'tts_{index}.mp3')
            tts.save(filepath)
            print(f"✅ TTS 생성: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ TTS 오류: {e}")
            return None
    
    # ========== 캐시 관리 ==========
    
    def save_cache(self, data):
        """캐시 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"✅ 캐시 저장: {len(data)}개 항목")
        except Exception as e:
            print(f"⚠️ 캐시 저장 실패: {e}")
    
    def load_cache(self):
        """캐시 로드"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
        except Exception as e:
            print(f"⚠️ 캐시 로드 실패: {e}")
        return None
    
    def clear_cache(self):
        """캐시 삭제"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                print("✅ 캐시 삭제 완료")
        except Exception as e:
            print(f"⚠️ 캐시 삭제 실패: {e}")
    
    # ========== UI 다이얼로그 ==========
    
    def show_loading(self, message):
        """로딩 다이얼로그 표시"""
        try:
            if not self.loading_dialog:
                self.loading_dialog = MDDialog(
                    text=message,
                    size_hint=(0.8, None),
                    height=dp(200)
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
            print(f"⚠️ 로딩 다이얼로그 닫기 오류: {e}")
    
    def show_error(self, message):
        """에러 다이얼로그 표시"""
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


# 앱 실행
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 AP News App 시작 (v3.0)")
    print("=" * 50)
    try:
        APNewsApp().run()
    except Exception as e:
        print(f"❌ 앱 실행 오류: {e}")
        import traceback
        traceback.print_exc()
