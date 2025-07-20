# 부동산 매물 분석 시스템

네이버 부동산 매물 정보를 수집하고 분석하는 데스크톱 애플리케이션입니다.

## 주요 기능

- 매물 목록 조회 및 필터링
- 매물 상세 정보 확인
- 가격 비교 및 분석
- 선호도 기반 매물 추천
- 메모 기능
- 엑셀 다운로드

## 기술 스택

- Python 3.x
- PySide6 (Qt for Python)
- OpenAI GPT API
- Pandas

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/[username]/realestate.git
cd realestate
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\activate  # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
- `.env` 파일을 생성하고 다음 내용을 추가:
```
OPENAI_API_KEY=your_api_key_here
```

## 실행 방법

```bash
python main.py
```

## 주의사항

- 네이버 부동산 API 사용 시 적절한 딜레이를 두어 요청합니다.
- OpenAI API 키가 필요합니다.
- 데이터는 송도 지역 아파트 매물로 한정되어 있습니다.

## 라이선스

MIT License 