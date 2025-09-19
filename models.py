"""
STN 고객센터 STT 시스템 데이터 모델
Pydantic 모델 정의
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class ERPData(BaseModel):
    """ERP 등록 데이터 모델"""
    as_support: str = Field("", alias="AS 및 지원", description="지원 방식 (방문기술지원, 원격기술지원 등)")
    request_org: str = Field("", alias="요청기관", description="고객사 또는 기관명")
    work_location: str = Field("", alias="작업국소", description="지역 또는 위치")
    request_date: str = Field("", alias="요청일", description="고객이 요청한 날짜 (YYYY-MM-DD)")
    request_time: str = Field("", alias="요청시간", description="고객이 요청한 시간 (24시간 형식)")
    requester: str = Field("", alias="요청자", description="고객 담당자 이름")
    support_count: str = Field("", alias="지원인원수", description="필요한 지원 인원 수")
    support_staff: str = Field("", alias="지원요원", description="투입 예정 기술자 이름")
    equipment_name: str = Field("", alias="장비명", description="장비 종류")
    model_name: str = Field("", alias="기종명", description="구체적인 장비 모델명")
    as_period_status: str = Field("", alias="A/S기간만료여부", description="A/S 기간 상태 (무상, 유상)")
    system_name: str = Field("", alias="시스템명(고객사명)", description="고객사 시스템명")
    request_content: str = Field("", alias="요청 사항", description="고객 요청 내용 요약")
    
    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "AS 및 지원": "원격기술지원",
                "요청기관": "삼성 SDS",
                "작업국소": "서울",
                "요청일": "2024-01-15",
                "요청시간": "14:30",
                "요청자": "김주원",
                "지원인원수": "1명",
                "지원요원": "이기술",
                "장비명": "ROADM",
                "기종명": "ROADM-4000",
                "A/S기간만료여부": "무상",
                "시스템명(고객사명)": "해외 페콜망",
                "요청 사항": "링크 장애 원인 파악 요청"
            }
        }


class ERPRegisterResponse(BaseModel):
    """ERP 등록 응답 모델"""
    status: str = Field(..., description="처리 상태")
    erp_id: str = Field(..., description="ERP 등록 ID")
    message: Optional[str] = Field(None, description="처리 메시지")


class STTRequest(BaseModel):
    """STT 처리 요청 모델"""
    model_name: Optional[str] = Field("base", description="Whisper 모델명")
    language: Optional[str] = Field(None, description="언어 코드")
    enable_diarization: Optional[bool] = Field(True, description="화자 분리 활성화")


class STTResponse(BaseModel):
    """STT 처리 응답 모델 (하이브리드: 원본 + 후처리)"""
    status: str = Field(..., description="처리 상태")
    transcript: str = Field(..., description="후처리된 전체 텍스트")
    segments: List[Dict] = Field(..., description="후처리된 세그먼트별 결과")
    erp_data: Optional[ERPData] = Field(None, description="추출된 ERP 데이터")
    processing_time: float = Field(..., description="처리 시간(초)")
    file_id: str = Field(..., description="파일 처리 ID")
    session_id: Optional[int] = Field(None, description="데이터베이스 세션 ID")
    extraction_id: Optional[int] = Field(None, description="ERP 추출 결과 ID")
    
    # 하이브리드 필드 (원본 데이터 보존)
    original_transcript: Optional[str] = Field(None, description="원본 STT 텍스트")
    original_segments: Optional[List[Dict]] = Field(None, description="원본 STT 세그먼트")


class ERPExtractionRequest(BaseModel):
    """ERP 추출 요청 모델"""
    transcript_text: str
    use_legacy_format: bool = True
    temperature: float = 0.1
    max_tokens: int = 500
