import os
from dotenv import load_dotenv

def get_naver_auth_and_cookies():
    load_dotenv()
    cookie_str = os.getenv('NAVER_COOKIE', '')
    if not cookie_str:
        print("환경변수 NAVER_COOKIE가 필요합니다.")
        return None, None
    
    # Parse cookie string into dictionary
    cookies = {}
    for item in cookie_str.split(';'):
        item = item.strip()
        if not item:
            continue
        if '=' not in item:
            continue
        name, value = item.split('=', 1)
        cookies[name.strip()] = value.strip()
    
    # Generate authorization token
    auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTI2NzU4MTIsImV4cCI6MTc1MjY4NjYxMn0.s8tfWUqWUlBJl9iYnf88fCFeEK6cfdb3vpfIXPKWimA"
    
    return auth_token, cookies 