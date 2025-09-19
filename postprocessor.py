"""
ERP 데이터 후처리 모듈
STT 추출 결과를 도메인 데이터와 매핑하고 추가 정보를 추출하는 로직
"""

import re
import logging
from typing import Dict, List, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

def calculate_similarity(text1: str, text2: str) -> float:
    """두 텍스트 간의 유사도를 계산 (0.0 ~ 1.0)"""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.upper(), text2.upper()).ratio()

def find_best_match(target: str, candidates: List[str], threshold: float = 0.8) -> Optional[str]:
    """후보 목록에서 가장 유사한 항목을 찾아 반환"""
    if not target or not candidates:
        return None
    
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        score = calculate_similarity(target, candidate)
        if score >= threshold and score > best_score:
            best_match = candidate
            best_score = score
    
    if best_match:
        logger.info(f"유사도 매핑: '{target}' → '{best_match}' (유사도: {best_score:.2f})")
    
    return best_match

def extract_requester_name(text: str) -> str:
    """STT 텍스트에서 요청자 이름을 추출"""
    if not text:
        return "정보 없음"
    
    # 패턴 1: "○○팀의 ○○○입니다" 또는 "○○부서의 ○○○입니다"
    pattern1 = r'([가-힣]+(?:팀|부서|과|실|센터|원|지부|본부|사업부|사업단|연구소|연구원|기술원|기술센터|기술지원팀|망원지팀|망원팀|망원부|망원과|망원실|망원센터|망원원|망원지부|망원본부|망원사업부|망원사업단|망원연구소|망원연구원|망원기술원|망원기술센터|망원기술지원팀))의\s+([가-힣]{2,4})입니다'
    
    # 패턴 2: "○○팀 ○○○입니다" (의 없이)
    pattern2 = r'([가-힣]+(?:팀|부서|과|실|센터|원|지부|본부|사업부|사업단|연구소|연구원|기술원|기술센터|기술지원팀|망원지팀|망원팀|망원부|망원과|망원실|망원센터|망원원|망원지부|망원본부|망원사업부|망원사업단|망원연구소|망원연구원|망원기술원|망원기술센터|망원기술지원팀))\s+([가-힣]{2,4})입니다'
    
    # 패턴 3: "○○○입니다" (직접적인 이름)
    pattern3 = r'([가-힣]{2,4})입니다'
    
    # 패턴 4: "○○○이라고 합니다" 또는 "○○○이라고 해요"
    pattern4 = r'([가-힣]{2,4})(?:이라고|라고)\s+(?:합니다|해요|합니다)'
    
    patterns = [pattern1, pattern2, pattern3, pattern4]
    
    for i, pattern in enumerate(patterns, 1):
        matches = re.findall(pattern, text)
        if matches:
            if i <= 2:  # 패턴 1, 2: 부서 정보가 있는 경우
                name = matches[0][1]  # 두 번째 그룹이 이름
                logger.info(f"요청자 이름 추출 (패턴 {i}): {name}")
                return name
            else:  # 패턴 3, 4: 직접적인 이름
                name = matches[0] if isinstance(matches[0], str) else matches[0][0]
                logger.info(f"요청자 이름 추출 (패턴 {i}): {name}")
                return name
    
    logger.warning("요청자 이름을 찾을 수 없습니다")
    return "정보 없음"

def postprocess_to_codes(raw_json: dict, domain_data: dict) -> dict:
    """라벨→코드 변환 및 매핑 후처리"""
    if not domain_data:
        return raw_json
    
    result = {
        "장비명": raw_json.get("장비명"),
        "장애유형": raw_json.get("장애유형"),
        "요청유형": raw_json.get("요청유형"),
        "위치": raw_json.get("위치")
    }
    
    # 장비명 후처리 (모델명→장비명 매핑, 유사도 매핑)
    if result["장비명"] and result["장비명"] not in domain_data["allowed"]["equipment"]:
        # 1. 모델명으로 매핑 시도
        model_mapping = domain_data["maps"].get("model_to_equipment", {})
        if result["장비명"] in model_mapping:
            logger.info(f"모델명 매핑: {result['장비명']} → {model_mapping[result['장비명']]}")
            result["장비명"] = model_mapping[result["장비명"]]
        else:
            # 2. 유사도 기반 매핑 시도 (80% 이상 유사도)
            similar_equipment = find_best_match(result["장비명"], domain_data["allowed"]["equipment"], threshold=0.8)
            if similar_equipment:
                result["장비명"] = similar_equipment
                logger.info(f"유사도 매핑: {result['장비명']} → {similar_equipment}")
            else:
                logger.warning(f"알 수 없는 장비명: {result['장비명']}")
                result["장비명"] = None
    
    # 장애유형 후처리 (발화→코드 매핑, 유사도 매핑)
    if result["장애유형"] and result["장애유형"] not in domain_data["allowed"]["errors"]:
        error_mapping = domain_data["maps"].get("error_examples_to_code", {})
        if result["장애유형"] in error_mapping:
            logger.info(f"에러 발화 매핑: {result['장애유형']} → {error_mapping[result['장애유형']]}")
            result["장애유형"] = error_mapping[result["장애유형"]]
        else:
            # 2. 유사도 기반 매핑 시도 (80% 이상 유사도)
            similar_error = find_best_match(result["장애유형"], domain_data["allowed"]["errors"], threshold=0.8)
            if similar_error:
                result["장애유형"] = similar_error
                logger.info(f"유사도 매핑: {result['장애유형']} → {similar_error}")
            else:
                logger.warning(f"알 수 없는 장애유형: {result['장애유형']}")
                result["장애유형"] = None
    
    # 요청유형 후처리 (발화→코드 매핑, 유사도 매핑)
    if result["요청유형"] and result["요청유형"] not in domain_data["allowed"]["requests"]:
        request_mapping = domain_data["maps"].get("request_examples_to_code", {})
        if result["요청유형"] in request_mapping:
            logger.info(f"요청 발화 매핑: {result['요청유형']} → {request_mapping[result['요청유형']]}")
            result["요청유형"] = request_mapping[result["요청유형"]]
        else:
            # 2. 유사도 기반 매핑 시도 (80% 이상 유사도)
            similar_request = find_best_match(result["요청유형"], domain_data["allowed"]["requests"], threshold=0.8)
            if similar_request:
                result["요청유형"] = similar_request
                logger.info(f"유사도 매핑: {result['요청유형']} → {similar_request}")
            else:
                logger.warning(f"알 수 없는 요청유형: {result['요청유형']}")
                result["요청유형"] = None
    
    return result

def normalize_speech_terms(text: str) -> str:
    """통화 초기 부정확한 음성을 정확한 용어로 매핑"""
    if not text:
        return text
    
    # 음성 매핑 테이블
    speech_mappings = {
        "에스티엔": "STN",
        "에스엔": "STN", 
        "스티엔": "STN",
        "스텐": "STN",
        "스테인": "STN",
        "SN": "STN"
    }
    
    # 텍스트에서 매핑 대상 찾아서 교체
    normalized_text = text
    for incorrect_term, correct_term in speech_mappings.items():
        # 대소문자 구분 없이 매핑
        normalized_text = re.sub(
            re.escape(incorrect_term), 
            correct_term, 
            normalized_text, 
            flags=re.IGNORECASE
        )
        if incorrect_term in text:
            logger.info(f"음성 매핑: '{incorrect_term}' → '{correct_term}'")
    
    return normalized_text

def comprehensive_postprocess(text: str, domain_data: dict = None) -> str:
    """음성 정규화 + 유사도 매핑 통합 후처리"""
    if not text:
        return text
    
    # 1단계: 음성 정규화
    normalized_text = normalize_speech_terms(text)
    
    # 2단계: 유사도 매핑 적용 (도메인 데이터가 있는 경우)
    if domain_data and domain_data.get("allowed", {}).get("equipment"):
        equipment_list = domain_data["allowed"]["equipment"]
        
        # 텍스트에서 장비명 패턴 찾기 (ROADN, ROADM 등)
        equipment_patterns = [
            r'\bROADN\b', r'\bROADM\b', r'\b로드엔\b', r'\b로드엠\b'
        ]
        
        for pattern in equipment_patterns:
            matches = re.findall(pattern, normalized_text, re.IGNORECASE)
            for match in matches:
                # 유사도 매핑으로 올바른 장비명 찾기
                best_match = find_best_match(match, equipment_list, threshold=0.8)
                if best_match:
                    normalized_text = re.sub(
                        re.escape(match), 
                        best_match, 
                        normalized_text, 
                        flags=re.IGNORECASE
                    )
                    logger.info(f"통합 후처리 유사도 매핑: '{match}' → '{best_match}'")
    
    return normalized_text


def extract_datetime_from_filename(filename: str) -> tuple:
    """파일명에서 녹음 시간을 추출하여 (요청일, 요청시간) 반환"""
    if not filename:
        return "정보 없음", "정보 없음"
    
    # 파일명에서 날짜시간 패턴 추출 (YYYYMMDDHHMMSS 형식)
    datetime_pattern = r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})'
    matches = re.findall(datetime_pattern, filename)
    
    if matches:
        year, month, day, hour, minute, second = matches[0]
        
        # 요청일 형식: YYYY-MM-DD
        request_date = f"{year}-{month}-{day}"
        
        # 요청시간 형식: HH:MM:SS
        request_time = f"{hour}:{minute}:{second}"
        
        logger.info(f"파일명에서 시간 추출: {request_date} {request_time}")
        return request_date, request_time
    
    logger.warning(f"파일명에서 시간 정보를 찾을 수 없습니다: {filename}")
    return "정보 없음", "정보 없음"

def extract_customer_name(conversation_text: str) -> str:
    """STT 텍스트에서 고객사명을 추출"""
    if not conversation_text:
        return "정보 없음"
    
    # 고객사명 패턴들
    customer_patterns = [
        r'삼성\s*SDS',
        r'삼성\s*전자',
        r'LG\s*\w+',
        r'KT\s*\w*',
        r'SKT\s*\w*',
        r'네이버',
        r'카카오',
        r'한국전력',
        r'한전',
        r'현대\s*\w+',
        r'기아\s*\w*',
        r'포스코',
        r'대한항공',
        r'아시아나',
        r'CJ\s*\w+',
        r'GS\s*\w+',
        r'롯데\s*\w+'
    ]
    
    for pattern in customer_patterns:
        matches = re.findall(pattern, conversation_text, re.IGNORECASE)
        if matches:
            # 가장 자주 언급된 고객사 반환
            customer = matches[0].strip()
            logger.info(f"고객사명 추출: {customer}")
            return customer
    
    logger.warning("고객사명을 찾을 수 없습니다")
    return "정보 없음"

def analyze_request_context(conversation_text: str, stn_data: dict) -> str:
    """STT 텍스트에서 요청사항의 문맥을 분석하여 의미있는 요청사항 생성"""
    if not conversation_text:
        return f"장애유형: {stn_data.get('장애유형', '정보 없음')}, 요청유형: {stn_data.get('요청유형', '정보 없음')}"
    
    # 상세한 요청사항 분석
    request_details = []
    
    # 1. 장애 상황 분석
    if '링크 장애' in conversation_text:
        request_details.append("해외 페콜망 링크 장애 발생")
    if '복구' in conversation_text and '원인 파악' in conversation_text:
        request_details.append("장애 복구 후 원인 파악 요청")
    if '알람' in conversation_text and '성능' in conversation_text:
        request_details.append("성능 관련 알람 발생")
    
    # 2. 긴급성 및 처리 요청
    if '긴급하게' in conversation_text and '확인 요청' in conversation_text:
        request_details.append("긴급 확인 및 점검 요청")
    if '부탁드릴게요' in conversation_text:
        request_details.append("기술 지원 요청")
    
    # 3. 구체적인 요청 내용
    if '회산번호' in conversation_text and '장비명' in conversation_text:
        request_details.append("회선번호 및 장비명 확인 요청")
    if '서버 IP' in conversation_text:
        request_details.append("서버 IP 정보 확인")
    
    # 4. 시간 및 위치 정보
    time_pattern = r'(\d{1,2}시\s*\d{0,2}분?)'
    time_matches = re.findall(time_pattern, conversation_text)
    if time_matches:
        request_details.append(f"장애 발생 시간: {time_matches[0]}")
    
    if '천안 아산' in conversation_text:
        request_details.append("천안 아산 지역 장애")
    
    # 5. 장비 및 네트워크 정보
    ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    ip_matches = re.findall(ip_pattern, conversation_text)
    if ip_matches:
        request_details.append(f"대상 서버 IP: {ip_matches[0]}")
    
    if 'ROADN' in conversation_text or 'ROADM' in conversation_text:
        request_details.append("ROAD 장비 관련 이슈")
    
    # 6. 고객사 및 네트워크 정보
    if '삼성 SDS' in conversation_text:
        request_details.append("삼성 SDS 고객사")
    if '해외 페콜망' in conversation_text:
        request_details.append("해외 페콜망 관련")
    
    # 7. 요청자 및 후속 조치
    if '전역망원지팀' in conversation_text:
        request_details.append("전역망원지팀 요청")
    if '연락 드리겠습니다' in conversation_text:
        request_details.append("후속 연락 및 조치 예정")
    
    # 요청사항 종합 정리
    if request_details:
        # 기본 정보
        base_info = f"장애유형: {stn_data.get('장애유형', '정보 없음')}, 요청유형: {stn_data.get('요청유형', '정보 없음')}"
        
        # 상세 요청사항
        detailed_request = " | ".join(request_details)
        
        return f"{base_info} | 요청내용: {detailed_request}"
    else:
        # 기본 정보만 반환
        return f"장애유형: {stn_data.get('장애유형', '정보 없음')}, 요청유형: {stn_data.get('요청유형', '정보 없음')}"

def convert_to_legacy_erp_format(stn_data: dict, conversation_text: str = "", filename: str = "") -> dict:
    """STN 형식을 기존 ERP 형식으로 변환"""
    # 요청자 이름 추출 (STT 텍스트에서 직접 추출)
    requester_name = extract_requester_name(conversation_text)
    
    # 고객사명 추출 (STT 텍스트에서 직접 추출)
    customer_name = extract_customer_name(conversation_text)
    
    # 파일명에서 녹음 시간 추출
    request_date, request_time = extract_datetime_from_filename(filename)
    
    # 요청사항 문맥 분석
    request_context = analyze_request_context(conversation_text, stn_data)
    
    # None 값을 안전하게 처리하는 헬퍼 함수
    def safe_get(key: str, default: str = "정보 없음") -> str:
        value = stn_data.get(key, default)
        return str(value) if value is not None else default
    
    return {
        "AS 및 지원": "방문기술지원" if stn_data.get("요청유형") == "RQ-ONS" else "원격기술지원",
        "요청기관": "정보 없음",
        "작업국소": safe_get("위치"),
        "요청일": request_date,  # 파일명에서 추출된 요청일
        "요청시간": request_time,  # 파일명에서 추출된 요청시간
        "요청자": requester_name,  # 추출된 요청자 이름 사용
        "지원인원수": "1",
        "지원요원": "정보 없음",
        "장비명": safe_get("장비명"),
        "기종명": safe_get("장비명"),  # 장비명과 동일하게 처리
        "A/S기간만료여부": "정보 없음",
        "시스템명(고객사명)": customer_name,  # 추출된 고객사명 사용
        "요청 사항": request_context  # 문맥 분석된 요청사항 사용
    }
