"""
GPT 기반 ERP 항목 추출 모듈
OpenAI GPT-3.5-turbo를 사용하여 고객센터 통화 내용에서 ERP 등록용 JSON 데이터를 추출
"""

import openai
import json
import os
from typing import Dict, Optional, List
from dotenv import load_dotenv
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from domain_loader import load_domain
from payload_schema import validate_payload, get_validation_stats
from postprocessor import postprocess_to_codes, convert_to_legacy_erp_format, extract_requester_name, normalize_speech_terms

# 환경변수 로드
load_dotenv('config.env')

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ERPExtractor:
    """ERP 항목 추출을 위한 GPT 기반 클래스 (STN 도메인 데이터 연동)"""
    
    def __init__(self):
        """초기화 - OpenAI API 키 설정 및 도메인 데이터 로드"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key or self.api_key == 'your_openai_api_key_here':
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. config.env 파일을 확인하세요.")
        
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # STN 도메인 데이터 로드
        try:
            self.domain_data = load_domain()
            logger.info("✅ STN 도메인 데이터 로딩 성공")
            logger.info(f"- 장비명: {len(self.domain_data['allowed']['equipment'])}개")
            logger.info(f"- 에러코드: {len(self.domain_data['allowed']['errors'])}개")
            logger.info(f"- 요청코드: {len(self.domain_data['allowed']['requests'])}개")
        except Exception as e:
            logger.error(f"❌ STN 도메인 데이터 로딩 실패: {e}")
            self.domain_data = None
    
    def _build_system_prompt(self) -> str:
        """STN 도메인 데이터를 활용한 시스템 프롬프트 생성"""
        if not self.domain_data:
            # 도메인 데이터가 없는 경우 기본 프롬프트
            return """당신은 콜센터 대화로부터 ERP 항목을 추출하는 어시스턴트입니다.
반드시 JSON만 출력하세요: {"장비명": "<string|null>", "장애유형": "<string|null>", "요청유형": "<string|null>", "위치": "<string|null>"}"""
        
        dom = self.domain_data
        
        # 허용된 값들 (너무 길면 일부만 표시)
        equipment_list = dom['allowed']['equipment'][:20]  # 처음 20개만
        error_list = dom['allowed']['errors'][:20]         # 처음 20개만  
        request_list = dom['allowed']['requests'][:10]     # 처음 10개만
        
        return f"""당신은 콜센터 대화로부터 ERP 항목을 추출하는 어시스턴트입니다.
반드시 JSON만 출력하세요: {{"장비명": "<equipment_name|null>", "장애유형": "<error_code|null>", "요청유형": "<request_code|null>", "위치": "<string|null>"}}

[허용 값 예시]
- 장비명: {equipment_list}...
- 장애유형: {error_list}...  
- 요청유형: {request_list}...

허용 목록에 없는 값은 생성하지 말고 null을 사용하세요.
위치는 자유 텍스트로 요약해도 됩니다."""
    
    def _build_hints(self) -> str:
        """도메인 데이터 기반 힌트 생성"""
        if not self.domain_data:
            return ""
        
        hints = []
        
        # 각 카테고리에서 몇 개씩만 선택 (프롬프트가 너무 길어지지 않게)
        if self.domain_data['hints']['equipment']:
            hints.extend(self.domain_data['hints']['equipment'][:3])
        if self.domain_data['hints']['errors']:
            hints.extend(self.domain_data['hints']['errors'][:5])
        if self.domain_data['hints']['requests']:
            hints.extend(self.domain_data['hints']['requests'][:5])
        
        return "\n".join(hints) if hints else ""
    
    def _build_user_prompt(self, transcript_text: str) -> str:
        """사용자 프롬프트 생성"""
        hints = self._build_hints()
        
        prompt = f"""[대화]
{transcript_text}"""
        
        if hints:
            prompt += f"""

[표현 힌트(예시)]
{hints}"""
        
        return prompt
    
    
    
    def _call_gpt_with_timeout(self, messages, timeout=30):
        """타임아웃이 있는 GPT API 호출"""
        def call_api():
            return self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_api)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeoutError:
                logger.error(f"GPT API 호출 타임아웃 ({timeout}초)")
                raise TimeoutError(f"GPT API 호출이 {timeout}초 내에 완료되지 않았습니다.")
    
    def get_extraction_prompt(self, conversation_text: str) -> str:
        """ERP 항목 추출을 위한 프롬프트 생성"""
        
        prompt = f"""
아래 고객센터 통화 내용을 분석하여 ERP 등록용 JSON 데이터를 생성해주세요.

**추출할 필드:**
- AS 및 지원: 지원 방식 (예: 방문기술지원, 원격기술지원, 전화지원 등)
- 요청기관: 고객사 또는 기관명 (예: 수자원공사 FA망, KT, LG U+ 등)
- 작업국소: 지역 또는 위치 (예: 서울, 부산, 대전, 대구 등)
- 요청일: 고객이 요청한 날짜 (YYYY-MM-DD 형식)
- 요청시간: 고객이 요청한 시간 (24시간 형식, 예: 15)
- 요청자: 고객 담당자 이름 (예: 이정순, 김철수 등)
- 지원인원수: 필요한 지원 인원 수 (예: 1명, 2명 등)
- 지원요원: 투입 예정 기술자 이름 (상담원이 배정하는 경우)
- 장비명: 장비 종류 (예: MSPP, 공유기, 모뎀, 스위치 등)
- 기종명: 구체적인 장비 모델명 (예: 1646SMC, DGS-1100-24 등)
- A/S기간만료여부: A/S 기간 상태 (예: 무상, 유상)
- 시스템명(고객사명): 고객사 시스템명 (예: 수자원공사 FA망)

**출력 규칙:**
1. 반드시 JSON 형식으로만 출력하세요
2. 해당 정보를 찾을 수 없으면 "정보 없음"으로 표시하세요
3. 추측하지 말고 대화에서 명확히 언급된 내용만 추출하세요
4. 날짜는 YYYY-MM-DD 형식으로, 시간은 24시간 형식(숫자만)으로 표시하세요
5. JSON 외의 다른 텍스트는 포함하지 마세요

**대화 내용:**
{conversation_text}

**출력 형식:**
{{
    "AS 및 지원": "값",
    "요청기관": "값",
    "작업국소": "값",
    "요청일": "값",
    "요청시간": "값",
    "요청자": "값",
    "지원인원수": "값",
    "지원요원": "값",
    "장비명": "값",
    "기종명": "값",
    "A/S기간만료여부": "값",
    "시스템명(고객사명)": "값"
}}
"""
        return prompt
    
    def extract_erp_data(self, conversation_text: str, max_retries: int = 2, filename: str = "") -> Dict[str, str]:
        """
        대화 내용에서 ERP 항목을 추출 (STN 도메인 데이터 연동)
        
        Args:
            conversation_text (str): 고객센터 통화 텍스트
            max_retries (int): 최대 재시도 횟수
            
        Returns:
            Dict[str, str]: 추출된 ERP 항목들
        """
        
        # 음성 정규화 (부정확한 음성을 정확한 용어로 매핑)
        normalized_text = normalize_speech_terms(conversation_text)
        
        # STN 도메인 데이터 기반 프롬프트 생성
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(normalized_text)
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"GPT API 호출 시도 {attempt + 1}/{max_retries + 1}")
                
                # 타임아웃이 있는 GPT API 호출 (성능 개선)
                messages = [
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": user_prompt
                    }
                ]
                response = self._call_gpt_with_timeout(messages, timeout=30)
                
                # 응답 텍스트 추출
                content = response.choices[0].message.content.strip()
                logger.info(f"GPT 응답: {content}")
                
                # JSON 파싱 시도
                try:
                    raw_data = json.loads(content)
                    
                    # STN 도메인 데이터 기반 후처리
                    processed_data = postprocess_to_codes(raw_data, self.domain_data)
                    
                    # 스키마 검증
                    if self.domain_data:
                        try:
                            validate_payload(processed_data, self.domain_data)
                            logger.info("✅ STN 스키마 검증 성공")
                            
                            # 검증 통계 출력
                            stats = get_validation_stats(processed_data, self.domain_data)
                            logger.info(f"검증 통계: 장비({stats['valid_equipment']}), 에러({stats['valid_error']}), 요청({stats['valid_request']})")
                            if stats['warnings']:
                                logger.warning(f"검증 경고: {stats['warnings']}")
                                
                        except Exception as e:
                            logger.warning(f"STN 스키마 검증 실패: {e}")
                    
                    # 기존 ERP 필드와의 호환성을 위한 변환 (필요시)
                    # 파일명 정보 전달
                    legacy_data = convert_to_legacy_erp_format(processed_data, conversation_text, filename)
                    
                    logger.info("ERP 데이터 추출 및 후처리 완료")
                    return legacy_data
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 실패 (시도 {attempt + 1}): {e}")
                    logger.error(f"응답 내용: {content}")
                    
                    if attempt == max_retries:
                        # 마지막 시도에서도 실패하면 기본값 반환
                        logger.error("모든 재시도 실패, 기본값 반환")
                        return self._get_default_erp_data()
                
            except (TimeoutError, FuturesTimeoutError) as e:
                logger.error(f"GPT API 타임아웃 (시도 {attempt + 1}): {e}")
                
                if attempt == max_retries:
                    logger.error("모든 재시도 실패 (타임아웃), 기본값 반환")
                    return self._get_default_erp_data()
                    
            except Exception as e:
                logger.error(f"GPT API 호출 실패 (시도 {attempt + 1}): {e}")
                
                if attempt == max_retries:
                    logger.error("모든 재시도 실패, 기본값 반환")
                    return self._get_default_erp_data()
        
        # 여기까지 오면 모든 시도가 실패한 경우
        return self._get_default_erp_data()
    
    def _get_default_erp_data(self) -> Dict[str, str]:
        """추출 실패 시 기본값 반환"""
        return {
            "AS 및 지원": "정보 없음",
            "요청기관": "정보 없음",
            "작업국소": "정보 없음",
            "요청일": "정보 없음",
            "요청시간": "정보 없음",
            "요청자": "정보 없음",
            "지원인원수": "정보 없음",
            "지원요원": "정보 없음",
            "장비명": "정보 없음",
            "기종명": "정보 없음",
            "A/S기간만료여부": "정보 없음",
            "시스템명(고객사명)": "정보 없음"
        }
    
    def extract_from_segments(self, segments: List[Dict], filename: str = "") -> Dict[str, str]:
        """
        Whisper 세그먼트 리스트에서 ERP 항목을 추출
        
        Args:
            segments (List[Dict]): Whisper STT 결과 세그먼트들
            
        Returns:
            Dict[str, str]: 추출된 ERP 항목들
        """
        
        # 세그먼트들을 하나의 대화 텍스트로 결합
        conversation_text = ""
        
        for segment in segments:
            speaker = segment.get('speaker', 'Unknown')
            text = segment.get('text', '').strip()
            start_time = segment.get('start', 0)
            
            # 시간 정보와 화자 정보 포함
            time_str = f"[{int(start_time//60):02d}:{int(start_time%60):02d}]"
            conversation_text += f"{time_str} {speaker}: {text}\n"
        
        # 음성 정규화 적용
        normalized_text = normalize_speech_terms(conversation_text)
        
        return self.extract_erp_data(normalized_text, filename=filename)


# 편의 함수들
def extract_erp_from_text(conversation_text: str) -> Dict[str, str]:
    """텍스트에서 ERP 항목을 추출하는 편의 함수"""
    extractor = ERPExtractor()
    return extractor.extract_erp_data(conversation_text)

def extract_erp_from_segments(segments: List[Dict]) -> Dict[str, str]:
    """세그먼트에서 ERP 항목을 추출하는 편의 함수"""
    extractor = ERPExtractor()
    return extractor.extract_from_segments(segments)

# 테스트용 코드
if __name__ == "__main__":
    # 테스트 대화 내용
    test_conversation = """
    [00:01] 상담원: 안녕하세요, 고객센터입니다. 어떤 도움이 필요하신가요?
    [00:05] 고객: 안녕하세요. 2층에 있는 공유기가 계속 꺼져서 인터넷이 안돼요.
    [00:12] 상담원: 공유기 전원이 꺼지는 문제이시군요. 언제부터 그런 증상이 있으셨나요?
    [00:18] 고객: 어제부터 계속 그래요. 전원을 다시 켜도 또 꺼져요.
    [00:25] 상담원: 확인해보겠습니다. 수리 기사를 보내드릴까요?
    [00:30] 고객: 네, 수리해주세요.
    """
    
    try:
        extractor = ERPExtractor()
        result = extractor.extract_erp_data(test_conversation)
        print("추출 결과:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"테스트 실행 중 오류: {e}") 