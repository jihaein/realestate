import sys
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QTextBrowser, QSplitter,
    QLineEdit, QPushButton, QHBoxLayout, QComboBox, QFileDialog, QLabel, QTextEdit, QMessageBox, QCheckBox,
    QTabWidget, QInputDialog
)
import os
from PySide6.QtCore import Qt
import datetime
import json
import subprocess
import numpy as np
import requests
from openai import OpenAI
from dotenv import load_dotenv
import time
import pickle
import importlib.util
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = os.path.abspath(".")
    if hasattr(sys, '_MEIPASS'):  # PyInstaller creates a temp folder
        base_path = sys._MEIPASS
    return os.path.join(base_path, relative_path)

def prompt_for_naver_credentials(env_path):
    from PySide6.QtWidgets import QApplication, QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QLabel
    import sys
    class NaverCredDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('네이버 로그인 정보 입력')
            self.naver_id = ''
            self.naver_pw = ''
            layout = QVBoxLayout()
            form = QFormLayout()
            self.id_input = QLineEdit()
            self.pw_input = QLineEdit()
            self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow('네이버 아이디:', self.id_input)
            form.addRow('네이버 비밀번호:', self.pw_input)
            layout.addLayout(form)
            self.info_label = QLabel('네이버 아이디와 비밀번호를 입력하세요. (이 정보는 이 컴퓨터의 .env 파일에 저장됩니다)')
            layout.addWidget(self.info_label)
            btn = QPushButton('저장')
            btn.clicked.connect(self.accept)
            layout.addWidget(btn)
            self.setLayout(layout)
        def accept(self):
            self.naver_id = self.id_input.text().strip()
            self.naver_pw = self.pw_input.text().strip()
            if not self.naver_id or not self.naver_pw:
                self.info_label.setText('모든 정보를 입력해야 합니다.')
                return
            super().accept()
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = NaverCredDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        naver_id = dialog.naver_id
        naver_pw = dialog.naver_pw
        # Save to .env
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        # Remove old NAVER_ID/PW lines
        lines = [l for l in lines if not l.startswith('NAVER_ID=') and not l.startswith('NAVER_PW=')]
        lines.append(f'NAVER_ID={naver_id}\n')
        lines.append(f'NAVER_PW={naver_pw}\n')
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        # Reload env vars
        os.environ['NAVER_ID'] = naver_id
        os.environ['NAVER_PW'] = naver_pw
        return naver_id, naver_pw
    else:
        return None, None

# Load environment variables from .env file
env_path = get_resource_path('.env')
print(f"Looking for .env at: {env_path}")  # Debug print
load_dotenv(env_path)

def get_naver_auth_and_cookies():
    naver_id = os.getenv('NAVER_ID')
    naver_pw = os.getenv('NAVER_PW')
    if not naver_id or not naver_pw:
        print("환경변수 NAVER_ID, NAVER_PW가 필요합니다.")
        return None, None

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    # Use a generic user-agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

    # OS-specific Chrome path logic
    if sys.platform == 'darwin':  # macOS
        chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
        else:
            print("Chrome 브라우저를 찾을 수 없습니다. Chrome이 설치되어 있는지 확인해주세요. (macOS)")
            return None, None
    elif sys.platform.startswith('win'):
        # On Windows, do not set binary_location; ChromeDriverManager should find Chrome
        pass
    else:
        print(f"이 운영체제({sys.platform})에서는 Chrome 브라우저 경로를 자동으로 설정하지 않습니다. Chrome이 설치되어 있고 PATH에 등록되어 있어야 합니다.")
        # Optionally, you could add Linux logic here

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10)

        print("네이버 로그인 페이지로 이동 중...")
        # Navigate to Naver login
        driver.get('https://nid.naver.com/nidlogin.login')
        time.sleep(2)  # Short pause for page load

        print("로그인 시도 중...")
        # Execute JavaScript to bypass bot detection
        driver.execute_script(
            f"document.getElementById('id').value='{naver_id}';"
            f"document.getElementById('pw').value='{naver_pw}';"
        )
        time.sleep(1)

        # Click login button
        login_button = wait.until(EC.element_to_be_clickable((By.ID, 'log.login')))
        login_button.click()
        time.sleep(3)  # Wait for login to complete

        print("네이버 부동산으로 이동 중...")
        # Navigate to Naver Land
        driver.get('https://land.naver.com/')
        time.sleep(2)

        print("인증 정보 추출 중...")
        # Navigate to a property detail page to trigger authorization
        driver.get('https://new.land.naver.com/complexes/142817?articleNo=2324123456')
        time.sleep(3)

        # Extract authorization token
        auth_token = None
        auth_headers = {}
        for request in driver.requests:
            if request.url and 'land.naver.com/api' in request.url:
                if request.headers:
                    print(f"Found API request headers: {request.headers}")
                    auth_headers = request.headers
                    if 'authorization' in request.headers:
                        auth_token = request.headers['authorization']
                        print(f"Found auth token: {auth_token}")
                        break

        if not auth_token and auth_headers:
            print("Warning: Could not find 'authorization' in headers. Available headers:", auth_headers)

        # Extract cookies
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        print(f"Extracted cookies: {cookies}")
        
        if not auth_token or not cookies:
            print("인증 토큰 또는 쿠키를 추출하지 못했습니다.")
            return None, None

        print("인증 정보 추출 완료!")
        return auth_token, cookies

    except Exception as e:
        print(f"네이버 자동 로그인/토큰 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        try:
            driver.quit()
        except:
            pass

class RealEstateViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("부동산 매물 리스트 뷰어 (CSV)")
        self.resize(1200, 700)

        # Try to get authentication automatically
        print("네이버 인증 정보를 가져오는 중...")
        self.naver_auth, self.naver_cookies = get_naver_auth_and_cookies()
        
        if not self.naver_auth or not self.naver_cookies:
            raise RuntimeError("네이버 인증정보를 자동으로 가져오지 못했습니다. 환경변수 NAVER_ID, NAVER_PW를 확인하세요.")

        print(f"Authentication successful. Token: {self.naver_auth}")
        print(f"Cookies: {self.naver_cookies}")

        self.data = self.load_data()
        self.notes = self.load_notes()
        self.saved_items = self.load_saved_items()
        self.current_article = None  # 현재 선택된 매물 정보 저장
        self.article_details_cache = self.load_cache()  # 캐시 로드
        self.description_cache = self.load_description_cache()  # GPT 설명 캐시 로드
        self.last_api_call = 0  # API 호출 시간 제한을 위한 변수
        
        # OpenAI API 키가 있는 경우에만 클라이언트 초기화
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"OpenAI 클라이언트 초기화 실패: {e}")
        
        self.init_ui()

    def load_data(self):
        csv_path = get_resource_path('songdo_apartments_listings.csv')
        df = pd.read_csv(csv_path, dtype=str)
        return df.fillna("").to_dict(orient="records")

    def load_notes(self):
        try:
            notes_path = get_resource_path('property_notes.json')
            with open(notes_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def load_saved_items(self):
        try:
            saved_items_path = get_resource_path('saved_properties.json')
            with open(saved_items_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def load_cache(self):
        """파일에서 API 응답 캐시를 로드합니다."""
        try:
            cache_path = get_resource_path('api_cache.pkl')
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except (FileNotFoundError, pickle.UnpicklingError):
            return {}

    def save_cache(self):
        """API 응답 캐시를 파일에 저장합니다."""
        try:
            cache_path = get_resource_path('api_cache.pkl')
            with open(cache_path, 'wb') as f:
                pickle.dump(self.article_details_cache, f)
        except Exception as e:
            print(f"캐시 저장 중 오류 발생: {e}")

    def load_description_cache(self):
        """GPT 설명 캐시를 로드합니다."""
        try:
            desc_cache_path = get_resource_path('description_cache.json')
            with open(desc_cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_description_cache(self):
        """GPT 설명 캐시를 저장합니다."""
        try:
            desc_cache_path = get_resource_path('description_cache.json')
            with open(desc_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.description_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"GPT 설명 캐시 저장 중 오류 발생: {e}")

    def save_note(self):
        if not hasattr(self, 'current_article_no'):
            return
        note_text = self.note_input.toPlainText().strip()
        notes_path = get_resource_path('property_notes.json')
        if note_text:
            self.notes[self.current_article_no] = note_text
        elif self.current_article_no in self.notes:
            del self.notes[self.current_article_no]
        
        with open(notes_path, 'w', encoding='utf-8') as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def save_to_saved_items(self, article_no, row):
        if article_no not in self.saved_items:
            self.saved_items.append(article_no)
        else:
            self.saved_items.remove(article_no)
            
        # 파일 저장
        saved_items_path = get_resource_path('saved_properties.json')
        with open(saved_items_path, 'w', encoding='utf-8') as f:
            json.dump(self.saved_items, f, ensure_ascii=False, indent=2)
        
        # 체크박스 상태만 업데이트
        self.create_save_checkbox(row, article_no)

    def get_last_update(self):
        try:
            last_update_path = get_resource_path('last_update.txt')
            with open(last_update_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return "알 수 없음"

    def get_article_detail(self, article_no):
        """매물 상세 정보를 가져옵니다."""
        if not article_no:
            return None
            
        # Check cache first
        if article_no in self.article_details_cache:
            return self.article_details_cache[article_no]
            
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_api_call < 1.0:  # 1초 간격
            time.sleep(1.0 - (current_time - self.last_api_call))
        self.last_api_call = time.time()
        
        try:
            url = f"https://new.land.naver.com/api/articles/{article_no}?complexNo="
            headers = {
                'Authorization': self.naver_auth,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'Host': 'new.land.naver.com',
                'Referer': 'https://new.land.naver.com/',
                'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            response = requests.get(
                url,
                headers=headers,
                cookies=self.naver_cookies,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.article_details_cache[article_no] = data
                self.save_cache()  # 캐시 저장
                return data
            else:
                print(f"API 요청 실패 - Status: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"매물 상세 정보 조회 중 오류 발생: {e}")
            return None

    def format_description_with_gpt(self, description, article_no):
        """ChatGPT를 사용하여 매물 설명을 포맷팅합니다."""
        # 캐시된 설명이 있으면 반환
        if article_no in self.description_cache:
            return self.description_cache[article_no]

        # OpenAI 클라이언트가 없으면 원본 설명 반환
        if not self.client:
            return description

        try:
            prompt = f"""
            아래 부동산 매물 설명을 읽기 쉽게 정리해주세요:
            1. 중요 정보를 카테고리별로 구분해주세요 (위치, 특징, 가격 정보 등)
            2. 불필요한 반복이나 과도한 홍보성 문구는 제거해주세요
            3. 이모지는 적절히 유지하되, 과도한 사용은 정리해주세요
            4. 연락처 정보는 마지막에 한 번만 표시해주세요
            5. 결과는 명확한 섹션으로 구분하고 깔끔하게 포맷팅해주세요

            매물 설명:
            {description}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "부동산 매물 설명을 깔끔하게 정리하는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            
            formatted_description = response.choices[0].message.content
            # 캐시에 저장
            self.description_cache[article_no] = formatted_description
            self.save_description_cache()
            return formatted_description

        except Exception as e:
            print(f"GPT 포맷팅 에러: {e}")
            return description

    def refresh_last_update(self):
        self.last_update_label.setText(f"마지막 업데이트: {self.get_last_update()}")
        font = self.last_update_label.font()
        font.setPointSize(9)  # Smaller font size
        self.last_update_label.setFont(font)
        self.last_update_label.setStyleSheet("color: gray; margin-bottom: 2px;")

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Top bar with last update and update button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch to push everything to the right
        top_bar.addStretch(1)
        
        # Last update label
        self.last_update_label = QLabel(f"마지막 업데이트: {self.get_last_update()}")
        font = self.last_update_label.font()
        font.setPointSize(9)
        self.last_update_label.setFont(font)
        self.last_update_label.setStyleSheet("color: gray; margin-bottom: 0px; margin-top: 0px; padding: 0px;")
        top_bar.addWidget(self.last_update_label)
        
        # Add small spacing between label and button
        top_bar.addSpacing(5)
        
        # Update button (now next to the label)
        self.update_button = QPushButton("데이터 업데이트")
        self.update_button.clicked.connect(self.update_data)
        self.update_button.setFixedWidth(100)  # Set fixed width
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #C5C5C5;
                color: #3B3B3B;
                padding: 3px;
                border: none;
                border-radius: 2px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #979797;
                color: white;
            }
        """)
        top_bar.addWidget(self.update_button)
        
        main_layout.addLayout(top_bar)

        # 검색/필터/정렬/엑셀 UI
        search_layout = QHBoxLayout()
        
        # 매물번호 검색 추가
        article_no_label = QLabel("매물번호:")
        article_no_label.setFixedWidth(60)
        search_layout.addWidget(article_no_label)
        
        self.article_no_input = QLineEdit()
        self.article_no_input.setPlaceholderText("매물번호 입력")
        self.article_no_input.setFixedWidth(120)
        self.article_no_input.returnPressed.connect(self.search_articles)  # Enter 키로 검색
        search_layout.addWidget(self.article_no_input)
        
        # 아파트 단지 선택 콤보박스 추가
        complex_label = QLabel("단지:")
        complex_label.setFixedWidth(30)  # 레이블 너비 고정
        search_layout.addWidget(complex_label)
        self.complex_combo = QComboBox()
        self.complex_combo.addItem("전체 단지")
        complex_names = sorted(list(set(d.get("complexName", "") for d in self.data)))
        self.complex_combo.addItems(complex_names)
        search_layout.addWidget(self.complex_combo)
        
        # 동 선택 콤보박스 추가
        dong_label = QLabel("동:")
        dong_label.setFixedWidth(20)  # 레이블 너비 고정
        search_layout.addWidget(dong_label)
        self.dong_combo = QComboBox()
        self.dong_combo.addItem("전체 동")
        search_layout.addWidget(self.dong_combo)
        
        # 거래유형 콤보박스 추가
        trade_type_label = QLabel("거래유형:")
        trade_type_label.setFixedWidth(50)  # 레이블 너비 고정
        search_layout.addWidget(trade_type_label)
        self.trade_type_combo = QComboBox()
        self.trade_type_combo.addItem("전체")
        self.trade_type_combo.addItem("전세")
        self.trade_type_combo.addItem("월세")
        self.trade_type_combo.addItem("매매")
        # 정렬 콤보박스 추가
        self.sort_target_combo = QComboBox()
        self.sort_target_combo.addItem("정렬대상 없음")
        self.sort_target_combo.addItem("보증금/매매가")
        self.sort_target_combo.addItem("월세")
        self.sort_target_combo.addItem("층수")
        self.sort_target_combo.addItem("면적")  # 면적 정렬 옵션 추가
        
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItem("오름차순")
        self.sort_order_combo.addItem("내림차순")
        self.excel_button = QPushButton("엑셀 다운로드")
        search_layout.addWidget(self.trade_type_combo)
        search_layout.addWidget(self.sort_target_combo)
        search_layout.addWidget(self.sort_order_combo)
        search_layout.addWidget(self.excel_button)

        # 저장된 매물 필터 추가
        self.show_saved_only = QPushButton("저장된 매물")
        self.show_saved_only.setCheckable(True)  # 토글 버튼으로 설정
        self.show_saved_only.setFixedWidth(80)
        self.show_saved_only.clicked.connect(self.search_articles)
        search_layout.addWidget(self.show_saved_only)
        main_layout.addLayout(search_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 테이블 위젯
        self.table = QTableWidget()
        self.table.setColumnCount(11)  # Changed from 10 to 11 (added price comparison column)
        self.table.setHorizontalHeaderLabels([
            "단지명", "동", "층", "매물번호", "거래유형", "보증금/매매가", "월세", "면적(m²)", "중개사", "시세비교", "저장"
        ])
        self.table.cellClicked.connect(self.show_detail)
        self.table.resizeColumnsToContents()
        self.table.setMinimumHeight(400)

        # 검색/필터/정렬 기능 연결
        self.complex_combo.currentIndexChanged.connect(self.update_dong_list)  # 단지 선택 시 동 목록 업데이트
        self.complex_combo.currentIndexChanged.connect(self.search_articles)
        self.dong_combo.currentIndexChanged.connect(self.search_articles)  # 동 선택 시 검색
        self.trade_type_combo.currentIndexChanged.connect(self.search_articles)
        self.sort_target_combo.currentIndexChanged.connect(self.search_articles)  # 정렬 대상 변경 시 검색
        self.sort_order_combo.currentIndexChanged.connect(self.search_articles)  # 정렬 순서 변경 시 검색
        self.excel_button.clicked.connect(self.download_excel)

        # Detail and Analysis Layout
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        
        # 탭 위젯 추가
        tab_widget = QTabWidget()
        
        # 상세 정보 탭
        detail_tab = QWidget()
        detail_tab_layout = QVBoxLayout(detail_tab)
        
        self.detail = QTextBrowser()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("매물을 선택하면 상세 정보가 표시됩니다.")
        detail_tab_layout.addWidget(self.detail)
        
        # 메모 입력
        note_label = QLabel("메모:")
        detail_tab_layout.addWidget(note_label)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("이 매물에 대한 메모를 입력하세요...")
        self.note_input.setMaximumHeight(100)
        detail_tab_layout.addWidget(self.note_input)
        
        save_note_btn = QPushButton("메모 저장")
        save_note_btn.clicked.connect(self.save_note)
        detail_tab_layout.addWidget(save_note_btn)
        
        # 분석 탭
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        self.analysis_browser = QTextBrowser()
        self.analysis_browser.setPlaceholderText("매물을 선택하면 분석 정보가 표시됩니다.")
        analysis_layout.addWidget(self.analysis_browser)

        # 추천 시스템 탭 추가
        recommendation_tab = QWidget()
        recommendation_layout = QVBoxLayout(recommendation_tab)
        
        # 선호도 입력
        preference_label = QLabel("선호도 입력:")
        recommendation_layout.addWidget(preference_label)
        
        self.preference_input = QTextEdit()
        self.preference_input.setPlaceholderText("원하시는 조건을 자연스럽게 입력해주세요.\n예시: 바다뷰를 선호하고 젊은 부부와 아이는 2명. 아이 둘은 초등학생이어서 공원이 가까웠으면 좋겠어요.")
        self.preference_input.setMaximumHeight(100)
        recommendation_layout.addWidget(self.preference_input)
        
        analyze_btn = QPushButton("매물 분석 및 추천")
        analyze_btn.clicked.connect(self.analyze_preferences)
        recommendation_layout.addWidget(analyze_btn)
        
        self.recommendation_browser = QTextBrowser()
        self.recommendation_browser.setPlaceholderText("선호도를 입력하고 분석 버튼을 누르면 맞춤 매물이 추천됩니다.")
        recommendation_layout.addWidget(self.recommendation_browser)
        
        # 탭 추가
        tab_widget.addTab(detail_tab, "상세 정보")
        tab_widget.addTab(analysis_tab, "매물 분석")
        tab_widget.addTab(recommendation_tab, "맞춤 추천")
        
        detail_layout.addWidget(tab_widget)
        
        splitter.addWidget(self.table)
        splitter.addWidget(detail_container)
        splitter.setSizes([700, 500])

        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Set the layout for main widget
        main_widget.setLayout(main_layout)
        
        # Set the central widget
        self.setCentralWidget(main_widget)

        # 최초 전체 데이터 표시
        self.search_articles()

    def update_dong_list(self):
        selected_complex = self.complex_combo.currentText()
        current_dong = self.dong_combo.currentText()
        
        self.dong_combo.clear()
        self.dong_combo.addItem("전체 동")
        
        if selected_complex != "전체 단지":
            # 선택된 단지의 동 목록 가져오기
            dong_list = sorted(list(set(
                d.get("dong", "") for d in self.data 
                if d.get("complexName", "") == selected_complex and d.get("dong", "")
            )))
            self.dong_combo.addItems(dong_list)
        
        # 이전 선택 복원 시도
        index = self.dong_combo.findText(current_dong)
        if index >= 0:
            self.dong_combo.setCurrentIndex(index)
        
    def search_articles(self):
        complex_name = self.complex_combo.currentText()
        dong = self.dong_combo.currentText()
        trade_type = self.trade_type_combo.currentText()
        sort_target = self.sort_target_combo.currentText()
        sort_order = self.sort_order_combo.currentText()
        show_saved_only = self.show_saved_only.isChecked()
        article_no = self.article_no_input.text().strip()  # 매물번호 검색어

        # 1. 필터링
        filtered = self.data
        
        # 매물번호 필터
        if article_no:
            filtered = [a for a in filtered if str(a.get("articleNo", "")).startswith(article_no)]
            
        # 저장된 매물 필터
        if show_saved_only:
            filtered = [a for a in filtered if a.get("articleNo", "") in self.saved_items]
            
        # 단지명 필터
        if complex_name != "전체 단지":
            filtered = [a for a in filtered if a.get("complexName", "") == complex_name]
            # 동 필터
            if dong != "전체 동":
                filtered = [a for a in filtered if a.get("dong", "") == dong]
        # 거래유형 필터
        if trade_type != "전체":
            filtered = [a for a in filtered if a.get("tradeTypeName", "") == trade_type]

        # 2. 정렬
        if sort_target != "정렬대상 없음":
            reverse = sort_order == "내림차순"
            if sort_target == "보증금/매매가":
                def parse_price(val):
                    if not val:
                        return 0
                    val = str(val).replace(",", "").replace(" ", "")
                    if "억" in val:
                        parts = val.split("억")
                        num = int(parts[0]) * 10000
                        if len(parts) > 1 and parts[1].strip():
                            try:
                                num += int(parts[1])
                            except:
                                pass
                        return num
                    try:
                        return int(val)
                    except:
                        return 0
                filtered = sorted(filtered, key=lambda a: parse_price(a.get("dealOrWarrantPrc", "")), reverse=reverse)
            elif sort_target == "월세":
                def parse_rent(val):
                    try:
                        return int(val)
                    except:
                        return 0
                filtered = sorted(filtered, key=lambda a: parse_rent(a.get("rentPrc", "")), reverse=reverse)
            elif sort_target == "층수":
                def parse_floor(val):
                    if not val:
                        return (-1, "")  # 층수 정보가 없는 경우
                    val = str(val).split("/")[0].strip()  # "12/48" 형태에서 실제 층수만 추출
                    try:
                        return (0, int(val))  # 숫자인 경우 (0은 정상 데이터를 의미)
                    except:
                        return (1, val)  # 숫자가 아닌 경우 (예: "저층", "고층" 등) 맨 아래로
                filtered = sorted(filtered, key=lambda a: parse_floor(a.get("floorInfo", "")))  # 오름차순 기준
                if reverse:  # 내림차순인 경우 숫자만 역순으로, 텍스트는 그대로 아래에
                    nums = [x for x in filtered if parse_floor(x.get("floorInfo", ""))[0] == 0]
                    texts = [x for x in filtered if parse_floor(x.get("floorInfo", ""))[0] != 0]
                    filtered = list(reversed(nums)) + texts
            elif sort_target == "면적":  # 면적 정렬 추가
                def parse_area(val):
                    try:
                        return float(str(val))
                    except:
                        return 0
                filtered = sorted(filtered, key=lambda a: parse_area(a.get("area2", "0")), reverse=reverse)

        self.update_table(filtered)

    def remove_outliers(self, prices):
        """극단적인 가격(이상치)을 제거
        IQR(사분위수 범위) 방법 사용: Q1 - 1.5*IQR ~ Q3 + 1.5*IQR 범위 밖의 값을 제거"""
        if len(prices) < 4:  # 데이터가 너무 적으면 이상치 제거하지 않음
            return prices
            
        prices = sorted(prices)
        q1 = prices[len(prices)//4]  # 제1사분위수
        q3 = prices[len(prices)*3//4]  # 제3사분위수
        iqr = q3 - q1  # 사분위수 범위
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        filtered_prices = [p for p in prices if lower_bound <= p <= upper_bound]
        return filtered_prices if filtered_prices else prices  # 필터링 후 데이터가 없으면 원본 반환

    def get_price_comparison(self, article):
        """매물의 가격을 같은 단지 내 동일 거래유형 매물들과 비교"""
        complex_name = article.get('complexName', '')
        trade_type = article.get('tradeTypeName', '')
        
        # 거래유형별로 비교할 가격 결정
        if trade_type == "매매":
            price = self.parse_price(article.get('dealOrWarrantPrc', '0'))
            price_type = "매매가"
        elif trade_type == "전세":
            price = self.parse_price(article.get('dealOrWarrantPrc', '0'))
            price_type = "보증금"
        elif trade_type == "월세":
            price = self.parse_price(article.get('rentPrc', '0'))  # 월세 금액으로 변경
            price_type = "월세"
        else:
            return "-"
        
        # 같은 단지, 같은 거래유형, 비슷한 면적의 매물들과 비교
        area = float(article.get('area2', 0))
        same_complex_articles = [
            a for a in self.data 
            if a.get('complexName') == complex_name 
            and a.get('tradeTypeName') == trade_type
            and a.get('articleNo') != article.get('articleNo')
            and abs(float(a.get('area2', 0)) - area) <= 5  # 면적 차이 5m² 이내
        ]
        
        if same_complex_articles and price > 0:
            # 거래유형별로 적절한 가격 비교
            if trade_type == "매매":
                prices = [self.parse_price(a.get('dealOrWarrantPrc', '0')) for a in same_complex_articles]
            elif trade_type == "전세":
                prices = [self.parse_price(a.get('dealOrWarrantPrc', '0')) for a in same_complex_articles]
            elif trade_type == "월세":
                prices = [self.parse_price(a.get('rentPrc', '0')) for a in same_complex_articles]  # 월세 금액 비교로 변경
            
            # 이상치 제거
            filtered_prices = self.remove_outliers(prices)
            
            if filtered_prices:
                avg_price = sum(filtered_prices) / len(filtered_prices)
                price_diff_percent = ((price - avg_price) / avg_price) * 100
                
                if price_diff_percent < 0:
                    return f'<span style="color: green;">▼ {abs(price_diff_percent):.1f}%</span>'
                elif price_diff_percent > 0:
                    return f'<span style="color: red;">▲ {price_diff_percent:.1f}%</span>'
                else:
                    return "평균"
        return "-"

    def parse_price(self, price_text):
        """가격 문자열을 숫자로 변환"""
        if not price_text:
            return 0
        price_text = str(price_text).replace(",", "").replace(" ", "")
        if "억" in price_text:
            parts = price_text.split("억")
            price = float(parts[0]) * 10000
            if len(parts) > 1 and parts[1].strip():
                try:
                    price += float(parts[1])
                except:
                    pass
            return price
        try:
            return float(price_text)
        except:
            return 0

    def format_price(self, price_text):
        """가격을 포맷팅합니다."""
        if not price_text:
            return ""
            
        # 이미 포맷된 가격이면 그대로 반환
        if isinstance(price_text, str) and ('억' in price_text or ',' in price_text):
            return price_text
            
        try:
            price = int(str(price_text).replace(',', ''))
            if price < 10000:  # 1억 미만
                return f"{price:,}"
            else:  # 1억 이상
                억 = price // 10000
                만 = price % 10000
                if 만 > 0:
                    return f"{억}억 {만:,}"
                else:
                    return f"{억}억"
        except (ValueError, TypeError):
            return price_text

    def update_table(self, articles):
        self.table.setRowCount(0)
        if not articles:
            self.table.setRowCount(1)
            for col in range(self.table.columnCount()):
                self.table.setItem(0, col, QTableWidgetItem("-"))
            self.detail.setHtml("검색 결과가 없습니다.")
            return
        self.table.setRowCount(len(articles))
        for row, article in enumerate(articles):
            article_no = article.get("articleNo", "")
            self.table.setItem(row, 0, QTableWidgetItem(article.get("complexName", "")))
            self.table.setItem(row, 1, QTableWidgetItem(article.get("dong", "")))
            self.table.setItem(row, 2, QTableWidgetItem(article.get("floorInfo", "")))
            self.table.setItem(row, 3, QTableWidgetItem(article_no))
            self.table.setItem(row, 4, QTableWidgetItem(article.get("tradeTypeName", "")))
            self.table.setItem(row, 5, QTableWidgetItem(article.get("dealOrWarrantPrc", "")))
            self.table.setItem(row, 6, QTableWidgetItem(article.get("rentPrc", "")))
            self.table.setItem(row, 7, QTableWidgetItem(str(article.get("area2", ""))))
            
            # 중개사 정보 (링크)
            realtor_name = article.get("realtorName", "")
            realtor_id = article.get("realtorId", "")
            if realtor_id and realtor_name:
                url = f"https://m.land.naver.com/agency/info/{realtor_id}"
                link_label = QLabel(f'<a href="{url}" style="color: #0066cc; text-decoration: none;">{realtor_name}</a>')
                link_label.setOpenExternalLinks(True)
                link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                link_label = QLabel(realtor_name or "-")
                link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 8, link_label)
            
            # 시세비교 정보
            price_comparison_label = QLabel(self.get_price_comparison(article))
            price_comparison_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 9, price_comparison_label)
            
            # 저장 체크박스
            self.create_save_checkbox(row, article_no)

        self.table.resizeColumnsToContents()
        self.detail.clear()

    def create_save_checkbox(self, row, article_no):
        checkbox_container = QWidget()
        layout = QHBoxLayout(checkbox_container)
        layout.setContentsMargins(4, 0, 4, 0)  # 좌우 여백 추가
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        checkbox = QCheckBox()
        checkbox.setChecked(article_no in self.saved_items)
        checkbox.clicked.connect(lambda checked, a=article_no, r=row: self.save_to_saved_items(a, r))
        
        layout.addWidget(checkbox)
        self.table.setCellWidget(row, 10, checkbox_container) # Changed column index to 10

    def show_detail(self, row, column):
        if column == 10:  # 저장 체크박스 열
            article_no_item = self.table.item(row, 3)  # 매물번호 열
            if article_no_item is None:
                return
            article_no = article_no_item.text()
            self.save_to_saved_items(article_no, row)
            return

        # 현재 선택된 매물 정보 저장
        article_no_item = self.table.item(row, 3)  # 매물번호
        if article_no_item is None:
            return
        self.current_article_no = article_no_item.text()
        article = next((a for a in self.data if str(a.get('articleNo')) == self.current_article_no), None)
        if not article:
            return

        # 캐시된 상세 정보 확인
        detail_info = None
        if self.current_article_no in self.article_details_cache:
            detail_info = self.article_details_cache[self.current_article_no]
        else:
            # 캐시에 없는 경우에만 API 호출
            detail_info = self.get_article_detail(self.current_article_no)
        
        # HTML 스타일 정의
        style = """
        <style>
        .section-title {
            font-size: 16px;
            font-weight: bold;
            margin-top: 12px;
            margin-bottom: 8px;
            color: #333;
        }
        .content {
            margin-left: 10px;
            line-height: 1.5;
        }
        hr {
            border: 0;
            height: 1px;
            background: #ddd;
            margin: 8px 0;
        }
        </style>
        """
        
        # 기본 정보
        detail_text = style
        detail_text += '<div class="section-title">기본 정보</div>'
        detail_text += '<div class="content">'
        detail_text += f"단지명: {article.get('complexName', '')}<br>"
        detail_text += f"동: {article.get('dong', '')}<br>"
        detail_text += f"매물번호: {article.get('articleNo', '')}<br>"
        detail_text += f"거래유형: {article.get('tradeTypeName', '')}<br>"
        
        # 가격 정보
        if article.get('dealOrWarrantPrc') or article.get('rentPrc'):
            detail_text += f"보증금/매매가: {article.get('dealOrWarrantPrc', '')}<br>"
            if article.get('rentPrc'):
                detail_text += f"월세: {article.get('rentPrc', '')}만원<br>"
        
        # 상세 정보
        detail_text += f"층: {article.get('floorInfo', '')}<br>"
        detail_text += f"전용면적: {article.get('area2', '')}m²<br>"
        detail_text += f"공급면적: {article.get('area1', '')}m²<br>"
        if article.get('direction'):
            detail_text += f"방향: {article.get('direction', '')}<br>"
        detail_text += f"확인일자: {article.get('articleConfirmYmd', '')}<br>"
        detail_text += '</div>'
        detail_text += '<hr>'
        
        # 중개사 정보
        detail_text += '<div class="section-title">중개사 정보</div>'
        detail_text += '<div class="content">'
        detail_text += f"중개사무소: {article.get('realtorName', '')}<br>"
        detail_text += '</div>'
        detail_text += '<hr>'
        
        # 매물 특징
        if article.get('articleFeatureDesc'):
            detail_text += '<div class="section-title">매물 특징</div>'
            detail_text += '<div class="content">'
            detail_text += f"{article.get('articleFeatureDesc', '')}<br>"
            detail_text += '</div>'
            detail_text += '<hr>'
            
        # API 상세 설명
        if detail_info and 'articleDetail' in detail_info:
            article_detail = detail_info['articleDetail']
            description = article_detail.get('detailDescription')
            if description:
                detail_text += '<div class="section-title">상세 설명</div>'
                detail_text += '<div class="content">'
                # ChatGPT를 통해 설명 포맷팅 (캐시 사용)
                formatted_description = self.format_description_with_gpt(description, self.current_article_no)
                if formatted_description:
                    # 볼드 처리 (**text**를 <b>text</b>로 변환)
                    formatted_description = formatted_description.replace('**', '<b>')
                    # 홀수 번째 <b>는 시작 태그, 짝수 번째는 종료 태그로 변경
                    parts = formatted_description.split('<b>')
                    formatted_description = parts[0]
                    for i, part in enumerate(parts[1:], 1):
                        if i % 2 == 1:
                            formatted_description += '<b>' + part
                        else:
                            formatted_description += '</b>' + part
                    detail_text += formatted_description.replace('\n', '<br>')
                else:
                    detail_text += description.replace('\n', '<br>')
                detail_text += '</div>'
                detail_text += '<hr>'

        # QTextBrowser에 HTML 설정
        self.detail.setHtml(detail_text)
        
        # 메모 표시
        self.note_input.setPlainText(self.notes.get(self.current_article_no, ""))
        
        # 분석 정보 표시
        self.show_analysis(article)

    def format_price_korean(self, price_in_manwon):
        """가격을 한국식으로 포맷팅 (억 단위)"""
        if price_in_manwon < 1:
            return "0원"
        
        # 1억 이상일 때만 억 단위 사용
        if price_in_manwon >= 10000:
            eok = int(price_in_manwon // 10000)  # 정수로 변환
            man = int(price_in_manwon % 10000)   # 정수로 변환
            
            if man > 0:
                return f"{eok}억 {man:,}만원"
            return f"{eok}억원"
        return f"{int(price_in_manwon):,}만원"  # 정수로 변환

    def show_analysis(self, article):
        if not article:
            return
            
        analysis_text = "<h3>매물 분석</h3>"
        
        # 주요 정보 표시
        trade_type = article.get('tradeTypeName', '')
        price_text = article.get('dealOrWarrantPrc', '0')
        rent_price_text = article.get('rentPrc', '0')
        rent_price = self.parse_price(rent_price_text)
        area = float(article.get('area2', 0))  # 전용면적 (m²)
        floor_info = article.get('floorInfo', '')
        complex_name = article.get('complexName', '')
        dong = article.get('dong', '')
        
        # 매물 기본 정보
        analysis_text += f"{complex_name} {dong} {floor_info}층<br>"
        analysis_text += f"{trade_type}"
        if trade_type == "월세" and rent_price > 0:
            analysis_text += f" {rent_price_text}만원"
        analysis_text += f" / 보증금 {price_text}"
        if trade_type == "매매":
            analysis_text += " (매매가)"
        analysis_text += f"<br>전용 {area:.1f}m²<br><br>"
        
        # 1. 평당 가격 계산
        if trade_type == "매매":
            price_type = "매매가"
        elif trade_type == "전세":
            price_type = "보증금"
        elif trade_type == "월세":
            price_type = "보증금"
        else:
            price_type = ""
                
        price = self.parse_price(price_text)
        
        if area > 0 and price > 0:
            price_per_m2 = price / area  # 만원/m²
            price_per_pyeong = price_per_m2 * 3.3058  # 만원/평
            
            analysis_text += f"<br>▶ 단위면적당 {price_type}<br>"
            analysis_text += f"• m² 당 가격: {price_per_m2:.1f}만원/m²<br>"
            analysis_text += f"• 평당 가격: {price_per_pyeong:.1f}만원/평<br>"
            
            # 같은 단지 내 매물들과 비교 (비슷한 면적대)
            complex_name = article.get('complexName', '')
            if complex_name in ['센텀하이브B동오피스', '센텀하이브B동상가']:
                same_complex_articles = [
                    a for a in self.data
                    if a.get('complexName') == complex_name
                    and a.get('tradeTypeName') == trade_type
                    and a.get('articleNo') != article.get('articleNo')
                    and abs(float(a.get('area2', 0)) - area) <= 5
                ]
            else:
                same_complex_articles = [
                    a for a in self.data
                    if a.get('complexName') == complex_name
                    and a.get('tradeTypeName') == trade_type
                    and a.get('articleNo') != article.get('articleNo')
                    and abs(float(a.get('area2', 0)) - area) <= 5
                ]
            
            if same_complex_articles:
                analysis_text += f"<br>▶ 같은 단지 내 비슷한 면적의 {trade_type} 매물 비교<br>"
                
                # 가격 통계
                if trade_type == "매매":
                    prices = [self.parse_price(a.get('dealOrWarrantPrc', '0')) for a in same_complex_articles]
                elif trade_type == "전세":
                    prices = [self.parse_price(a.get('dealOrWarrantPrc', '0')) for a in same_complex_articles]
                elif trade_type == "월세":
                    prices = [self.parse_price(a.get('rentPrc', '0')) for a in same_complex_articles]
                    rent_prices = [self.parse_price(a.get('rentPrc', '0')) for a in same_complex_articles]
                
                # 이상치 제거
                if prices:
                    filtered_prices = self.remove_outliers(prices)
                    avg_price = sum(filtered_prices) / len(filtered_prices)
                    min_price = min(filtered_prices)
                    max_price = max(filtered_prices)
                    
                    # 평균 대비 가격 차이 계산 및 색상 적용
                    price_diff = price - avg_price
                    if price_diff < 0:
                        color = "green"
                        diff_text = f"-{self.format_price_korean(abs(price_diff))}"
                    elif price_diff > 0:
                        color = "red"
                        diff_text = f"+{self.format_price_korean(price_diff)}"
                    else:
                        color = "black"
                        diff_text = "평균"
                    
                    total_count = len(prices)
                    filtered_count = len(filtered_prices)
                    excluded_count = total_count - filtered_count
                    
                    if excluded_count > 0:
                        analysis_text += f"(극단가 {excluded_count}개 제외 분석)<br>"
                    
                    analysis_text += f"• {price_type} 평균 대비: <span style='color: {color};'>{diff_text}</span><br>"
                    analysis_text += f"• 최저 {price_type}: {self.format_price_korean(min_price)}<br>"
                    analysis_text += f"• 평균 {price_type}: {self.format_price_korean(int(avg_price))}<br>"  # 평균값을 정수로 변환
                    analysis_text += f"• 최고 {price_type}: {self.format_price_korean(max_price)}<br>"
                    
                    if trade_type == "월세" and rent_prices:
                        filtered_rent_prices = self.remove_outliers(rent_prices)
                        avg_rent = sum(filtered_rent_prices) / len(filtered_rent_prices)
                        min_rent = min(filtered_rent_prices)
                        max_rent = max(filtered_rent_prices)
                        
                        rent_diff = rent_price - avg_rent
                        if rent_diff < 0:
                            rent_color = "green"
                            rent_diff_text = f"-{abs(rent_diff):.0f}만원"
                        elif rent_diff > 0:
                            rent_color = "red"
                            rent_diff_text = f"+{rent_diff:.0f}만원"
                        else:
                            rent_color = "black"
                            rent_diff_text = "평균"
                        
                        excluded_rent_count = len(rent_prices) - len(filtered_rent_prices)
                        if excluded_rent_count > 0:
                            analysis_text += f"(극단 월세 {excluded_rent_count}개 제외 분석)<br>"
                        
                        analysis_text += f"<br>▶ 월세 비교<br>"
                        analysis_text += f"• 월세 평균 대비: <span style='color: {rent_color};'>{rent_diff_text}</span><br>"
                        analysis_text += f"• 최저 월세: {min_rent:.0f}만원<br>"
                        analysis_text += f"• 평균 월세: {avg_rent:.0f}만원<br>"
                        analysis_text += f"• 최고 월세: {max_rent:.0f}만원<br>"
                
                # 면적 분포
                areas = [float(a.get('area2', 0)) for a in same_complex_articles]
                if areas:
                    avg_area = sum(areas) / len(areas)
                    analysis_text += f"<br>▶ 면적 분포<br>"
                    analysis_text += f"• 평균 면적: {avg_area:.1f}m²<br>"
                    
                    # 현재 매물의 면적이 평균 대비 얼마나 차이나는지
                    area_diff_percent = ((area - avg_area) / avg_area) * 100
                    analysis_text += f"• 평균 대비: {area_diff_percent:+.1f}%<br>"
        
        self.analysis_browser.setHtml(analysis_text)

    def pre_filter_properties(self, preferences):
        """선호도 키워드를 기반으로 매물을 1차 필터링합니다."""
        keywords = {
            '바다': ['바다', '오션', '뷰', '전망'],
            '공원': ['공원', '녹지', '산책'],
            '학교': ['학교', '초등학교', '통학'],
            '역세권': ['역세권', '지하철', '교통'],
            '신축': ['신축', '새 아파트', '새건물'],
            '주차': ['주차', '주차장'],
            '편의시설': ['편의시설', '상가', '마트'],
            '테라스': ['테라스', '정원', '마당'],
            '채광': ['채광', '햇살', '밝은', '햇빛'],
            '구조': ['구조', '구조변경', '확장', '올수리', '풀옵션'],
            '인테리어': ['인테리어', '리모델링', '신규', '새로'],
            '방향': ['방향', '남향', '남서향', '남동향', '동향', '서향'],
            '조망': ['조망', '뷰', '전망', '탁트인'],
        }
        
        # 선호도에서 키워드 추출
        active_keywords = []
        preferences_lower = preferences.lower()
        
        # 층수 조건 확인
        floor_requirement = None
        if "층" in preferences:
            import re
            floor_matches = re.findall(r'(\d+)층\s*(이상|이하|초과|미만)?', preferences)
            if floor_matches:
                floor_num, condition = floor_matches[0]
                floor_requirement = {
                    'number': int(floor_num),
                    'condition': condition if condition else '이상'
                }
        
        # 사용자 입력에서 키워드 추출
        for category, words in keywords.items():
            for word in words:
                if word in preferences_lower:
                    # 키워드와 그 유사어들을 모두 포함
                    active_keywords.extend(words)
                    break  # 한 카테고리에서 하나만 매칭되어도 충분
        
        # 직접적인 검색어도 키워드로 추가
        direct_keywords = [word.strip() for word in preferences_lower.split() if len(word.strip()) >= 2]
        active_keywords.extend(direct_keywords)
        
        # 중복 제거
        active_keywords = list(set(active_keywords))
        
        # 키워드가 없고 층수 조건도 없으면 상위 10개만 반환
        if not active_keywords and not floor_requirement:
            return self.data[:10]
            
        # 매물 필터링 및 점수 계산
        scored_properties = []
        for article in self.data:
            score = 0
            
            # 층수 조건 체크
            if floor_requirement:
                floor_info = article.get('floorInfo', '')
                try:
                    actual_floor = int(floor_info.split('/')[0])
                    meets_floor_requirement = False
                    
                    if floor_requirement['condition'] == '이상':
                        meets_floor_requirement = actual_floor >= floor_requirement['number']
                    elif floor_requirement['condition'] == '이하':
                        meets_floor_requirement = actual_floor <= floor_requirement['number']
                    elif floor_requirement['condition'] == '초과':
                        meets_floor_requirement = actual_floor > floor_requirement['number']
                    elif floor_requirement['condition'] == '미만':
                        meets_floor_requirement = actual_floor < floor_requirement['number']
                    
                    if not meets_floor_requirement:
                        continue  # 층수 조건을 만족하지 않으면 제외
                except (ValueError, IndexError):
                    continue  # 층수 파싱 실패 시 제외
            
            # 검색 대상 텍스트 생성
            search_text = (
                str(article.get('articleFeatureDesc', '')) + ' ' +
                str(article.get('complexName', '')) + ' ' +
                str(article.get('direction', '')) + ' ' +
                str(article.get('tagList', [])).replace('[', '').replace(']', '') + ' ' +  # 태그 리스트 추가
                str(article.get('dealerComment', ''))  # 중개사 코멘트 추가
            ).lower()
            
            # 캐시된 상세 정보가 있는 경우 포함
            article_no = article.get('articleNo', '')
            if article_no in self.article_details_cache:
                detail_info = self.article_details_cache[article_no]
                if detail_info:
                    # 상세 설명 추가
                    if detail_info.get('articleDetail', {}).get('detailDescription'):
                        search_text += ' ' + str(detail_info['articleDetail']['detailDescription']).lower()
                    # 추가 특징 정보 추가
                    if detail_info.get('articleDetail', {}).get('articleFeatureDesc'):
                        search_text += ' ' + str(detail_info['articleDetail']['articleFeatureDesc']).lower()
                    # 중개사 코멘트 추가
                    if detail_info.get('articleDetail', {}).get('dealerComment'):
                        search_text += ' ' + str(detail_info['articleDetail']['dealerComment']).lower()
            
            # 키워드 매칭 및 점수 계산
            for keyword in active_keywords:
                if keyword in search_text:
                    # 제목이나 특징에서 발견되면 더 높은 점수
                    if keyword in str(article.get('articleFeatureDesc', '')).lower():
                        score += 3
                    else:
                        score += 1
                        
            # 층수 조건을 만족하면 추가 점수
            if floor_requirement:
                score += 5
                    
            if score > 0:  # 키워드가 하나라도 매칭되면 포함
                scored_properties.append((score, article))
        
        # 점수 기준 정렬 후 상위 20개만 반환 (토큰 제한을 위해)
        scored_properties.sort(key=lambda x: x[0], reverse=True)
        return [prop for score, prop in scored_properties[:50]]  # 20개에서 50개로 증가

    def analyze_preferences(self):
        """사용자 선호도를 분석하고 매물을 추천합니다."""
        preferences = self.preference_input.toPlainText().strip()
        if not preferences:
            QMessageBox.warning(self, "입력 오류", "선호도를 입력해주세요.")
            return

        try:
            # 진행 상태 표시
            self.recommendation_browser.setPlainText("매물을 분석하는 중입니다...")
            QApplication.processEvents()  # UI 업데이트

            # 1차 필터링
            filtered_properties = self.pre_filter_properties(preferences)
            
            if not filtered_properties:
                self.recommendation_browser.setHtml("""
                <style>
                .no-result {
                    color: #666;
                    text-align: center;
                    margin-top: 20px;
                    font-size: 14px;
                }
                </style>
                <div class="no-result">
                    조건에 맞는 매물을 찾을 수 없습니다.<br>
                    다른 조건으로 다시 시도해보세요.
                </div>
                """)
                return
            
            # 매물 번호 목록 생성
            valid_article_numbers = [str(article.get('articleNo', '')) for article in filtered_properties]
            
            # ChatGPT 프롬프트 생성 - 토큰 수 최소화
            prompt = f"""선호도({preferences})와 일치하는 매물을 추천해주세요.
매물이 없으면 "매칭 없음"이라고만 답변하세요.
반드시 5개 이상의 매물을 추천해주세요.
유효번호: {', '.join(valid_article_numbers)}

매물 목록:"""
            
            # 필터링된 매물 정보 압축
            for article in filtered_properties:
                article_no = article.get('articleNo', '')
                complex_name = article.get('complexName', '')
                trade_type = article.get('tradeTypeName', '')
                floor_info = article.get('floorInfo', '')
                detail_info = self.article_details_cache.get(article_no, {})
                
                # 특징 정보 압축
                features = []
                if article.get('articleFeatureDesc'):
                    features.append(article.get('articleFeatureDesc'))
                if article.get('direction'):
                    features.append(article.get('direction'))
                if detail_info and detail_info.get('articleDetail', {}).get('detailDescription'):
                    desc = detail_info['articleDetail']['detailDescription']
                    if len(desc) > 100:  # 상세 설명이 너무 길면 잘라서 추가
                        desc = desc[:100] + "..."
                    features.append(desc)
                
                # 중복 제거 및 문자열 결합
                unique_features = ' '.join(list(set(features)))
                if len(unique_features) > 150:  # 전체 설명 길이 제한
                    unique_features = unique_features[:150] + "..."
                
                prompt += f"\n[{article_no}] {complex_name} {trade_type} {floor_info}층 - {unique_features}"

            prompt += """

형식:
▶ [매물번호] - [단지명]
• 추천이유: (간단히)

반드시 5개 이상의 매물을 추천해주세요."""

            # 최대 3번까지 재시도
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "부동산 매물 추천 전문가입니다. 주어진 매물 중에서 반드시 5개 이상을 추천해야 합니다."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                    )
                    
                    recommendation = response.choices[0].message.content
                    if not recommendation:
                        continue  # 응답이 비어있으면 재시도
                    
                    # 추천된 매물 번호 검증
                    recommended_articles = []
                    for line in recommendation.split('\n'):
                        if line.startswith('▶'):
                            try:
                                article_no = line.split('[')[1].split(']')[0]
                                if article_no not in valid_article_numbers:
                                    continue  # 잘못된 매물 번호는 건너뜀
                                recommended_articles.append(article_no)
                            except IndexError:
                                continue
                    
                    # 최소 5개 매물 추천 검증
                    if len(recommended_articles) >= 5 or len(filtered_properties) < 5:
                        break  # 성공하거나 가능한 매물이 5개 미만이면 종료
                    
                    if attempt == max_retries - 1:  # 마지막 시도에서도 실패
                        # 점수 기준으로 상위 5개 매물 강제 추천
                        top_articles = filtered_properties[:5]
                        recommendation = "선호도에 따른 추천 매물:\n\n"
                        for article in top_articles:
                            article_no = article.get('articleNo', '')
                            complex_name = article.get('complexName', '')
                            recommendation += f"▶ [{article_no}] - {complex_name}\n"
                            recommendation += "• 추천이유: 선호도 점수 기준 상위 매물\n\n"
                        recommended_articles = [a.get('articleNo', '') for a in top_articles]
                        
                except Exception as e:
                    if attempt == max_retries - 1:  # 마지막 시도에서 실패
                        raise Exception(f"매물 추천 중 오류가 발생했습니다: {str(e)}")
                    continue  # 다시 시도

            # HTML로 포맷팅
            formatted_recommendation = """
            <style>
            .recommendation-title {
                font-size: 16px;
                font-weight: bold;
                margin-top: 12px;
                margin-bottom: 8px;
                color: #333;
            }
            .recommendation-content {
                margin-left: 10px;
                line-height: 1.5;
                padding: 8px;
                border-radius: 4px;
            }
            .recommendation-reason {
                margin-left: 20px;
                margin-top: 5px;
                margin-bottom: 15px;
                color: #666;
            }
            .filtered-info {
                color: #888;
                font-size: 12px;
                margin-bottom: 10px;
            }
            .property-item {
                border-bottom: 1px solid #eee;
                padding: 10px 0;
            }
            .property-item:last-child {
                border-bottom: none;
            }
            </style>
            """

            if "매칭 없음" in (recommendation or ""):
                formatted_recommendation += """
                <div class="no-result">
                    매칭되는 매물이 없습니다.<br>
                    다른 조건으로 다시 시도해보세요.
                </div>
                """
            else:
                formatted_recommendation += f'<div class="filtered-info">총 {len(self.data)}개 매물 중 {len(filtered_properties)}개의 관련 매물을 분석했습니다.</div>'
                formatted_recommendation += '<div class="recommendation-title">맞춤 매물 추천</div>'
                
                # 추천 결과를 HTML로 변환
                current_item = None
                if recommendation:  # Add null check
                    for line in recommendation.split('\n'):
                        if line.strip():
                            if line.startswith('▶'):
                                if current_item:
                                    formatted_recommendation += '</div>'
                                formatted_recommendation += f'<div class="property-item"><div class="recommendation-content"><b>{line}</b></div>'
                                current_item = True
                            elif line.startswith('•'):
                                formatted_recommendation += f'<div class="recommendation-reason">{line}</div>'
                            else:
                                formatted_recommendation += f'<div class="recommendation-reason">{line}</div>'
                
                if current_item:
                    formatted_recommendation += '</div>'

            self.recommendation_browser.setHtml(formatted_recommendation)

        except Exception as e:
            QMessageBox.critical(self, "분석 오류", f"매물 분석 중 오류가 발생했습니다:\n{str(e)}")

    def download_excel(self):
        row_count = self.table.rowCount()
        col_count = self.table.columnCount()
        data = []
        headers = []
        
        # 헤더 처리
        for i in range(col_count):
            header_item = self.table.horizontalHeaderItem(i)
            headers.append(header_item.text() if header_item else "")
            
        # 데이터 처리
        for row in range(row_count):
            row_data = []
            for col in range(col_count):
                cell_widget = self.table.cellWidget(row, col)
                if cell_widget:
                    if isinstance(cell_widget, QLabel):
                        row_data.append(cell_widget.text().replace('<a href="', '').split('">')[0])
                    elif isinstance(cell_widget, QWidget):  # 체크박스 컨테이너
                        checkbox = cell_widget.findChild(QCheckBox)
                        row_data.append("✓" if checkbox and checkbox.isChecked() else "")
                else:
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
            data.append(row_data)
            
        df = pd.DataFrame(data)
        df.columns = headers
        file_path, _ = QFileDialog.getSaveFileName(self, "엑셀로 저장", "매물목록.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            df.to_excel(file_path, index=False)

    def update_data(self):
        try:
            # Show updating message
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("데이터를 업데이트하는 중입니다...")
            msg.setWindowTitle("업데이트 중")
            msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            msg.show()
            QApplication.processEvents()  # Force UI update
            
            # Get the current working directory
            current_dir = os.getcwd()
            print(f"Running fetch_all.py from directory: {current_dir}")
            
            # Import and run fetch_all.py directly as a module
            import fetch_all
            
            # Capture stdout and stderr
            import io
            import contextlib
            
            # Redirect stdout and stderr to capture output
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                try:
                    # Run the main function from fetch_all
                    fetch_all.main()
                    return_code = 0
                except Exception as e:
                    print(f"Error in fetch_all.main(): {e}", file=stderr_capture)
                    return_code = 1
            
            result = type('Result', (), {
                'stdout': stdout_capture.getvalue(),
                'stderr': stderr_capture.getvalue(),
                'returncode': return_code
            })()
            
            print(f"fetch_all.py stdout: {result.stdout}")
            print(f"fetch_all.py stderr: {result.stderr}")
            print(f"fetch_all.py return code: {result.returncode}")
            
            if result.returncode != 0:
                error_msg = f"Error running fetch_all.py (return code: {result.returncode}):\n"
                if result.stderr:
                    error_msg += f"STDERR: {result.stderr}\n"
                if result.stdout:
                    error_msg += f"STDOUT: {result.stdout}"
                raise Exception(error_msg)
            
            # Reload the data
            self.data = self.load_data()
            
            # Update complex names in dropdown
            current_complex = self.complex_combo.currentText()
            self.complex_combo.clear()
            self.complex_combo.addItem("전체 단지")
            complex_names = sorted(list(set(d.get("complexName", "") for d in self.data)))
            self.complex_combo.addItems(complex_names)
            
            # Try to restore previous selection
            index = self.complex_combo.findText(current_complex)
            if index >= 0:
                self.complex_combo.setCurrentIndex(index)
            
            # Refresh the table
            self.search_articles()
            
            # Update the last update label
            self.refresh_last_update()
            
            # Close the updating message
            msg.close()
            
            # Show success message
            QMessageBox.information(self, "업데이트 완료", "데이터가 성공적으로 업데이트되었습니다.")
            
            # After updating the CSV, run the post-processing script
            import subprocess
            try:
                subprocess.run(['python', 'update_centum_b_office.py'], check=True)
            except Exception as e:
                print(f'센텀하이브B동오피스 변환 스크립트 실행 중 오류 발생: {e}')
            
        except Exception as e:
            print(f"Update data error: {str(e)}")
            QMessageBox.critical(self, "업데이트 실패", f"데이터 업데이트 중 오류가 발생했습니다:\n{str(e)}")

if __name__ == "__main__":
    import traceback
    try:
        app = QApplication(sys.argv)
        # Prompt for NAVER_ID/PW if missing
        if not os.getenv('NAVER_ID') or not os.getenv('NAVER_PW'):
            prompt_for_naver_credentials(env_path)
            load_dotenv(env_path, override=True)
        viewer = RealEstateViewer()
        viewer.show()
        sys.exit(app.exec())
    except Exception as e:
        print("\n[ERROR] An exception occurred while starting the application:\n")
        traceback.print_exc()
        input("\nPress Enter to exit...")