#!/usr/bin/env python3
"""
도메인 로더 테스트 스크립트
"""

from domain_loader import load_domain
from payload_schema import validate_payload, get_validation_stats
import json

def test_domain_loader():
    print("🔍 도메인 데이터 로딩 테스트...")
    
    try:
        data = load_domain()
        print("✅ 도메인 데이터 로딩 성공!")
        
        # 기본 통계
        print(f"\n📊 로딩된 데이터 통계:")
        print(f"- 장비 코드: {len(data['allowed']['equipment'])}개")
        print(f"- 에러 코드: {len(data['allowed']['errors'])}개") 
        print(f"- 요청 코드: {len(data['allowed']['requests'])}개")
        
        # 샘플 데이터 출력
        print(f"\n📋 장비 코드 샘플 (처음 5개):")
        for i, code in enumerate(data['allowed']['equipment'][:5]):
            print(f"  {i+1}. {code}")
            
        print(f"\n📋 에러 코드 샘플 (처음 5개):")
        for i, code in enumerate(data['allowed']['errors'][:5]):
            print(f"  {i+1}. {code}")
            
        print(f"\n📋 요청 코드 샘플 (처음 5개):")
        for i, code in enumerate(data['allowed']['requests'][:5]):
            print(f"  {i+1}. {code}")
            
        # 힌트 데이터 확인
        print(f"\n💡 힌트 데이터:")
        print(f"- 장비 힌트: {len(data['hints']['equipment'])}개")
        print(f"- 에러 힌트: {len(data['hints']['errors'])}개")
        print(f"- 요청 힌트: {len(data['hints']['requests'])}개")
        
        if data['hints']['equipment']:
            print(f"\n장비 힌트 예시:")
            for hint in data['hints']['equipment'][:3]:
                print(f"  - {hint}")
        
        # 모델명→장비명 매핑 테스트
        print(f"\n🔗 모델명→장비명 매핑:")
        print(f"- 총 매핑된 모델: {len(data['maps']['model_to_equipment'])}개")
        if data['maps']['model_to_equipment']:
            print(f"매핑 예시:")
            for i, (model, equipment) in enumerate(list(data['maps']['model_to_equipment'].items())[:5]):
                print(f"  {i+1}. '{model}' → '{equipment}'")
        
        # 고객 발화 예시→코드 매핑 테스트
        print(f"\n🗣️ 고객 발화→에러코드 매핑:")
        print(f"- 총 매핑된 발화: {len(data['maps']['error_examples_to_code'])}개")
        if data['maps']['error_examples_to_code']:
            print(f"발화 예시:")
            for i, (example, code) in enumerate(list(data['maps']['error_examples_to_code'].items())[:3]):
                print(f"  {i+1}. '{example}' → '{code}'")
        
        print(f"\n🗣️ 고객 발화→요청코드 매핑:")
        print(f"- 총 매핑된 발화: {len(data['maps']['request_examples_to_code'])}개")
        if data['maps']['request_examples_to_code']:
            print(f"발화 예시:")
            for i, (example, code) in enumerate(list(data['maps']['request_examples_to_code'].items())[:3]):
                print(f"  {i+1}. '{example}' → '{code}'")
                
    except Exception as e:
        print(f"❌ 도메인 데이터 로딩 실패: {e}")
        return False
        
    return True

def test_payload_schema():
    print("\n🔍 페이로드 스키마 검증 테스트...")
    
    # 도메인 데이터 로드
    try:
        domain_data = load_domain()
    except Exception as e:
        print(f"❌ 도메인 데이터 로딩 실패: {e}")
        return False
    
    # 테스트 케이스 1: 정상 케이스 (유효한 값들)
    valid_payload = {
        "장비명": "IP/MPLS",
        "장애유형": "ER-HW-001", 
        "요청유형": "RQ-REM",
        "위치": "서울 본사"
    }
    
    try:
        validate_payload(valid_payload, domain_data)
        print("✅ 정상 페이로드 기본 검증 성공!")
        
        # 도메인 검증 통계
        stats = get_validation_stats(valid_payload, domain_data)
        print(f"  - 장비명 유효: {stats['valid_equipment']}")
        print(f"  - 장애유형 유효: {stats['valid_error']}")
        print(f"  - 요청유형 유효: {stats['valid_request']}")
        if stats['warnings']:
            print(f"  - 경고: {stats['warnings']}")
            
    except Exception as e:
        print(f"❌ 정상 페이로드 검증 실패: {e}")
        return False
    
    # 테스트 케이스 2: 모델명 사용 케이스
    model_payload = {
        "장비명": "7250 IXR-R4",  # 모델명 사용
        "장애유형": "ER-HW-001", 
        "요청유형": "RQ-REM",
        "위치": "부산 지사"
    }
    
    try:
        validate_payload(model_payload, domain_data)
        print("✅ 모델명 페이로드 검증 성공!")
        
        stats = get_validation_stats(model_payload, domain_data)
        print(f"  - 장비명(모델명) 유효: {stats['valid_equipment']}")
        if stats['warnings']:
            print(f"  - 경고: {stats['warnings']}")
            
    except Exception as e:
        print(f"❌ 모델명 페이로드 검증 실패: {e}")
        return False
    
    # 테스트 케이스 3: 필수 필드 누락 케이스
    invalid_payload = {
        "장비명": "IP/MPLS",
        # "장애유형" 누락
        "요청유형": "RQ-REM"
    }
    
    try:
        validate_payload(invalid_payload, domain_data)
        print("❌ 잘못된 페이로드가 통과됨 (문제!)")
        return False
    except Exception as e:
        print(f"✅ 필수필드 누락 검증 성공: 필수 필드 누락 감지됨")
    
    # 테스트 케이스 4: 알 수 없는 값들
    unknown_payload = {
        "장비명": "알 수 없는 장비",
        "장애유형": "알 수 없는 에러", 
        "요청유형": "알 수 없는 요청"
    }
    
    try:
        validate_payload(unknown_payload, domain_data)
        print("✅ 알 수 없는 값 검증 완료 (경고 발생)")
        
        stats = get_validation_stats(unknown_payload, domain_data)
        print(f"  - 유효성: 장비({stats['valid_equipment']}), 에러({stats['valid_error']}), 요청({stats['valid_request']})")
        print(f"  - 경고 {len(stats['warnings'])}개: {stats['warnings'][:2]}...")
        
    except Exception as e:
        print(f"알 수 없는 값 검증 중 오류: {e}")
    
    return True

if __name__ == "__main__":
    print("🚀 STN 도메인 데이터 테스트 시작\n")
    
    success1 = test_domain_loader()
    success2 = test_payload_schema()
    
    if success1 and success2:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n❌ 일부 테스트 실패")
