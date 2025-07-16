import os
import sys
import shutil
from datetime import datetime, timedelta
import subprocess
import platform
import time
import base64
import pickle
import json
import importlib.util

VERSION = "1.0.0"  # 버전 정보

def ensure_jwt_installed():
    """Ensure PyJWT is installed and return the jwt module"""
    jwt_spec = importlib.util.find_spec("jwt")
    if jwt_spec is None:
        print("PyJWT not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyJWT"])
    jwt = importlib.import_module("jwt")
    return jwt

def generate_secret_key():
    """Generate a secure secret key for JWT signing"""
    return base64.b64encode(os.urandom(32)).decode('utf-8')

def create_env_file(directory):
    """실제 환경 변수 파일 생성"""
    try:
        # Import PyJWT
        jwt = ensure_jwt_installed()

        # Generate a new JWT token that will be valid for 3 hours from now
        secret_key = generate_secret_key()
        current_time = int(time.time())
        token = jwt.encode(
            {
                "id": "REALESTATE",
                "iat": current_time,
                "exp": current_time + 10800  # 3 hours
            },
            "naver_land_secret_key_2024",  # Updated secret key
            algorithm="HS256"
        )
    except Exception as e:
        print(f"Warning: Failed to generate JWT token: {e}")
        print("Using fallback token...")
        # Use a fallback token if JWT generation fails
        secret_key = generate_secret_key()
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3MDAwMDAwMDAsImV4cCI6MTcwMDAxMDAwMH0.KwYXPGCsSelmJRHhMQZrUFZZlUa4Q9jQ8eUl3Yx0Zk8"
    
    # Generate current timestamp in Korean time
    kst_time = datetime.now() + timedelta(hours=9)  # Convert to KST
    realestate_cookie = kst_time.strftime("%a %b %d %Y %H:%M:%S GMT+0900 (Korean Standard Time)")
    
    # Update cookies with current timestamp
    env_content = (
        "# 네이버 부동산 API 인증 정보\n"
        f"NAVER_LAND_AUTHORIZATION=Bearer {token}\n"
        f"NAVER_LAND_COOKIES={{\"NNB\":\"ZNCS4KNQE3UWK\",\"nhn.realestate.article.rlet_type_cd\":\"A01\","
        f"\"nhn.realestate.article.trade_type_cd\":\"\\\"\\\"\",\"nhn.realestate.article.ipaddress_city\":\"4100000000\","
        f"\"landHomeFlashUseYn\":\"Y\",\"NAC\":\"aVAdBsAI3X4eB\",\"NACT\":\"1\","
        f"\"REALESTATE\":\"{realestate_cookie}\",\"SRT30\":\"{current_time}\",\"SRT5\":\"{current_time + 300}\","
        f"\"JSESSIONID\":\"naver_land_{current_time}\","
        f"\"NFS\":\"2\",\"NID_AUT\":\"naver_land_auth_{current_time}\","
        f"\"NID_SES\":\"AAABpYxHUEH0/OJ6QgEbUVzHj8Zr1qSMxwNf+XJ4\"}}\n\n"
        "# OpenAI API 키 (선택사항)\n"
        "OPENAI_API_KEY=\n\n"
        f"# JWT Secret Key\nJWT_SECRET_KEY={secret_key}\n"
    )
    
    env_path = os.path.join(directory, '.env')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)

def create_readme():
    """설치 및 사용 방법 README 생성"""
    readme_content = (
        "# 부동산 매물 리스트 뷰어 (Windows)\n\n"
        "## 설치 방법\n\n"
        "1. ZIP 파일의 압축을 해제합니다.\n"
        "2. 압축 해제된 폴더에서 `부동산매물뷰어.exe`를 실행합니다.\n"
        "   - Windows 보안 경고가 표시되면 \"추가 정보\" → \"실행\"을 클릭합니다.\n\n"
        "## 사용 방법\n\n"
        "1. 프로그램이 시작되면 자동으로 최신 매물 데이터를 불러옵니다.\n"
        "2. 매물 목록에서 원하는 매물을 클릭하여 상세 정보를 확인합니다.\n"
        "3. 다음 기능들을 활용하여 매물을 찾아보세요:\n"
        "   - 전세/월세/매매 거래유형 필터\n"
        "   - 가격순 정렬\n"
        "   - 면적순 정렬\n"
        "   - 엑셀 다운로드\n"
        "   - 매물 저장 및 메모 기능\n\n"
        "## 주의사항\n\n"
        "- 처음 실행 시 Windows 보안 경고는 정상입니다.\n"
        "- 프로그램이 있는 폴더에 쓰기 권한이 필요합니다.\n"
        "- 인터넷 연결이 필요합니다.\n\n"
        "## 문제 해결\n\n"
        "1. 프로그램이 실행되지 않는 경우:\n"
        "   - 압축을 완전히 해제했는지 확인\n"
        "   - 폴더에 쓰기 권한이 있는지 확인\n"
        "   - 바이러스 백신 프로그램이 실행을 차단하는지 확인\n\n"
        "2. 데이터가 표시되지 않는 경우:\n"
        "   - 인터넷 연결 확인\n"
        "   - \"데이터 업데이트\" 버튼 클릭\n\n"
        f"버전: {VERSION}"
    )
    with open('README_WINDOWS.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)

def main():
    # Windows 환경 확인
    if platform.system() != 'Windows':
        print("이 스크립트는 Windows 환경에서만 실행할 수 있습니다.")
        return

    # 빌드 시작 시간
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    print(f"빌드 시작: {start_time}")

    # 필요한 파일들 생성
    create_readme()
    create_env_file('.')  # Create .env file in current directory

    # 빈 데이터 파일 생성
    if not os.path.exists('property_notes.json'):
        with open('property_notes.json', 'w', encoding='utf-8') as f:
            f.write('{}')
    if not os.path.exists('saved_properties.json'):
        with open('saved_properties.json', 'w', encoding='utf-8') as f:
            f.write('{}')
    if not os.path.exists('description_cache.json'):
        with open('description_cache.json', 'w', encoding='utf-8') as f:
            f.write('{}')
    if not os.path.exists('api_cache.pkl'):
        with open('api_cache.pkl', 'wb') as f:
            pickle.dump({}, f)
    if not os.path.exists('last_update.txt'):
        with open('last_update.txt', 'w', encoding='utf-8') as f:
            f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 데이터 파일 목록
    data_files = [
        ('songdo_apartments_listings.csv', '.'),
        ('songdo_officetel_listings.csv', '.'),
        ('송도_매물.json', '.'),
        ('saved_properties.json', '.'),
        ('property_notes.json', '.'),
        ('api_cache.pkl', '.'),
        ('description_cache.json', '.'),
        ('last_update.txt', '.'),
        ('README_WINDOWS.txt', '.'),
        ('.env', '.')  # Add .env file to the data files list
    ]

    # PyInstaller 명령어 생성
    app_name = f"부동산매물뷰어_v{VERSION}"
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--clean',  # Clean PyInstaller cache
        '--log-level=WARN',  # Only show warnings and errors
        f'--name={app_name}',
    ]

    # 데이터 파일 추가
    for data_file, dest in data_files:
        if os.path.exists(data_file):
            cmd.append(f'--add-data={data_file}{os.pathsep}{dest}')

    # 필수 패키지 추가
    cmd.extend([
        '--hidden-import=pandas',
        '--hidden-import=PySide6',
        '--hidden-import=PySide6.QtCore',
        '--hidden-import=PySide6.QtWidgets',
        '--hidden-import=PySide6.QtGui',
        '--hidden-import=requests',
        '--hidden-import=python-dotenv',
        '--hidden-import=openai',
        '--hidden-import=aiohttp',
        '--hidden-import=tqdm',
        '--hidden-import=numpy',
        '--hidden-import=openpyxl',
        '--hidden-import=jwt',
        '--hidden-import=PyJWT',
        '--hidden-import=base64',
        '--hidden-import=pickle',
        '--hidden-import=json',
        '--hidden-import=seleniumwire',
        '--hidden-import=blinker',
        'main.py'
    ])

    # 실행
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("빌드 실패!")
        return

    # 빌드 완료 시간
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n빌드 완료: {end_time}")
    print(f"소요 시간: {duration}")

    # 결과 파일 정리
    dist_dir = 'dist'
    if os.path.exists(dist_dir):
        app_path = os.path.join(dist_dir, app_name)
        release_name = f'부동산매물뷰어_Windows_v{VERSION}_{timestamp}'
        print("\n생성된 파일:")
        print(f"1. {app_path}")
        print(f"2. {release_name}.zip (배포용)")
        
        # 배포 폴더 생성
        release_dir = release_name
        if os.path.exists(release_dir):
            shutil.rmtree(release_dir)
        os.makedirs(release_dir)
        
        # 필요한 파일들 복사
        shutil.copytree(app_path, os.path.join(release_dir, app_name))
        
        # 배포용 zip 파일 생성
        shutil.make_archive(release_name, 'zip', release_dir)
        
        print(f"\n배포 파일이 생성되었습니다:")
        print(f"1. {release_name}.zip")
        print(f"2. {release_dir}/ (폴더)")

if __name__ == "__main__":
    main() 