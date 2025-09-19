#!/usr/bin/env python3
"""
API 서버 헬스 체크
"""

import requests
import json

def test_api_health():
    """API 서버 헬스 체크"""
    print("🔍 API 서버 헬스 체크...")
    
    try:
        # 헬스 체크
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"📊 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 서버 정상 작동!")
            print(f"🔧 모델 상태:")
            print(f"  - Whisper: {data.get('models', {}).get('whisper_model', 'N/A')}")
            print(f"  - ERP Extractor: {data.get('models', {}).get('erp_extractor', 'N/A')}")
            print(f"  - Supabase: {data.get('models', {}).get('supabase', 'N/A')}")
        else:
            print(f"❌ API 서버 문제: {response.status_code}")
            print(f"응답: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API 서버에 연결할 수 없습니다.")
        return False
    except Exception as e:
        print(f"❌ 헬스 체크 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_api_health()

