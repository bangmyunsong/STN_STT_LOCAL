#!/usr/bin/env python3
"""
React Admin이 호출하는 주요 API들 테스트
"""

import requests
import json
import time

def test_react_admin_apis():
    """React Admin이 사용하는 주요 API들을 테스트"""
    print("🔍 React Admin API 테스트 시작...")
    
    base_url = "http://localhost:8000"
    test_results = {}
    
    # 테스트할 API 목록
    apis_to_test = [
        ("/health", "헬스 체크"),
        ("/api/statistics", "시스템 통계"),
        ("/api/audio-files", "음성 파일 목록"),
        ("/api/sessions?limit=5", "STT 세션 목록"),
        ("/api/extractions?limit=5", "ERP 추출 결과"),
        ("/api/register-logs?limit=5", "ERP 등록 로그"),
        ("/api/directory-summary", "디렉토리 요약"),
        ("/api/file-processing-status?limit=5", "파일 처리 상태"),
        ("/api/processing-summary-enhanced", "향상된 처리 요약")
    ]
    
    for endpoint, description in apis_to_test:
        print(f"\n📋 테스트: {description} ({endpoint})")
        
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                print(f"  ✅ 성공: 200 OK")
                data = response.json()
                if 'status' in data:
                    print(f"  📊 상태: {data['status']}")
                if 'message' in data:
                    print(f"  💬 메시지: {data['message'][:100]}...")
                test_results[endpoint] = "SUCCESS"
                
            elif response.status_code == 503:
                print(f"  ⚠️ 503 Service Unavailable")
                print(f"  📝 응답: {response.text}")
                test_results[endpoint] = "503_ERROR"
                
            elif response.status_code == 500:
                print(f"  ❌ 500 Internal Server Error")
                print(f"  📝 응답: {response.text}")
                test_results[endpoint] = "500_ERROR"
                
            else:
                print(f"  ⚠️ 예상치 못한 상태 코드: {response.status_code}")
                print(f"  📝 응답: {response.text[:200]}...")
                test_results[endpoint] = f"HTTP_{response.status_code}"
                
        except requests.exceptions.ConnectionError:
            print(f"  ❌ 연결 실패: API 서버가 실행 중인지 확인")
            test_results[endpoint] = "CONNECTION_ERROR"
            
        except requests.exceptions.Timeout:
            print(f"  ❌ 타임아웃: API 응답 시간 초과")
            test_results[endpoint] = "TIMEOUT"
            
        except Exception as e:
            print(f"  ❌ 예외 발생: {e}")
            test_results[endpoint] = f"EXCEPTION: {str(e)}"
    
    # 결과 요약
    print(f"\n🎯 테스트 결과 요약:")
    print("="*50)
    
    success_count = 0
    error_count = 0
    
    for endpoint, result in test_results.items():
        status_icon = "✅" if result == "SUCCESS" else "❌"
        print(f"{status_icon} {endpoint}: {result}")
        
        if result == "SUCCESS":
            success_count += 1
        else:
            error_count += 1
    
    print("="*50)
    print(f"성공: {success_count}개, 실패: {error_count}개")
    
    if error_count > 0:
        print(f"\n💡 해결 방안:")
        if any("503" in result for result in test_results.values()):
            print("- 503 오류: Supabase 연결 문제 (이미 수정된 상태)")
        if any("CONNECTION_ERROR" in result for result in test_results.values()):
            print("- 연결 오류: API 서버가 실행 중인지 확인")
        if any("500" in result for result in test_results.values()):
            print("- 500 오류: 서버 내부 오류, 로그 확인 필요")
    
    return test_results

if __name__ == "__main__":
    # API 서버가 시작될 때까지 잠시 대기
    print("⏳ API 서버 시작 대기 중...")
    time.sleep(3)
    
    test_react_admin_apis()

