#!/usr/bin/env python3
"""
GPT 결과 디버깅 스크립트
"""

from gpt_extractor import ERPExtractor
import json
import os
from dotenv import load_dotenv

load_dotenv('config.env')

def debug_gpt_result():
    print("🔍 GPT 결과 디버깅 시작\n")
    
    # 세션 100번의 STT 전사 텍스트
    session100_text = """예, SDA입니다. 예, 안녕하세요. 전성만 CTA입니다. 예, 그 저희 선관위 5C 예. 방치 설치할 때 저희가 UPS까지 같이 설치되나요? 혹시 거기를 제가 비치해? 선관위 설치할 때 UPS가 같이 설치되냐고요? 예, 예. 그러니까 저희 그 이게 아까 인천 동부선관이 예. UPS 교체 작업을 하고 있다고 하는데 그 UPS가 고객 건지 아니면 저희 건지 그걸 좀 확인하고 싶어서 그러거든요. 아, 그러세요. 잠깐. 그러니까 지금 UPS가 지금 고객사면 선관위 UPS인지 자치 UPS인지 아니면 KTS가 제공하는 UPS인지 그걸 알고 싶으시다고요? 예, 예. 선관위 거. 아, 죄송합니다. 매니저님 전화번호, 아니, 매니저님 성함 어떻게 되시죠? 네, 이훈하입니다. 전성만 CTA 전성만입니다. 아, 6130으로 연락드리면 되죠? 예, 예. 아, 제가 확인해보고 연락을 한번 드리겠습니다. 이거는. 예, 알겠습니다. 예."""
    
    try:
        print("📋 STT 전사 텍스트:")
        print(f"'{session100_text[:100]}...'")
        print("\n" + "="*80 + "\n")
        
        # ERP Extractor 초기화
        print("🔧 ERP Extractor 초기화 중...")
        extractor = ERPExtractor()
        print("✅ ERP Extractor 초기화 성공\n")
        
        # GPT API 호출 및 ERP 데이터 추출
        print("🤖 GPT API 호출 및 ERP 데이터 추출 중...")
        result = extractor.extract_erp_data(session100_text, filename="debug_test")
        
        print("🔍 GPT 추출 결과 (전체):")
        print("="*50)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        print("\n" + "="*80 + "\n")
        
        # STN 형식 데이터 확인
        if "_stn_format" in result:
            stn_data = result["_stn_format"]
            print("📊 STN 형식 데이터:")
            print("="*30)
            for key, value in stn_data.items():
                print(f"  {key}: {value}")
            
            print("\n🔍 핵심 필드 확인:")
            print("="*30)
            print(f"요청기관: '{stn_data.get('요청기관', 'N/A')}'")
            print(f"장비명: '{stn_data.get('장비명', 'N/A')}'")
            print(f"요청자: '{stn_data.get('요청자', 'N/A')}'")
            print(f"작업국소: '{stn_data.get('작업국소', 'N/A')}'")
            print(f"요청사항: '{stn_data.get('요청사항', 'N/A')}'")
        else:
            print("❌ STN 형식 데이터가 없습니다!")
        
        return True
        
    except Exception as e:
        print(f"❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_gpt_result()
    if success:
        print("\n✅ GPT 결과 디버깅 완료!")
    else:
        print("\n💥 GPT 결과 디버깅 실패!")
