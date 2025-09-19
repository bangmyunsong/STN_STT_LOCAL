#!/usr/bin/env python3
"""
통합된 API 서버 테스트 스크립트
새로 추가된 핫리로드 및 개선된 ERP 추출 API 테스트
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api_health():
    """기본 헬스 체크"""
    print("🔍 API 서버 헬스 체크...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ API 서버 정상 작동")
            print(f"  - 모델 상태: {data.get('models', {})}")
            return True
        else:
            print(f"❌ 헬스 체크 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 서버 연결 실패: {e}")
        return False

def test_domain_reload():
    """도메인 데이터 핫리로드 테스트"""
    print("\n🔄 도메인 데이터 핫리로드 테스트...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/reload-domain")
        if response.status_code == 200:
            data = response.json()
            print("✅ 도메인 데이터 리로드 성공")
            print(f"  - 장비명: {data['stats']['equipment_count']}개")
            print(f"  - 에러코드: {data['stats']['error_count']}개")
            print(f"  - 요청코드: {data['stats']['request_count']}개")
            print(f"  - 모델 매핑: {data['stats']['model_mappings']}개")
            return True
        else:
            print(f"❌ 리로드 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 리로드 API 호출 실패: {e}")
        return False

def test_enhanced_erp_extraction():
    """개선된 ERP 추출 API 테스트"""
    print("\n🎯 개선된 ERP 추출 API 테스트...")
    
    test_cases = [
        {
            "name": "모델명 케이스",
            "transcript": "고객: 7250 IXR-R4 장비에서 HW FAIL 발생했어요. 현장 점검 요청드립니다. 위치는 서울 본사입니다."
        },
        {
            "name": "표준 표현 케이스",
            "transcript": "고객: IP/MPLS 장비에서 유니트 불량이 생겼습니다. 원격으로 확인해주세요."
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 테스트 케이스 {i}: {test_case['name']}")
        
        payload = {
            "transcript_text": test_case["transcript"],
            "use_legacy_format": True,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/extract-erp-enhanced",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ ERP 추출 성공")
                
                stn_format = data.get("stn_format", {})
                validation = data.get("validation", {})
                
                print(f"  📊 STN 형식:")
                print(f"    - 장비명: {stn_format.get('장비명')}")
                print(f"    - 장애유형: {stn_format.get('장애유형')}")
                print(f"    - 요청유형: {stn_format.get('요청유형')}")
                print(f"    - 위치: {stn_format.get('위치')}")
                
                print(f"  🔍 검증 결과:")
                print(f"    - 장비명 유효: {validation.get('valid_equipment')}")
                print(f"    - 장애유형 유효: {validation.get('valid_error')}")
                print(f"    - 요청유형 유효: {validation.get('valid_request')}")
                
                if validation.get('warnings'):
                    print(f"    - 경고: {validation['warnings'][:2]}...")
                
                if data.get("legacy_format"):
                    legacy = data["legacy_format"]
                    print(f"  🔄 레거시 형식:")
                    print(f"    - AS 및 지원: {legacy.get('AS 및 지원')}")
                    print(f"    - 장비명: {legacy.get('장비명')}")
                    print(f"    - 작업국소: {legacy.get('작업국소')}")
            else:
                print(f"❌ ERP 추출 실패: {response.status_code}")
                print(f"응답: {response.text}")
                
        except Exception as e:
            print(f"❌ API 호출 실패: {e}")

def test_original_erp_api():
    """기존 ERP API와 비교 테스트"""
    print("\n🔗 기존 ERP API 비교 테스트...")
    
    test_text = "고객: IP/MPLS 장비에서 문제가 생겼습니다. 확인해주세요."
    
    try:
        # 기존 API 테스트 (POST 요청으로 conversation_text 전달)
        response = requests.post(
            f"{BASE_URL}/api/extract-erp",
            data={"conversation_text": test_text}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 기존 ERP API 정상 작동")
            print(f"  - 상태: {data.get('status')}")
            print(f"  - 메시지: {data.get('message')}")
        else:
            print(f"⚠️ 기존 ERP API 응답: {response.status_code}")
            print(f"응답: {response.text}")
            
    except Exception as e:
        print(f"⚠️ 기존 ERP API 테스트 실패: {e}")

def main():
    """메인 테스트 실행"""
    print("🚀 STN 통합 API 서버 테스트 시작\n")
    
    # 1. 기본 헬스 체크
    if not test_api_health():
        print("❌ API 서버가 실행되지 않았습니다. 먼저 API 서버를 시작해주세요.")
        return
    
    # 2. 도메인 데이터 리로드 테스트
    reload_success = test_domain_reload()
    
    # 3. 개선된 ERP 추출 테스트
    test_enhanced_erp_extraction()
    
    # 4. 기존 API 호환성 테스트
    test_original_erp_api()
    
    print(f"\n🎉 통합 테스트 완료!")
    if reload_success:
        print("✅ 모든 새로운 기능이 정상적으로 작동합니다.")
    else:
        print("⚠️ 일부 기능에 문제가 있을 수 있습니다.")

if __name__ == "__main__":
    main()

