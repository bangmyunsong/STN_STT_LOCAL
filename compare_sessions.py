#!/usr/bin/env python3
"""
STT 세션 비교 체크 프로그램
세션 43 (LARGE) vs 세션 44 (MEDIUM) 모델별 장비명 도출 차이 분석
"""

import requests
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

def check_api_health():
    """API 서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API 서버 연결 성공")
            return True
        else:
            print(f"❌ API 서버 연결 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 서버 연결 오류: {e}")
        return False

def get_session_data(session_id):
    """특정 세션의 데이터를 가져옵니다"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}")
        if response.status_code == 200:
            data = response.json()
            return data.get('session', {}), data.get('erp_extraction', {})
        else:
            print(f"❌ 세션 {session_id} 조회 실패: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"❌ 세션 {session_id} 조회 오류: {e}")
        return None, None

def analyze_text_for_equipment(text):
    """텍스트에서 장비명 관련 키워드를 분석합니다"""
    if not text:
        return {"found": False, "keywords": []}
    
    # 장비명 관련 키워드들
    equipment_keywords = [
        'ROADN', 'ROADM', '로드엔', '로드엠', '로드', 'ROAD'
    ]
    
    found_keywords = []
    for keyword in equipment_keywords:
        if keyword.lower() in text.lower():
            found_keywords.append(keyword)
    
    return {
        "found": len(found_keywords) > 0,
        "keywords": found_keywords
    }

def compare_sessions(session_id1, session_id2):
    """두 세션을 상세 비교합니다"""
    print(f"\n{'='*60}")
    print(f"🔍 세션 {session_id1} vs 세션 {session_id2} 상세 비교")
    print(f"{'='*60}")
    
    # 세션 데이터 가져오기
    session1, erp1 = get_session_data(session_id1)
    session2, erp2 = get_session_data(session_id2)
    
    if not session1 or not session2:
        print("❌ 세션 데이터를 가져올 수 없습니다.")
        return
    
    # 기본 정보 비교
    print(f"\n📊 기본 정보 비교:")
    print(f"세션 {session_id1}: 모델={session1.get('model_name', 'N/A')}, 파일={session1.get('file_name', 'N/A')}")
    print(f"세션 {session_id2}: 모델={session2.get('model_name', 'N/A')}, 파일={session2.get('file_name', 'N/A')}")
    
    # STT 텍스트 비교
    text1 = session1.get('transcript', '')
    text2 = session2.get('transcript', '')
    
    print(f"\n📝 STT 텍스트 비교:")
    print(f"세션 {session_id1} 길이: {len(text1)}자")
    print(f"세션 {session_id2} 길이: {len(text2)}자")
    
    # 텍스트 미리보기
    print(f"\n세션 {session_id1} 미리보기:")
    print(f"  {text1[:150]}...")
    print(f"\n세션 {session_id2} 미리보기:")
    print(f"  {text2[:150]}...")
    
    # 장비명 키워드 분석
    analysis1 = analyze_text_for_equipment(text1)
    analysis2 = analyze_text_for_equipment(text2)
    
    print(f"\n🔧 장비명 키워드 분석:")
    print(f"세션 {session_id1}: {'✅' if analysis1['found'] else '❌'} - {analysis1['keywords']}")
    print(f"세션 {session_id2}: {'✅' if analysis2['found'] else '❌'} - {analysis2['keywords']}")
    
    # ERP 추출 결과 비교
    print(f"\n📋 ERP 추출 결과 비교:")
    erp_fields = ['장비명', '기종명', '장애유형', '요청유형', '요청자', '시스템명(고객사명)']
    
    for field in erp_fields:
        value1 = erp1.get(field, 'N/A')
        value2 = erp2.get(field, 'N/A')
        status1 = "✅" if value1 != 'N/A' and value1 != '정보 없음' else "❌"
        status2 = "✅" if value2 != 'N/A' and value2 != '정보 없음' else "❌"
        
        print(f"  {field}:")
        print(f"    세션 {session_id1}: {status1} {value1}")
        print(f"    세션 {session_id2}: {status2} {value2}")
    
    # 차이점 요약
    print(f"\n📈 차이점 요약:")
    
    # 장비명 도출 차이
    equipment1 = erp1.get('장비명', 'N/A')
    equipment2 = erp2.get('장비명', 'N/A')
    
    if equipment1 != 'N/A' and equipment1 != '정보 없음' and (equipment2 == 'N/A' or equipment2 == '정보 없음'):
        print(f"  🚨 장비명 도출 차이 발견!")
        print(f"    - 세션 {session_id1} ({session1.get('model_name')}): {equipment1}")
        print(f"    - 세션 {session_id2} ({session2.get('model_name')}): {equipment2}")
        
        # 원인 분석
        if analysis1['found'] and not analysis2['found']:
            print(f"  💡 원인: STT 텍스트에서 장비명 키워드 인식 차이")
            print(f"    - {session1.get('model_name')} 모델: 장비명 키워드 인식 ✅")
            print(f"    - {session2.get('model_name')} 모델: 장비명 키워드 인식 ❌")
        elif analysis1['found'] and analysis2['found']:
            print(f"  💡 원인: STT 텍스트는 동일하지만 ERP 추출 과정에서 차이")
        else:
            print(f"  💡 원인: 두 모델 모두 STT 텍스트에서 장비명 키워드 미인식")
    else:
        print(f"  ✅ 장비명 도출 결과 동일")

def main():
    """메인 함수"""
    print("🔍 STT 세션 비교 체크 프로그램")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # API 서버 상태 확인
    if not check_api_health():
        print("❌ API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return
    
    # 세션 43 vs 44 비교
    compare_sessions(43, 44)
    
    print(f"\n{'='*60}")
    print("✅ 비교 완료")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

















