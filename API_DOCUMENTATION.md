# 공공데이터 OpenAPI 조회 서비스

## 가. API 서비스 개요
- 서비스명: 국토교통부_아파트 매매 실거래가 상세 자료
- 제공기관: 국토교통부
- API 버전: 1.0.0
- 서비스 설명: 「부동산 거래신고 등에 관한 법률」에 따라 신고된 자료로서 행정표준코드관리시스템(www.code.go.kr)의 법정동 코드 중 앞5자리(예시 : 서울 종로구 - 11110), 계약년월 6자리(예시 : 201801)로 해당 지역, 해당 기간의 아파트 매매 신고상세정보를 조회할 수 있습니다.
- Base URL: https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev
- 비용: 무료
- 트래픽 제한: 
  * 개발계정: 10,000회/일
  * 운영계정: 활용사례 등록시 신청하면 트래픽 증가 가능
- 승인유형:
  * 개발단계: 자동승인
  * 운영단계: 자동승인

※ 참고사항: 공개내용 중 개인정보보호를 위해 아파트의 층정보만 제공되며, 소유권 이전등기 완료된 건에 한하여 동정보가 추가적으로 공개됩니다.

## 나. 상세기능 목록
1. 아파트매매 실거래가 상세자료 조회 기능
   - 지역코드, 계약월 기준으로 매매 계약 자료 제공
   - 실거래가 상세 정보 포함 (거래금액, 건축년도, 면적, 층수 등)

## 다. 상세기능내역

### a) 상세기능정보
- 기능명: 아파트 매매 실거래가 공개 자료(상세)
- 오퍼레이션명: getRTMSDataSvcAptTradeDev
- 메서드: GET
- Content-Type: application/xml

### b) 요청 메시지 명세
| 항목명 | 항목구분 | 항목크기 | 타입 | 항목설명 |
|--------|----------|-----------|------|----------|
| serviceKey | 1 | 100 | String | 인증키 |
| LAWD_CD | 1 | 5 | String | 지역코드 (법정동 코드 앞 5자리) |
| DEAL_YMD | 1 | 6 | String | 계약월 (YYYYMM) |
| pageNo | 0 | 4 | String | 페이지번호 |
| numOfRows | 0 | 4 | String | 한 페이지 결과 수 |

### c) 응답 메시지 명세
| 항목명 | 항목구분 | 항목크기 | 타입 | 항목설명 |
|--------|----------|-----------|------|----------|
| resultCode | 1 | 2 | String | 결과코드 |
| resultMsg | 1 | 100 | String | 결과메시지 |
| dealAmount | 1 | 40 | String | 거래금액(만원) |
| buildYear | 1 | 4 | String | 건축년도 |
| dong | 1 | 40 | String | 법정동 |
| apartment | 1 | 40 | String | 아파트명 |
| area | 1 | 20 | String | 전용면적(㎡) |
| floor | 1 | 4 | String | 층수 |
| dealYear | 1 | 4 | String | 거래년도 |
| dealMonth | 1 | 2 | String | 거래월 |
| dealDay | 1 | 2 | String | 거래일 |

### d) 요청/응답 메시지 예제

#### 요청 예제
```
GET /1613000/RTMSDataSvcAptTradeDev/getAptTradeDev
?serviceKey=인증키
&LAWD_CD=11110
&DEAL_YMD=202401
&pageNo=1
&numOfRows=10
```

#### 응답 예제
```xml
<?xml version="1.0" encoding="UTF-8"?>
<response>
    <header>
        <resultCode>00</resultCode>
        <resultMsg>NORMAL SERVICE</resultMsg>
    </header>
    <body>
        <items>
            <item>
                <dealAmount>82,500</dealAmount>
                <buildYear>2010</buildYear>
                <dong>사직동</dong>
                <apartment>광화문풍림스페이스본</apartment>
                <area>84.97</area>
                <floor>18</floor>
                <dealYear>2024</dealYear>
                <dealMonth>01</dealMonth>
                <dealDay>15</dealDay>
            </item>
        </items>
        <numOfRows>10</numOfRows>
        <pageNo>1</pageNo>
        <totalCount>100</totalCount>
    </body>
</response>
```

## 󰊲 OpenAPI 에러 코드정리

| 에러코드 | 에러메시지 | 조치방안 |
|----------|------------|-----------|
| 00 | NORMAL SERVICE | 정상처리되었습니다 |
| 01 | APPLICATION ERROR | 시스템 에러가 발생하였습니다. 관리자에게 문의하세요. |
| 02 | DB ERROR | 데이터베이스 에러가 발생하였습니다. |
| 03 | NODATA ERROR | 데이터가 존재하지 않습니다. |
| 04 | HTTP ERROR | HTTP 에러가 발생하였습니다. |
| 05 | SERVICETIMEOUT ERROR | 서비스 연결 실패하였습니다. 잠시 후 다시 시도하세요. |
| 10 | INVALID REQUEST PARAMETER ERROR | 잘못된 요청 파라메터가 포함되었습니다. |
| 11 | NO MANDATORY REQUEST PARAMETERS ERROR | 필수 요청 파라메터가 누락되었습니다. |
| 12 | NO OPENAPI SERVICE ERROR | 해당 오픈API 서비스가 존재하지 않습니다. |
| 20 | SERVICE ACCESS DENIED ERROR | 서비스 접근이 거부되었습니다. |
| 21 | TEMPORARILY DISABLE THE SERVICEKEY ERROR | 일시적으로 사용할 수 없는 서비스 키입니다. |
| 22 | LIMITED NUMBER OF SERVICE REQUESTS EXCEEDS ERROR | 서비스 요청 제한 횟수를 초과하였습니다. |
| 30 | SERVICE KEY IS NOT REGISTERED ERROR | 등록되지 않은 서비스키입니다. |
| 31 | DEADLINE HAS EXPIRED ERROR | 기한이 만료된 서비스키입니다. |
| 32 | UNREGISTERED IP ERROR | 등록되지 않은 IP입니다. |
| 33 | UNSIGNED CALL ERROR | 서명되지 않은 호출입니다. | 