# main.py - 안드로이드용 AP News 앱 (안정화 버전)
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.expansionpanel import MDExpansionPanel, MDExpansionPanelOneLine
from kivy.metrics import dp
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.utils import platform

import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import os
from googletrans import Translator
import tempfile
import re
import json
from functools import lru_cache
import threading

# 안드로이드 권한 요청 (개선된 버전)
def request_android_permissions():
    """안드로이드 권한 안전하게 요청"""
    if platform == 'android':
        try:
            from android.permissions import request_permissions, Permission, check_permission
            
            perms = [
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.ACCESS_NETWORK_STATE
            ]
            
            # 권한 체크 후 필요한 권한만 요청
            needed_perms = []
            for perm in perms:
                if not check_permission(perm):
                    needed_perms.append(perm)
            
            if needed_perms:
                request_permissions(needed_perms)
                
        except Exception as e:
            print(f"권한 요청 오류: {e}")

# NLTK 초기화 (안전한 버전)
def init_nltk_safe():
    """안드로이드 환경에서 안전하게 NLTK 초기화"""
    try:
        import nltk
        try:
            nltk.data.find('corpora/wordnet.zip')
        except LookupError:
            # 백그라운드에서 다운로드 시도
            try:
                nltk.download('wordnet', quiet=True)
                nltk.download('omw-1.4', quiet=True)
            except:
                print("NLTK 데이터 다운로드 실패 - WordNet 기능 제한됨")
    except Exception as e:
        print(f"NLTK 초기화 오류: {e}")


class NewsCard(MDCard):
    """각 뉴스 기사를 표시하는 카드"""
    
    def __init__(self, headline, index, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.headline = headline
        self.index = index
        self.app = app_instance
        self.show_translation = False
        self.show_analysis = False
        
        # 카드 스타일
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(200)
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
            text=f"[b]📄 기사 {self.index}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Custom",
            text_color=(0.17, 0.24, 0.31, 1)
        )
        self.add_widget(title_label)
        
        # 기사 내용
        self.content_label = MDLabel(
            text=self.headline,
            size_hint_y=None,
            font_style='Body1',
            theme_text_color="Custom",
            text_color=(0.2, 0.2, 0.2, 1)
        )
        self.content_label.bind(texture_size=self.content_label.setter('size'))
        self.add_widget(self.content_label)
        
        # 버튼 레이아웃
        button_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        # TTS 버튼
        tts_btn = MDRaisedButton(
            text="🔊 읽기",
            md_bg_color=(0.3, 0.7, 0.3, 1),
            on_release=self.play_tts
        )
        button_layout.add_widget(tts_btn)
        
        # 번역 버튼
        trans_btn = MDRaisedButton(
            text="🇰🇷 번역",
            md_bg_color=(0.2, 0.6, 0.9, 1),
            on_release=self.toggle_translation
        )
        button_layout.add_widget(trans_btn)
        
        # 단어 분석 버튼
        analyze_btn = MDRaisedButton(
            text="📚 분석",
            md_bg_color=(0.9, 0.5, 0.2, 1),
            on_release=self.toggle_analysis
        )
        button_layout.add_widget(analyze_btn)
        
        self.add_widget(button_layout)
        
        # 번역 결과 라벨 (초기 숨김)
        self.translation_label = MDLabel(
            text="",
            size_hint_y=None,
            height=0,
            theme_text_color="Secondary",
            markup=True
        )
        self.add_widget(self.translation_label)
    
    def play_tts(self, instance):
        """TTS 재생"""
        self.app.show_loading("음성 생성 중...")
        # 백그라운드 스레드에서 TTS 생성
        threading.Thread(target=self._play_tts_async, daemon=True).start()
    
    def _play_tts_async(self):
        """비동기 TTS 생성 및 재생"""
        try:
            audio_file = self.app.text_to_speech(self.headline, self.index)
            if audio_file and os.path.exists(audio_file):
                # UI 스레드에서 재생
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
                # 재생 완료 후 파일 삭제
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
    
    def toggle_translation(self, instance):
        """번역 토글"""
        self.show_translation = not self.show_translation
        
        if self.show_translation:
            self.app.show_loading("번역 중...")
            # 백그라운드에서 번역
            threading.Thread(target=self._show_translation, daemon=True).start()
        else:
            self.translation_label.text = ""
            self.translation_label.height = 0
            self.height = dp(200)
    
    def _show_translation(self):
        """번역 표시"""
        try:
            translation = self.app.translate_to_korean(self.headline)
            # UI 업데이트는 메인 스레드에서
            Clock.schedule_once(lambda dt: self._update_translation_ui(translation), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_error(f"번역 오류: {str(e)}"), 0)
    
    def _update_translation_ui(self, translation):
        """번역 UI 업데이트"""
        self.translation_label.text = f"[b]한글 번역:[/b] {translation}"
        self.translation_label.height = dp(60)
        self.height = dp(260)
        self.app.hide_loading()
    
    def toggle_analysis(self, instance):
        """단어 분석 토글"""
        self.app.show_loading("단어 분석 중...")
        # 백그라운드에서 분석
        threading.Thread(target=self._show_analysis, daemon=True).start()
    
    def _show_analysis(self):
        """단어 분석 표시"""
        try:
            word_info = self.app.analyze_words(self.headline)
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_analysis_dialog(word_info), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.app.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.app.show_error(f"분석 오류: {str(e)}"), 0)


class APNewsApp(MDApp):
    """메인 앱 클래스"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headlines = []
        self.cache_file = None
        self.dialog = None
        self.loading_dialog = None
        self.translator = None
        self.nltk_available = False
        
    def on_start(self):
        """앱 시작 시 실행"""
        # 안드로이드 권한 요청
        request_android_permissions()
        
        # NLTK 초기화 (백그라운드에서)
        threading.Thread(target=self._init_nltk, daemon=True).start()
    
    def _init_nltk(self):
        """NLTK 초기화"""
        try:
            init_nltk_safe()
            import nltk
            from nltk.corpus import wordnet
            # 테스트
            synsets = wordnet.synsets('test')
            self.nltk_available = True
        except:
            self.nltk_available = False
            print("NLTK 사용 불가 - 단어 분석 기능 제한됨")
        
    def build(self):
        """앱 UI 빌드"""
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.theme_style = "Light"
        
        # 번역기 초기화
        try:
            self.translator = Translator()
        except:
            pass
        
        # 캐시 파일 경로 설정
        if platform == 'android':
            try:
                from android.storage import app_storage_path
                self.cache_file = os.path.join(app_storage_path(), 'news_cache.json')
            except:
                self.cache_file = '/sdcard/news_cache.json'
        else:
            self.cache_file = 'news_cache.json'
        
        # 메인 레이아웃
        main_layout = BoxLayout(orientation='vertical')
        
        # 상단 툴바
        toolbar = MDTopAppBar(
            title="📰 AP News",
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
        
        # 초기 뉴스 로드
        Clock.schedule_once(lambda dt: self.load_news(), 1.0)
        
        return main_layout
    
    def load_news(self):
        """뉴스 로드"""
        self.show_loading("AP News에서 기사를 가져오는 중...")
        # 백그라운드에서 로드
        threading.Thread(target=self._load_news_async, daemon=True).start()
    
    def _load_news_async(self):
        """비동기 뉴스 로드"""
        try:
            # 캐시 확인
            cached_headlines = self.load_cache()
            if cached_headlines:
                self.headlines = cached_headlines
            else:
                self.headlines = self.fetch_ap_news()
                self.save_cache(self.headlines)
            
            # UI 업데이트는 메인 스레드에서
            Clock.schedule_once(lambda dt: self.update_news_ui(), 0)
            Clock.schedule_once(lambda dt: self.hide_loading(), 0)
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self.hide_loading(), 0)
            Clock.schedule_once(lambda dt: self.show_error(f"뉴스 로드 오류: {str(e)}"), 0)
    
    def update_news_ui(self):
        """뉴스 UI 업데이트"""
        self.news_layout.clear_widgets()
        
        if not self.headlines:
            self.headlines = ["뉴스를 불러올 수 없습니다. 새로고침을 시도하세요."]
        
        for idx, headline in enumerate(self.headlines, 1):
            card = NewsCard(headline, idx, self)
            self.news_layout.add_widget(card)
    
    def refresh_news(self):
        """뉴스 새로고침"""
        self.clear_cache()
        self.load_news()
    
    # ========== 핵심 기능 함수 ==========
    
    def fetch_ap_news(self):
        """AP News 크롤링 (개선된 버전)"""
        try:
            url = "https://apnews.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
            }
            
            # 타임아웃 설정
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            headlines = []
            
            selectors = [
                'h2.PagePromo-title',
                'h3.PagePromo-title',
                'span.PagePromoContentIcons-text',
                'div.CardHeadline',
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
            
            return headlines[:10] if headlines else ["기사를 가져올 수 없습니다."]
        
        except requests.exceptions.Timeout:
            return ["네트워크 타임아웃. 인터넷 연결을 확인하세요."]
        except requests.exceptions.ConnectionError:
            return ["인터넷 연결을 확인하세요."]
        except Exception as e:
            return [f"오류: {str(e)}"]
    
    def translate_to_korean(self, text):
        """한글 번역 (개선된 버전)"""
        try:
            if not self.translator:
                self.translator = Translator()
            
            result = self.translator.translate(text, src='en', dest='ko')
            return result.text
        except Exception as e:
            # 번역 실패 시 재시도
            try:
                self.translator = Translator()
                result = self.translator.translate(text, src='en', dest='ko')
                return result.text
            except:
                return f"번역 오류: {str(e)}"
    
    def text_to_speech(self, text, index):
        """TTS 생성"""
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            
            # 안드로이드용 임시 파일
            if platform == 'android':
                try:
                    from android.storage import app_storage_path
                    temp_dir = app_storage_path()
                except:
                    temp_dir = '/sdcard'
            else:
                temp_dir = tempfile.gettempdir()
            
            filepath = os.path.join(temp_dir, f'tts_{index}.mp3')
            tts.save(filepath)
            return filepath
            
        except Exception as e:
            print(f"TTS 생성 오류: {e}")
            return None
    
    def get_pronunciation(self, word):
        """발음기호 조회 (단순화 버전)"""
        # eng-to-ipa는 안드로이드에서 문제가 있을 수 있으므로 단순화
        return f"/{word.lower()}/"
    
    def pos_to_korean(self, pos):
        """품사 한글 변환"""
        pos_dict = {
            'n': '명사', 'v': '동사', 'a': '형용사',
            's': '형용사', 'r': '부사', 'j': '형용사'
        }
        return pos_dict.get(pos, '기타')
    
    def get_word_info(self, word):
        """단어 정보 조회"""
        try:
            if not self.nltk_available:
                # NLTK 없이 기본 번역만
                if not self.translator:
                    self.translator = Translator()
                meaning_kr = self.translator.translate(word, src='en', dest='ko').text
                return meaning_kr, '-'
            
            from nltk.corpus import wordnet
            synsets = wordnet.synsets(word)
            
            if synsets:
                synset = synsets[0]
                definition = synset.definition()
                pos = synset.pos()
                
                if not self.translator:
                    self.translator = Translator()
                meaning_kr = self.translator.translate(definition, src='en', dest='ko').text
                pos_kr = self.pos_to_korean(pos)
                
                return meaning_kr, pos_kr
            else:
                if not self.translator:
                    self.translator = Translator()
                meaning_kr = self.translator.translate(word, src='en', dest='ko').text
                return meaning_kr, '-'
        except Exception as e:
            print(f"단어 정보 조회 오류: {e}")
            return "조회 실패", '-'
    
    def analyze_words(self, sentence):
        """문장 단어 분석"""
        words = re.findall(r'\b[a-zA-Z]+\b', sentence.lower())
        unique_words = sorted(set(words))
        
        word_info = []
        for word in unique_words:
            if len(word) > 2:
                pronunciation = self.get_pronunciation(word)
                meaning, pos = self.get_word_info(word)
                word_info.append({
                    '단어': word.capitalize(),
                    '발음기호': pronunciation,
                    '품사': pos,
                    '뜻': meaning
                })
        
        return word_info
    
    # ========== 캐시 관리 ==========
    
    def save_cache(self, data):
        """캐시 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            print(f"캐시 저장 오류: {e}")
    
    def load_cache(self):
        """캐시 로드"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"캐시 로드 오류: {e}")
        return None
    
    def clear_cache(self):
        """캐시 삭제"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except Exception as e:
            print(f"캐시 삭제 오류: {e}")
    
    # ========== UI 다이얼로그 ==========
    
    def show_loading(self, message):
        """로딩 다이얼로그 표시"""
        if not self.loading_dialog:
            self.loading_dialog = MDDialog(
                text=message,
                size_hint=(0.8, None),
                height=dp(200)
            )
        else:
            self.loading_dialog.text = message
        
        try:
            self.loading_dialog.open()
        except:
            pass
    
    def hide_loading(self):
        """로딩 다이얼로그 숨김"""
        if self.loading_dialog:
            try:
                self.loading_dialog.dismiss()
            except:
                pass
    
    def show_error(self, message):
        """에러 다이얼로그 표시"""
        if self.dialog:
            try:
                self.dialog.dismiss()
            except:
                pass
        
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
        
        try:
            self.dialog.open()
        except:
            pass
    
    def show_analysis_dialog(self, word_info):
        """단어 분석 다이얼로그 표시"""
        if not word_info:
            self.show_error("분석할 단어가 없습니다.")
            return
        
        # 다이얼로그 내용 생성
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        for info in word_info[:20]:  # 최대 20개까지만
            word_card = MDCard(
                orientation='vertical',
                size_hint_y=None,
                height=dp(100),
                padding=dp(10),
                spacing=dp(5),
                elevation=2,
                radius=[10]
            )
            
            word_card.add_widget(MDLabel(
                text=f"[b]{info['단어']}[/b]  {info['발음기호']}",
                markup=True,
                size_hint_y=None,
                height=dp(30)
            ))
            
            word_card.add_widget(MDLabel(
                text=f"[color=0000FF][{info['품사']}][/color]",
                markup=True,
                size_hint_y=None,
                height=dp(25)
            ))
            
            word_card.add_widget(MDLabel(
                text=info['뜻'],
                size_hint_y=None,
                height=dp(35),
                font_style='Caption'
            ))
            
            content.add_widget(word_card)
        
        # 스크롤 뷰로 감싸기
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(content)
        
        # 다이얼로그 생성
        if self.dialog:
            try:
                self.dialog.dismiss()
            except:
                pass
        
        self.dialog = MDDialog(
            title="📖 단어 분석 결과",
            type="custom",
            content_cls=scroll,
            size_hint=(0.9, 0.8),
            buttons=[
                MDFlatButton(
                    text="닫기",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        
        try:
            self.dialog.open()
        except:
            pass


# 앱 실행
if __name__ == '__main__':
    APNewsApp().run()
