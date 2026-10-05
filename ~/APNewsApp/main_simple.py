# main.py - AP News 앱 (완전히 새로 작성 - 안정화 버전)
# 최소한의 의존성, 최대한의 안정성

from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.text import LabelBase

import os
import json
import threading

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


class SimpleNewsCard(MDCard):
    """간단한 뉴스 카드"""
    
    def __init__(self, title, content, index, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(120)
        self.padding = dp(10)
        self.spacing = dp(5)
        self.md_bg_color = (1, 1, 1, 1)
        self.elevation = 2
        self.radius = [10]
        
        # 제목
        title_label = MDLabel(
            text=f"[b]{title}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(25),
            font_size='14sp'
        )
        self.add_widget(title_label)
        
        # 내용
        content_label = MDLabel(
            text=content,
            size_hint_y=None,
            height=dp(60),
            font_size='12sp'
        )
        self.add_widget(content_label)


class APNewsApp(MDApp):
    """메인 앱"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.news_data = []
        
    def build(self):
        """UI 빌드"""
        print("🚀 앱 시작")
        
        # 테마
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        
        # 메인 레이아웃
        layout = BoxLayout(orientation='vertical')
        
        # 툴바
        toolbar = MDTopAppBar(
            title="AP News",
            md_bg_color=(0.2, 0.6, 1, 1),
            right_action_items=[["refresh", self.load_news]]
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
    
    def load_news(self, instance=None):
        """뉴스 로드"""
        print("📰 뉴스 로드 중")
        threading.Thread(target=self._fetch_news, daemon=True).start()
    
    def _fetch_news(self):
        """뉴스 가져오기"""
        try:
            # 일단 샘플 데이터 사용
            self.news_data = self._get_sample_news()
            
            # 실제 크롤링 시도 (실패해도 샘플 사용)
            try:
                real_news = self._crawl_ap_news()
                if real_news:
                    self.news_data = real_news
            except Exception as e:
                print(f"⚠️ 크롤링 실패, 샘플 사용: {e}")
            
            Clock.schedule_once(lambda dt: self._update_ui(), 0)
            
        except Exception as e:
            print(f"❌ 뉴스 로드 오류: {e}")
            import traceback
            traceback.print_exc()
    
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
                card = SimpleNewsCard(
                    title=news['title'],
                    content=news['content'],
                    index=idx
                )
                self.news_list.add_widget(card)
            
            print(f"✅ UI 업데이트: {len(self.news_data)}개")
            
        except Exception as e:
            print(f"❌ UI 업데이트 오류: {e}")


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 AP News App 시작")
    print("=" * 50)
    try:
        APNewsApp().run()
    except Exception as e:
        print(f"❌ 앱 오류: {e}")
        import traceback
        traceback.print_exc()
