"""
도메인 데이터 관리 모듈
STN 도메인 데이터 로딩, 시스템 프롬프트 생성, 검증 관련 로직
"""

import logging
from typing import Dict, List, Optional
from domain_loader import load_domain

logger = logging.getLogger(__name__)

class DomainManager:
    """도메인 데이터 관리 클래스"""
    
    def __init__(self):
        """초기화 - 도메인 데이터 로드"""
        self.domain_data = None
        self._load_domain_data()
    
    def _load_domain_data(self):
        """도메인 데이터 로드"""
        try:
            self.domain_data = load_domain()
            if self.domain_data:
                logger.info("✅ STN 도메인 데이터 로드 완료")
                logger.info(f"   - 장비: {len(self.domain_data.get('allowed', {}).get('equipment', []))}개")
                logger.info(f"   - 장애유형: {len(self.domain_data.get('allowed', {}).get('errors', []))}개")
                logger.info(f"   - 요청유형: {len(self.domain_data.get('allowed', {}).get('requests', []))}개")
            else:
                logger.warning("⚠️ STN 도메인 데이터 로드 실패 - 기본 모드로 동작")
        except Exception as e:
            logger.error(f"❌ 도메인 데이터 로드 중 오류: {e}")
            self.domain_data = None
    
    def get_domain_data(self) -> Optional[Dict]:
        """도메인 데이터 반환"""
        return self.domain_data
    
    def build_enhanced_system_prompt(self) -> str:
        """도메인 데이터 기반 향상된 시스템 프롬프트 생성"""
        if not self.domain_data:
            return self._get_default_system_prompt()
        
        allowed = self.domain_data.get("allowed", {})
        maps = self.domain_data.get("maps", {})
        
        # 장비명 목록
        equipment_list = allowed.get("equipment", [])
        equipment_text = ", ".join(equipment_list[:20])  # 최대 20개만
        if len(equipment_list) > 20:
            equipment_text += f" 등 총 {len(equipment_list)}개"
        
        # 장애유형 목록
        errors_list = allowed.get("errors", [])
        errors_text = ", ".join(errors_list[:15])  # 최대 15개만
        if len(errors_list) > 15:
            errors_text += f" 등 총 {len(errors_list)}개"
        
        # 요청유형 목록
        requests_list = allowed.get("requests", [])
        requests_text = ", ".join(requests_list[:10])  # 최대 10개만
        if len(requests_list) > 10:
            requests_text += f" 등 총 {len(requests_list)}개"
        
        # 위치 정보
        locations = allowed.get("locations", [])
        locations_text = ", ".join(locations[:10]) if locations else "위치 정보 없음"
        
        # 매핑 예시들
        model_examples = list(maps.get("model_to_equipment", {}).items())[:5]
        error_examples = list(maps.get("error_examples_to_code", {}).items())[:5]
        request_examples = list(maps.get("request_examples_to_code", {}).items())[:5]
        
        prompt = f"""당신은 콜센터 대화에서 ERP 항목을 추출하는 어시스턴트입니다.

[허용된 값들]
- 장비명: {equipment_text}
- 장애유형: {errors_text}
- 요청유형: {requests_text}
- 위치: {locations_text}

[매핑 예시]
장비명 매핑: {', '.join([f"{k}→{v}" for k, v in model_examples])}
장애유형 매핑: {', '.join([f"{k}→{v}" for k, v in error_examples])}
요청유형 매핑: {', '.join([f"{k}→{v}" for k, v in request_examples])}

[추출 규칙]
1. 정확한 코드값만 사용하세요 (예: "ROADM", "ERR-001", "RQ-ONS")
2. 모르는 경우 null을 반환하세요
3. 반드시 JSON 형식으로만 출력하세요
4. 대화 내용을 분석하여 가장 적절한 값들을 추출하세요

반드시 다음 JSON 형식으로만 출력하세요:
{{"장비명": "<string|null>", "장애유형": "<string|null>", "요청유형": "<string|null>", "위치": "<string|null>"}}"""
        
        return prompt
    
    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트 (도메인 데이터 없을 때)"""
        return """당신은 콜센터 대화에서 ERP 항목을 추출하는 어시스턴트입니다.
반드시 JSON만 출력하세요: {"장비명": "<string|null>", "장애유형": "<string|null>", "요청유형": "<string|null>", "위치": "<string|null>"}"""
    
    def get_validation_hints(self) -> List[str]:
        """검증 힌트 목록 반환"""
        if not self.domain_data:
            return []
        
        hints = []
        allowed = self.domain_data.get("allowed", {})
        
        # 장비명 힌트
        equipment = allowed.get("equipment", [])
        if equipment:
            hints.append(f"장비명 예시: {', '.join(equipment[:5])}")
        
        # 장애유형 힌트
        errors = allowed.get("errors", [])
        if errors:
            hints.append(f"장애유형 예시: {', '.join(errors[:5])}")
        
        # 요청유형 힌트
        requests = allowed.get("requests", [])
        if requests:
            hints.append(f"요청유형 예시: {', '.join(requests[:5])}")
        
        return hints
    
    def is_domain_data_available(self) -> bool:
        """도메인 데이터 사용 가능 여부"""
        return self.domain_data is not None
    
    def get_domain_stats(self) -> Dict:
        """도메인 데이터 통계 정보"""
        if not self.domain_data:
            return {"available": False}
        
        allowed = self.domain_data.get("allowed", {})
        maps = self.domain_data.get("maps", {})
        
        return {
            "available": True,
            "equipment_count": len(allowed.get("equipment", [])),
            "errors_count": len(allowed.get("errors", [])),
            "requests_count": len(allowed.get("requests", [])),
            "locations_count": len(allowed.get("locations", [])),
            "model_mappings_count": len(maps.get("model_to_equipment", {})),
            "error_mappings_count": len(maps.get("error_examples_to_code", {})),
            "request_mappings_count": len(maps.get("request_examples_to_code", {}))
        }

# 전역 도메인 매니저 인스턴스
domain_manager = DomainManager()



















