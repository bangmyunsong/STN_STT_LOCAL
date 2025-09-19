import jsonschema
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# 기본 스키마 (구조 검증용)
BASIC_SCHEMA = {
    "type": "object",
    "properties": {
        "장비명":   {"type": ["string","null"]},  # 장비명(이름) or null
        "장애유형": {"type": ["string","null"]},  # 장애유형 코드 or null
        "요청유형": {"type": ["string","null"]},  # 요청유형 코드 or null
        "위치":     {"type": ["string","null"]},  # 자유 텍스트 허용
    },
    "required": ["장비명","장애유형","요청유형"]
}

def validate_payload(payload: dict, domain_data: Optional[Dict] = None):
    """
    페이로드 검증 함수
    
    Args:
        payload: 검증할 JSON 데이터
        domain_data: 도메인 데이터 (선택사항, 값 검증용)
    
    Raises:
        jsonschema.ValidationError: 스키마 검증 실패
        ValueError: 도메인 값 검증 실패
    """
    # 1. 기본 스키마 검증
    jsonschema.validate(payload, BASIC_SCHEMA)
    
    # 2. 도메인 데이터 기반 값 검증 (선택사항)
    if domain_data:
        _validate_domain_values(payload, domain_data)

def _validate_domain_values(payload: dict, domain_data: Dict):
    """도메인 데이터 기반 값 검증"""
    
    # 장비명 검증
    equipment_name = payload.get("장비명")
    if equipment_name and equipment_name not in domain_data.get("allowed", {}).get("equipment", []):
        # 모델명으로 역추적 시도
        model_mapping = domain_data.get("maps", {}).get("model_to_equipment", {})
        if equipment_name not in model_mapping:
            logger.warning(f"알 수 없는 장비명: {equipment_name}")
            # 엄격한 검증을 원한다면 아래 주석 해제
            # raise ValueError(f"허용되지 않은 장비명: {equipment_name}")
    
    # 장애유형 검증
    error_type = payload.get("장애유형")
    if error_type and error_type not in domain_data.get("allowed", {}).get("errors", []):
        logger.warning(f"알 수 없는 장애유형: {error_type}")
        # raise ValueError(f"허용되지 않은 장애유형: {error_type}")
    
    # 요청유형 검증
    request_type = payload.get("요청유형")
    if request_type and request_type not in domain_data.get("allowed", {}).get("requests", []):
        logger.warning(f"알 수 없는 요청유형: {request_type}")
        # raise ValueError(f"허용되지 않은 요청유형: {request_type}")

def get_validation_stats(payload: dict, domain_data: Dict) -> Dict:
    """검증 통계 반환"""
    stats = {
        "valid_equipment": False,
        "valid_error": False, 
        "valid_request": False,
        "warnings": []
    }
    
    # 장비명 확인
    equipment_name = payload.get("장비명")
    if equipment_name:
        if equipment_name in domain_data.get("allowed", {}).get("equipment", []):
            stats["valid_equipment"] = True
        elif equipment_name in domain_data.get("maps", {}).get("model_to_equipment", {}):
            stats["valid_equipment"] = True
            stats["warnings"].append(f"모델명으로 인식됨: {equipment_name}")
        else:
            stats["warnings"].append(f"알 수 없는 장비명: {equipment_name}")
    
    # 장애유형 확인
    error_type = payload.get("장애유형")
    if error_type and error_type in domain_data.get("allowed", {}).get("errors", []):
        stats["valid_error"] = True
    elif error_type:
        stats["warnings"].append(f"알 수 없는 장애유형: {error_type}")
    
    # 요청유형 확인
    request_type = payload.get("요청유형")
    if request_type and request_type in domain_data.get("allowed", {}).get("requests", []):
        stats["valid_request"] = True
    elif request_type:
        stats["warnings"].append(f"알 수 없는 요청유형: {request_type}")
    
    return stats
