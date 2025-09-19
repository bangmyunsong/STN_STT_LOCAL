#!/usr/bin/env python3
"""
/api/statistics 엔드포인트 테스트
"""

import requests
import time

def test_statistics_api():
    """statistics API 테스트"""
    print("🔍 /api/statistics API 테스트...")
    
    try:
        # API 서버가 시작될 때까지 잠시 대기
        time.sleep(3)
        
        # statistics API 호출
        response = requests.get("http://localhost:8000/api/statistics", timeout=10)
        
        print(f"📊 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API 호출 성공!")
            data = response.json()
            print(f"응답 데이터: {data}")
        elif response.status_code == 503:
            print("❌ 503 Service Unavailable - Supabase 연결 문제")
            print(f"응답 내용: {response.text}")
        else:
            print(f"⚠️ 예상치 못한 상태 코드: {response.status_code}")
            print(f"응답 내용: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
    except requests.exceptions.Timeout:
        print("❌ API 요청 시간 초과")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    test_statistics_api()

