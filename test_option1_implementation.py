#!/usr/bin/env python3
"""
옵션1 구현 테스트: GPT 우선, 후처리 보완 방식
"""

from gpt_extractor import ERPExtractor
from postprocessor import convert_to_legacy_erp_format
import json
import os
from dotenv import load_dotenv

load_dotenv('config.env')

def test_option1_implementation():
    print("🚀 옵션1 구현 테스트: GPT 우선, 후처리 보완 방식\n")
    
    # 세션 100번의 STT 전사 텍스트
    session100_text = """예, SDA입니다. 예, 안녕하세요. 전성만 CTA입니다. 예, 그 저희 선관위 5C 예. 방치 설치할 때 저희가 UPS까지 같이 설치되나요? 혹시 거기를 제가 비치해? 선관위 설치할 때 UPS가 같이 설치되냐고요? 예, 예. 그러니까 저희 그 이게 아까 인천 동부선관이 예. UPS 교체 작업을 하고 있다고 하는데 그 UPS가 고객 건지 아니면 저희 건지 그걸 좀 확인하고 싶어서 그러거든요. 아, 그러세요. 잠깐. 그러니까 지금 UPS가 지금 고객사면 선관위 UPS인지 자치 UPS인지 아니면 KTS가 제공하는 UPS인지 그걸 알고 싶으시다고요? 예, 예. 선관위 거. 아, 죄송합니다. 매니저님 전화번호, 아니, 매니저님 성함 어떻게 되시죠? 네, 이훈하입니다. 전성만 CTA 전성만입니다. 아, 6130으로 연락드리면 되죠? 예, 예. 아, 제가 확인해보고 연락을 한번 드리겠습니다. 이거는. 예, 알겠습니다. 예."""
    
    try:
        print("📋 세션 100번 STT 전사 텍스트:")
        print(f"'{session100_text[:100]}...'")
        print("\n" + "="*80 + "\n")
        
        # ERP Extractor 초기화
        print("🔧 ERP Extractor 초기화 중...")
        extractor = ERPExtractor()
        print("✅ ERP Extractor 초기화 성공\n")
        
        # GPT API 호출 및 ERP 데이터 추출
        print("🤖 GPT API 호출 및 ERP 데이터 추출 중...")
        gpt_result = extractor.extract_erp_data(session100_text, filename="session100_test")
        
        print("🔍 GPT 추출 결과:")
        print("="*50)
        
        # GPT 결과 출력
        for key, value in gpt_result.items():
            if key != "_stn_format":
                print(f"  {key}: {value}")
        
        # STN 형식 데이터가 있으면 별도 출력
        if "_stn_format" in gpt_result:
            print(f"\n📊 STN 형식 데이터:")
            stn_data = gpt_result["_stn_format"]
            for key, value in stn_data.items():
                print(f"  {key}: {value}")
        
        print("\n" + "="*80 + "\n")
        
        # 옵션1 후처리 로직 테스트
        print("🔧 옵션1 후처리 로직 테스트 중...")
        final_result = convert_to_legacy_erp_format(
            stn_data=gpt_result.get("_stn_format", {}),
            conversation_text=session100_text,
            filename="session100_test"
        )
        
        print("🎯 최종 ERP 매핑 결과 (옵션1 적용):")
        print("="*50)
        
        # 최종 결과 출력
        for key, value in final_result.items():
            print(f"  {key}: {value}")
        
        print("\n🎉 옵션1 구현 테스트 완료!")
        
        # 핵심 항목 검증
        print("\n📋 핵심 항목 검증:")
        print("="*30)
        print(f"요청기관: {final_result.get('요청기관', 'N/A')}")
        print(f"요청자: {final_result.get('요청자', 'N/A')}")
        print(f"장비명: {final_result.get('장비명', 'N/A')}")
        print(f"작업국소: {final_result.get('작업국소', 'N/A')}")
        print(f"요청 사항: {final_result.get('요청 사항', 'N/A')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_option1_implementation()
    if success:
        print("\n✅ 옵션1 구현 테스트 성공!")
    else:
        print("\n💥 옵션1 구현 테스트 실패!")
