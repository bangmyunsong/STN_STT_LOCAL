#!/usr/bin/env python3
"""
STN 도메인 데이터 연동된 GPT Extractor 테스트
"""

from gpt_extractor import ERPExtractor

def test_enhanced_extractor():
    print("🚀 STN 도메인 데이터 연동 GPT Extractor 테스트\n")
    
    # 테스트 대화 내용들
    test_cases = [
        {
            "name": "모델명 언급 케이스",
            "conversation": """
            [00:01] 상담원: 안녕하세요, 고객센터입니다.
            [00:05] 고객: 7250 IXR-R4 장비에서 HW FAIL 발생했어요.
            [00:12] 상담원: 확인해보겠습니다. 현장 점검이 필요할 것 같습니다.
            [00:18] 고객: 네, 현장 점검 요청드립니다. 위치는 서울 본사입니다.
            """
        },
        {
            "name": "고객 발화 예시 케이스", 
            "conversation": """
            [00:01] 상담원: 무엇을 도와드릴까요?
            [00:05] 고객: IP/MPLS 장비에서 유니트 불량이 발생했습니다.
            [00:12] 상담원: 원격으로 확인 가능한지 먼저 봐드릴까요?
            [00:18] 고객: 네, 원격지원으로 먼저 확인해주세요.
            """
        }
    ]
    
    try:
        # ERP Extractor 초기화 (도메인 데이터 자동 로드)
        extractor = ERPExtractor()
        print("✅ ERP Extractor 초기화 성공\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"📋 테스트 케이스 {i}: {test_case['name']}")
            print("=" * 50)
            
            # STT 텍스트에서 ERP 데이터 추출
            result = extractor.extract_erp_data(test_case['conversation'])
            
            print("🔍 추출 결과:")
            if "_stn_format" in result:
                stn_data = result["_stn_format"]
                print(f"  📊 STN 형식:")
                print(f"    - 장비명: {stn_data.get('장비명')}")
                print(f"    - 장애유형: {stn_data.get('장애유형')}")
                print(f"    - 요청유형: {stn_data.get('요청유형')}")
                print(f"    - 위치: {stn_data.get('위치')}")
                
                print(f"  🔄 레거시 변환:")
                print(f"    - 장비명: {result.get('장비명')}")
                print(f"    - AS 및 지원: {result.get('AS 및 지원')}")
                print(f"    - 작업국소: {result.get('작업국소')}")
                print(f"    - 요청 사항: {result.get('요청 사항')}")
            else:
                print(f"  ⚠️ STN 형식 데이터 없음 (도메인 데이터 로드 실패?)")
                for key, value in result.items():
                    print(f"    - {key}: {value}")
            
            print("\n")
        
        print("🎉 모든 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_extractor()

