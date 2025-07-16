import requests
import json
import time
import csv
from datetime import datetime, timedelta
import asyncio
import aiohttp
from tqdm import tqdm
import os
import importlib.util

def get_naver_cookies_auto():
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
    except ImportError:
        print("selenium 패키지가 설치되어 있어야 자동 쿠키 갱신이 가능합니다. requirements.txt에 selenium을 추가하고 설치하세요.")
        return {}
    naver_id = os.getenv('NAVER_ID')
    naver_pw = os.getenv('NAVER_PW')
    if not naver_id or not naver_pw:
        print("환경변수 NAVER_ID, NAVER_PW가 필요합니다.")
        return {}
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    try:
        driver.get('https://nid.naver.com/nidlogin.login')
        driver.implicitly_wait(5)
        driver.find_element(By.ID, 'id').send_keys(naver_id)
        driver.find_element(By.ID, 'pw').send_keys(naver_pw)
        driver.find_element(By.ID, 'log.login').click()
        driver.implicitly_wait(5)
        driver.get('https://land.naver.com/')
        driver.implicitly_wait(5)
        cookies = driver.get_cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        needed_keys = [
            'NNB', 'nhn.realestate.article.rlet_type_cd', 'nhn.realestate.article.trade_type_cd',
            'nhn.realestate.article.ipaddress_city', 'landHomeFlashUseYn', 'NAC', 'NACT',
            'REALESTATE', 'SRT30', 'SRT5', 'JSESSIONID', 'NFS', 'NID_AUT', 'NID_SES'
        ]
        filtered = {k: v for k, v in cookie_dict.items() if k in needed_keys}
        return filtered
    except Exception as e:
        print(f"네이버 자동 로그인/쿠키 추출 실패: {e}")
        return {}
    finally:
        driver.quit()

def generate_jwt_token():
    jwt_spec = importlib.util.find_spec("jwt")
    if jwt_spec is None:
        import subprocess
        subprocess.check_call(["python", "-m", "pip", "install", "PyJWT"])
    import jwt
    current_time = int(time.time())
    token = jwt.encode(
        {
            "id": "REALESTATE",
            "iat": current_time,
            "exp": current_time + 10800  # 3 hours
        },
        "naver_land_secret_key_2024",
        algorithm="HS256"
    )
    return f"Bearer {token}"

# 자동 쿠키 갱신 사용
cookies = get_naver_cookies_auto()

# 고정된 헤더 설정
headers = {
    'Authorization': generate_jwt_token(),
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://new.land.naver.com/offices?ms=37.3972977,126.6285562,16&a=PRE:OPST:OBYG&e=RETAIL',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

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

async def fetch_by_complex_id(session, complex_id, complex_name, dong, pbar, previous_data):
    """단지 코드로 매물 검색 (비동기)"""
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
            async with session.get(url, headers=headers, cookies=cookies) as response:
                if response.status != 200:
                    print(f"\n❌ {complex_name} 요청 실패 (페이지 {page}): {response.status}")
                    break

                data = await response.json()
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
                await asyncio.sleep(0.3)  # 딜레이 시간 추가 감소

        except Exception as e:
            print(f"\n❌ {complex_name} 오류 발생 (페이지 {page}): {str(e)}")
            break

    return all_articles

def is_centum_a(lat, lng):
    """센텀하이브 A동 좌표 체크"""
    target_lat = 37.3968392
    target_lng = 126.6314085
    threshold = 0.0003
    return abs(lat - target_lat) < threshold and abs(lng - target_lng) < threshold

async def fetch_centum_a(session, pbar, previous_data):
    """센텀하이브 A동 매물 수집 (좌표 기반) (비동기)"""
    all_articles = []
    page = 1
    max_pages = 50  # 최대 페이지 수 제한
    no_new_data_count = 0
    last_update = get_last_update_time()

    while page <= max_pages:
        url = (
            "https://new.land.naver.com/api/articles"
            "?cortarNo=2818510600"
            "&order=rank"
            "&realEstateType=SG:SMS:GJCG:APTHGJ:GM:TJ"
            "&rentPriceMin=0&rentPriceMax=900000000"
            "&priceMin=0&priceMax=900000000"
            "&areaMin=0&areaMax=300"
            "&priceType=RETAIL"
            f"&page={page}"
        )

        try:
            async with session.get(url, headers=headers, cookies=cookies) as response:
                if response.status != 200:
                    print(f"\n❌ 센텀하이브 A동 요청 실패 (페이지 {page}): {response.status}")
                    break

                data = await response.json()
                articles = data.get("articleList", [])

                if not articles:
                    break

                new_articles = []
                for article in articles:
                    lat = float(article.get('latitude', 0))
                    lng = float(article.get('longitude', 0))
                    article_no = article.get('articleNo')
                    
                    if is_centum_a(lat, lng):
                        confirm_date = parse_date(article.get('articleConfirmYmd', ''))
                        
                        if (article_no not in previous_data or 
                            confirm_date > last_update):
                            article['complexName'] = '더샵송도센텀하이브A'
                            article['dong'] = 'A동'
                            new_articles.append(article)

                if new_articles:
                    all_articles.extend(new_articles)
                    pbar.update(len(new_articles))
                    no_new_data_count = 0
                else:
                    no_new_data_count += 1

                if no_new_data_count >= 3:
                    break

                page += 1
                await asyncio.sleep(0.3)

        except Exception as e:
            print(f"\n❌ 센텀하이브 A동 오류 발생 (페이지 {page}): {str(e)}")
            break

    return all_articles

def save_to_csv(all_articles, previous_data):
    """매물 정보를 CSV 파일에 저장"""
    filename = "songdo_apartments_listings.csv"
    
    # 이전 데이터와 새로운 데이터 병합
    merged_data = previous_data.copy()
    for article in all_articles:
        merged_data[article['articleNo']] = article

    fieldnames = [
        'complexName', 'articleNo', 'articleName', 'tradeTypeName',
        'dealOrWarrantPrc', 'rentPrc', 'floorInfo', 'area1', 'area2',
        'direction', 'articleConfirmYmd', 'articleFeatureDesc',
        'realtorName', 'realtorId', 'dong'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for article in merged_data.values():
            row = {
                'complexName': article.get('complexName', ''),
                'articleNo': article.get('articleNo', ''),
                'articleName': article.get('articleName', ''),
                'tradeTypeName': article.get('tradeTypeName', ''),
                'dealOrWarrantPrc': article.get('dealOrWarrantPrc', ''),
                'rentPrc': article.get('rentPrc', ''),
                'floorInfo': article.get('floorInfo', ''),
                'area1': article.get('area1', ''),
                'area2': article.get('area2', ''),
                'direction': article.get('direction', ''),
                'articleConfirmYmd': article.get('articleConfirmYmd', ''),
                'articleFeatureDesc': article.get('articleFeatureDesc', ''),
                'realtorName': article.get('realtorName', ''),
                'realtorId': article.get('realtorId', ''),
                'dong': article.get('dong', '')
            }
            writer.writerow(row)

async def main():
    # 이전 데이터 로드
    previous_data = load_previous_data()
    print("🔍 매물 수집을 시작합니다...")
    
    async with aiohttp.ClientSession() as session:
        with tqdm(desc="전체 진행률", unit="매물") as pbar:
            tasks = [
                fetch_by_complex_id(session, "142817", "더샵송도센텀하이브B", "B동", pbar, previous_data),
                fetch_by_complex_id(session, "146304", "송도아크베이", "", pbar, previous_data),
                fetch_by_complex_id(session, "27145", "송도센트로드", "", pbar, previous_data),
                fetch_centum_a(session, pbar, previous_data)
            ]
            
            results = await asyncio.gather(*tasks)
            
            all_articles = []
            for articles in results:
                all_articles.extend(articles)
    
    print(f"\n✅ 총 {len(all_articles)}개의 새로운/업데이트된 매물 발견")
    save_to_csv(all_articles, previous_data)
    print(f"✅ 전체 {len(previous_data) + len(all_articles)}개의 매물 정보를 저장했습니다.")

    # 마지막 업데이트 시간 저장
    with open('last_update.txt', 'w', encoding='utf-8') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == "__main__":
    asyncio.run(main()) 