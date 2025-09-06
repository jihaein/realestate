import requests
import json
import time
import csv
import sys
from datetime import datetime, timedelta
from tqdm import tqdm
import os
from dotenv import load_dotenv
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


def prompt_for_naver_credentials_cli(env_path):
    print("네이버 아이디와 비밀번호를 입력하세요. (이 정보는 이 컴퓨터의 .env 파일에 저장됩니다)")
    naver_id = input('네이버 아이디: ').strip()
    import getpass
    naver_pw = getpass.getpass('네이버 비밀번호: ').strip()
    if not naver_id or not naver_pw:
        print('모든 정보를 입력해야 합니다.')
        return None, None
    # Save to .env
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    lines = [l for l in lines if not l.startswith('NAVER_ID=') and not l.startswith('NAVER_PW=')]
    lines.append(f'NAVER_ID={naver_id}\n')
    lines.append(f'NAVER_PW={naver_pw}\n')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    os.environ['NAVER_ID'] = naver_id
    os.environ['NAVER_PW'] = naver_pw
    return naver_id, naver_pw

def get_naver_auth_and_cookies():
    env_path = os.path.abspath('.env')
    for attempt in range(2):
        naver_id = os.getenv('NAVER_ID')
        naver_pw = os.getenv('NAVER_PW')
        if not naver_id or not naver_pw:
            naver_id, naver_pw = prompt_for_naver_credentials_cli(env_path)
            if not naver_id or not naver_pw:
                return None, None
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        import sys
        if sys.platform == 'darwin':
            chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            if os.path.exists(chrome_path):
                options.binary_location = chrome_path
            else:
                print("Chrome 브라우저를 찾을 수 없습니다. Chrome이 설치되어 있는지 확인해주세요. (macOS)")
                return None, None
        elif sys.platform.startswith('win'):
            pass
        else:
            print(f"이 운영체제({sys.platform})에서는 Chrome 브라우저 경로를 자동으로 설정하지 않습니다. Chrome이 설치되어 있고 PATH에 등록되어 있어야 합니다.")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 10)
            print("네이버 로그인 페이지로 이동 중...")
            driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(2)
            print("로그인 시도 중...")
            driver.execute_script(
                f"document.getElementById('id').value='{naver_id}';"
                f"document.getElementById('pw').value='{naver_pw}';"
            )
            time.sleep(1)
            login_button = wait.until(EC.element_to_be_clickable((By.ID, 'log.login')))
            login_button.click()
            time.sleep(3)
            print("네이버 부동산으로 이동 중...")
            driver.get('https://land.naver.com/')
            time.sleep(2)
            print("인증 정보 추출 중...")
            driver.get('https://new.land.naver.com/complexes/142817?articleNo=2324123456')
            time.sleep(3)
            auth_token = None
            for request in driver.requests:
                if request.url and 'land.naver.com/api' in request.url:
                    if request.headers:
                        print(f"Found API request headers: {request.headers}")
                        if 'authorization' in request.headers:
                            auth_token = request.headers['authorization']
                            print(f"Found auth token: {auth_token}")
                            break
            cookies = {c['name']: c['value'] for c in driver.get_cookies()}
            if not auth_token or not cookies:
                print("인증 토큰 또는 쿠키를 추출하지 못했습니다.")
                os.environ['NAVER_ID'] = ''
                os.environ['NAVER_PW'] = ''
                continue
            print("인증 정보 추출 완료!")
            return auth_token, cookies
        except Exception as e:
            print(f"네이버 자동 로그인/토큰 추출 실패: {e}")
            import traceback
            traceback.print_exc()
            os.environ['NAVER_ID'] = ''
            os.environ['NAVER_PW'] = ''
            continue
        finally:
            try:
                driver.quit()
            except:
                pass
    return None, None

def load_previous_data():
    """이전 데이터 로드"""
    try:
        with open('songdo_apartments_listings.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return {row['articleNo']: row for row in reader}
    except FileNotFoundError:
        return {}

def get_last_update_time():
    """마지막 업데이트 시간 가져오기"""
    try:
        with open('last_update.txt', 'r', encoding='utf-8') as f:
            last_update = datetime.strptime(f.read().strip(), '%Y-%m-%d %H:%M:%S')
    except (FileNotFoundError, ValueError):
        last_update = datetime.now() - timedelta(days=7)  # 기본값: 7일 전
    return last_update

def parse_date(date_str):
    """날짜 문자열을 datetime 객체로 변환"""
    try:
        # YYYYMMDD 형식
        if len(date_str) == 8:
            return datetime.strptime(date_str, '%Y%m%d')
        # YYYY-MM-DD HH:MM:SS 형식
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return datetime.now()

def fetch_by_complex_id(complex_id, complex_name, dong, pbar, previous_data):
    """단지 코드로 매물 검색"""
    all_articles = []
    page = 1
    max_pages = 50  # 최대 페이지 수 제한
    no_new_data_count = 0  # 새로운 데이터가 없는 연속 페이지 수
    last_update = get_last_update_time()

    while page <= max_pages:
        url = (
            "https://new.land.naver.com/api/articles/complex/"
            f"{complex_id}?realEstateType=APT&tradeType=&page={page}"
            "&articleState=&viewerType=&complexNo="
            f"{complex_id}&buildingNos=&areaNos=&type=list&order=rank"
        )

        try:
            # Create new headers for each request
            request_headers = headers.copy()
            request_headers['Referer'] = f'https://new.land.naver.com/complexes/{complex_id}'
            request_headers['Origin'] = 'https://new.land.naver.com'
            request_headers['Host'] = 'new.land.naver.com'

            # Add all required cookies
            request_cookies = cookies.copy()
            request_cookies.update({
                'nhn.realestate.article.rlet_type_cd': 'A01',
                'nhn.realestate.article.trade_type_cd': '""',
                'landHomeFlashUseYn': 'Y'
            })

            response = requests.get(
                url,
                headers=request_headers,
                cookies=request_cookies,
                timeout=10
            )

            if response.status_code != 200:
                print(f"{complex_name} 요청 실패 (페이지 {page}): {response.status_code}")
                print(f"Request headers: {request_headers}")
                print(f"Request cookies: {request_cookies}")
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response body: {response.text}")
                break

            data = response.json()
            articles = data.get("articleList", [])
            
            if not articles:
                break

            new_articles = []
            for article in articles:
                article_no = article.get('articleNo')
                confirm_date = parse_date(article.get('articleConfirmYmd', ''))

                # 이전 데이터에 없거나 최근에 업데이트된 매물만 추가
                if (article_no not in previous_data or 
                    confirm_date > last_update):
                    article['complexName'] = complex_name
                    article['dong'] = dong
                    new_articles.append(article)

            if new_articles:
                all_articles.extend(new_articles)
                pbar.update(len(new_articles))
                no_new_data_count = 0
            else:
                no_new_data_count += 1

            # 연속 3페이지 동안 새로운 데이터가 없으면 중단
            if no_new_data_count >= 3:
                break

            page += 1
            time.sleep(1)  # 딜레이 시간

        except Exception as e:
            print(f"{complex_name} 오류 발생 (페이지 {page}): {str(e)}")
            break

    return all_articles

def save_to_csv(all_articles, previous_data):
    """매물 정보를 CSV 파일로 저장"""
    # 필드 정의
    fields = [
        'complexName', 'articleNo', 'articleName', 'tradeTypeName',
        'dealOrWarrantPrc', 'rentPrc', 'floorInfo', 'area1', 'area2',
        'direction', 'articleConfirmYmd', 'articleFeatureDesc',
        'realtorName', 'realtorId', 'dong'
    ]

    # 기존 데이터와 새로운 데이터 병합
    merged_data = previous_data.copy()
    for article in all_articles:
        article_no = article.get('articleNo')
        if article_no:
            row = {
                'complexName': article.get('complexName', ''),
                'articleNo': article.get('articleNo', ''),
                'articleName': article.get('articleName', ''),
                'tradeTypeName': article.get('tradeTypeName', ''),
                'dealOrWarrantPrc': article.get('dealOrWarrantPrc', ''),
                'rentPrc': article.get('rentPrc', ''),
                'floorInfo': article.get('floorInfo', ''),
                'area1': article.get('area2', ''),
                'area2': article.get('area1', ''),
                'direction': article.get('direction', ''),
                'articleConfirmYmd': article.get('articleConfirmYmd', ''),
                'articleFeatureDesc': article.get('articleFeatureDesc', ''),
                'realtorName': article.get('realtorName', ''),
                'realtorId': article.get('realtorId', ''),
                'dong': article.get('dong', '')
            }
            merged_data[article_no] = row

    # CSV 파일로 저장
    with open('songdo_apartments_listings.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(merged_data.values())

    # 마지막 업데이트 시간 저장
    with open(get_resource_path('last_update.txt'), 'w', encoding='utf-8') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

def main():
    """메인 함수"""
    # Load environment variables
    load_dotenv()

    # Get authentication
    print("매물 수집을 시작합니다...")
    global auth_token, cookies, headers
    auth_token, cookies = get_naver_auth_and_cookies()
    if not auth_token or not cookies:
        print("인증 정보를 가져오지 못했습니다.")
        exit(1)

    # Set headers with the obtained auth token
    headers = {
        'Authorization': auth_token,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://new.land.naver.com/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }

    # 이전 데이터 로드
    previous_data = load_previous_data()
    
    # 송도 주요 단지 정보
    complexes = [
        {"id": "142817", "name": "더샵송도센텀하이브B", "dong": ""},
        {"id": "142816", "name": "송도센트로드", "dong": ""},
        {"id": "142815", "name": "송도아크베이", "dong": ""},
        {"id": "142814", "name": "센텀하이브 A동", "dong": ""}
    ]
    
    all_articles = []
    # Estimate total articles for progress bar (rough estimate)
    total_articles = len(complexes) * 50  # Assume ~50 articles per complex
    
    with tqdm(total=total_articles, desc="전체 진행률", unit="매물") as pbar:
        # 각 단지별로 매물 수집
        for complex_info in complexes:
            articles = fetch_by_complex_id(
                complex_info["id"],
                complex_info["name"],
                complex_info["dong"],
                pbar,
                previous_data
            )
            all_articles.extend(articles)
    
    # 수집된 매물 저장
    save_to_csv(all_articles, previous_data)
    
    print(f"총 {len(all_articles)}개의 새로운/업데이트된 매물 발견")
    print(f"전체 {len(previous_data)}개의 매물 정보를 저장했습니다.")

if __name__ == "__main__":
    main() 