import os
import sys
import shutil
from datetime import datetime

VERSION = "1.0.0"  # 버전 정보

def create_env_file(directory):
    """실제 환경 변수 파일 생성"""
    env_content = """# 네이버 부동산 API 인증 정보
NAVER_LAND_AUTHORIZATION=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTE4NzE1MDksImV4cCI6MTc1MTg4MjMwOX0.vVPIKWIUS6_1USYaEEIPXJij0ngOQksyltA6hmMR0ZY
NAVER_LAND_COOKIES={"NNB":"ZNCS4KNQE3UWK","nhn.realestate.article.rlet_type_cd":"A01","nhn.realestate.article.trade_type_cd":"\"\"","nhn.realestate.article.ipaddress_city":"4100000000","_fwb":"9WICy4Co9xy1YQrJKdwWu.1751864932684","landHomeFlashUseYn":"Y","NAC":"aVAdBsAI3X4eB","NACT":"1","BUC":"oTUiNsBzMsU-7Mo_Y1ucbKECviqegSsrk7xPg7w1nTo=","PROP_TEST_KEY":"1751871509926.82f214590426eda9505d3faed7a0846288c2b969d3a5fc41a5f6d0393d2c1f85","PROP_TEST_ID":"8179ccccf6b241418afdecfa5b0fde3aee0ff90e36b5ad36c9f730de13bef407","_fwb":"9WICy4Co9xy1YQrJKdwWu.1751864932684","REALESTATE":"Mon Jul 07 2025 15:58:29 GMT+0900 (Korean Standard Time)","SRT30":"1751866802","SRT5":"1751871319"}

# OpenAI API 키 (선택사항)
OPENAI_API_KEY=
"""
    env_path = os.path.join(directory, '.env')
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)

def create_readme():
    """간단한 설치 및 사용 방법 README 생성"""
    readme = """# 부동산 매물 리스트 뷰어 (macOS)

## 설치 방법

1. `부동산매물뷰어.app`을 Applications 폴더나 원하는 위치로 복사합니다.
2. 처음 실행 시 "확인되지 않은 개발자" 경고가 표시될 수 있습니다:
   - Finder에서 앱을 우클릭(또는 Control+클릭)하고 "열기"를 선택합니다.
   - "열기" 버튼을 클릭하여 앱을 실행합니다.

## 사용 방법

1. `부동산매물뷰어.app`을 더블클릭하여 실행합니다.
2. "데이터 업데이트" 버튼을 클릭하여 최신 매물을 가져옵니다.
3. 매물 목록에서 원하는 매물을 클릭하여 상세 정보를 확인합니다.
4. 필터와 정렬 기능을 사용하여 원하는 매물을 찾습니다:
   - 전세/월세 거래유형 필터
   - 가격 정렬 (보증금/매매가, 월세)
   - 엑셀 다운로드 기능

## 주의사항

- 처음 실행 시 "확인되지 않은 개발자의 앱" 경고가 표시됩니다.
  이는 앱이 Apple 개발자 인증서로 서명되지 않았기 때문이며, 위의 설치 방법에 따라 실행할 수 있습니다.
- 네트워크 연결이 필요하며, 처음 실행 시 데이터를 가져오는 데 시간이 걸릴 수 있습니다.

## 문제 해결

1. 프로그램이 실행되지 않는 경우:
   - 네트워크 연결 상태 확인
   - "데이터 업데이트" 버튼을 다시 클릭

2. 보안 경고가 계속 표시되는 경우:
   - Finder에서 우클릭 → "열기" 사용

버전: """ + VERSION
    with open('README_MACOS.txt', 'w', encoding='utf-8') as f:
        f.write(readme)

def main():
    # 빌드 시작 시간
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    print(f"빌드 시작: {start_time}")

    # 필요한 파일들 생성
    create_readme()
    create_env_file('.')  # Create .env file in current directory

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
        ('README_MACOS.txt', '.'),
        ('.env', '.'),  # Add .env file to the data files list
        ('.env', '.')  # Add .env file to the data files list
    ]

    # PyInstaller 명령어 생성
    app_name = f"부동산매물뷰어_v{VERSION}"
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
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
        '--hidden-import=requests',
        '--hidden-import=dotenv',
        '--hidden-import=openai',
        '--hidden-import=aiohttp',
        '--hidden-import=tqdm',
        '--hidden-import=numpy',
        'main.py'
    ])

    # 실행
    import subprocess
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
        app_path = os.path.join(dist_dir, f'{app_name}.app')
        release_name = f'부동산매물뷰어_macOS_v{VERSION}_{timestamp}'
        print("\n생성된 파일:")
        print(f"1. {app_path}")
        print("2. README_MACOS.txt")
        
        # 배포 폴더 생성
        release_dir = release_name
        if os.path.exists(release_dir):
            shutil.rmtree(release_dir)
        os.makedirs(release_dir)
        
        # 필요한 파일들 복사
        shutil.copytree(app_path, os.path.join(release_dir, f'{app_name}.app'))
        shutil.copy('README_MACOS.txt', release_dir)
        shutil.copy('.env', release_dir) # Copy .env file to release directory
        
        # 배포용 zip 파일 생성
        shutil.make_archive(release_name, 'zip', release_dir)
        
        print(f"\n배포 파일이 생성되었습니다:")
        print(f"1. {release_name}.zip")
        print(f"2. {release_dir}/ (폴더)")

if __name__ == "__main__":
    main() 