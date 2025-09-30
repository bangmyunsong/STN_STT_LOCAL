"""
STN 고객센터 STT 시스템 데이터 모델
Pydantic 모델 정의
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union


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
    equipment_name: Optional[str] = Field("정보 없음", alias="장비명", description="장비 종류")
    model_name: Optional[str] = Field("정보 없음", alias="기종명", description="구체적인 장비 모델명")
    as_period_status: str = Field("", alias="A/S기간만료여부", description="A/S 기간 상태 (무상, 유상)")
    system_name: str = Field("", alias="시스템명(고객사명)", description="고객사 시스템명")
    request_content: str = Field("", alias="요청 사항", description="고객 요청 내용 요약")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
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


# ===== Admin UI API 응답 모델들 =====

class STTSession(BaseModel):
    """STT 세션 데이터 모델"""
    id: int = Field(..., description="세션 고유 ID")
    file_name: str = Field(..., description="처리된 음성 파일명")
    file_id: str = Field(..., description="파일 처리 ID")
    model_name: str = Field(..., description="사용된 Whisper 모델명")
    language: Optional[str] = Field(None, description="언어 코드")
    transcript: Optional[str] = Field(None, description="STT 변환된 전체 텍스트")
    segments: Optional[Union[List[Dict], str]] = Field(None, description="화자별 분할된 텍스트 세그먼트")
    original_segments: Optional[Union[List[Dict], str]] = Field(None, description="원본 화자별 분할된 텍스트 세그먼트")
    processing_time: Optional[float] = Field(None, description="처리 시간(초)")
    status: str = Field(..., description="처리 상태 (completed, failed, processing)")
    created_at: str = Field(..., description="생성일시")
    updated_at: Optional[str] = Field(None, description="수정일시")


class ERPExtraction(BaseModel):
    """ERP 추출 결과 모델"""
    id: int = Field(..., description="추출 결과 고유 ID")
    session_id: int = Field(..., description="연결된 STT 세션 ID")
    as_support: Optional[str] = Field(None, alias="AS 및 지원", description="지원 방식")
    request_org: Optional[str] = Field(None, alias="요청기관", description="요청 기관명")
    work_location: Optional[str] = Field(None, alias="작업국소", description="작업 위치")
    request_date: Optional[str] = Field(None, alias="요청일", description="요청 날짜")
    request_time: Optional[str] = Field(None, alias="요청시간", description="요청 시간")
    requester: Optional[str] = Field(None, alias="요청자", description="요청자명")
    support_count: Optional[str] = Field(None, alias="지원인원수", description="지원 인원 수")
    support_staff: Optional[str] = Field(None, alias="지원요원", description="지원 요원명")
    equipment_name: Optional[str] = Field(None, alias="장비명", description="장비명")
    model_name: Optional[str] = Field(None, alias="기종명", description="기종명")
    as_period_status: Optional[str] = Field(None, alias="A/S기간만료여부", description="A/S 기간 상태")
    system_name: Optional[str] = Field(None, alias="시스템명(고객사명)", description="시스템명")
    request_content: Optional[str] = Field(None, alias="요청 사항", description="요청 사항")
    confidence_score: Optional[float] = Field(None, description="추출 신뢰도 점수")
    created_at: Optional[str] = Field(None, description="생성일시")
    updated_at: Optional[str] = Field(None, description="수정일시")
    
    class Config:
        populate_by_name = True


class AudioFileInfo(BaseModel):
    """음성 파일 정보 모델"""
    filename: str = Field(..., description="파일명")
    path: str = Field(..., description="파일 경로")
    size: int = Field(..., description="파일 크기 (바이트)")
    modified: str = Field(..., description="수정일시")
    type: Optional[str] = Field(None, description="파일 타입 (direct, daily_folder)")
    extension: Optional[str] = Field(None, description="파일 확장자")
    location: Optional[str] = Field(None, description="파일 위치 (daily, uploaded)")
    folder: Optional[str] = Field(None, description="폴더명 (일자별 폴더인 경우)")


class ERPRegisterLog(BaseModel):
    """ERP 등록 로그 모델"""
    id: int = Field(..., description="로그 고유 ID")
    extraction_id: int = Field(..., description="연결된 ERP 추출 결과 ID")
    erp_id: Optional[str] = Field(None, description="ERP 시스템 등록 ID")
    status: str = Field(..., description="등록 상태 (success, failed, pending)")
    response_data: Optional[Dict] = Field(None, description="ERP 시스템 응답 데이터")
    registered_at: str = Field(..., description="등록 시도 일시")
    created_at: Optional[str] = Field(None, description="생성 일시 (호환성용)")


class SystemStatistics(BaseModel):
    """시스템 통계 모델"""
    total_sessions: int = Field(..., description="전체 STT 세션 수")
    completed_sessions: int = Field(..., description="완료된 세션 수")
    failed_sessions: int = Field(..., description="실패한 세션 수")
    total_extractions: int = Field(..., description="전체 ERP 추출 수")
    total_registers: int = Field(..., description="전체 ERP 등록 시도 수")
    success_registers: int = Field(..., description="성공한 ERP 등록 수")
    failed_registers: int = Field(..., description="실패한 ERP 등록 수")
    avg_processing_time: float = Field(..., description="평균 처리 시간(초)")
    model_usage: Optional[Dict[str, int]] = Field(None, description="모델별 사용 통계")


# ===== API 응답 래퍼 모델들 =====

class ExtractionsResponse(BaseModel):
    """ERP 추출 결과 목록 응답 모델"""
    status: str = Field(..., description="응답 상태 (success, error)")
    extractions: List[ERPExtraction] = Field(..., description="ERP 추출 결과 목록")
    total: int = Field(..., description="전체 개수")
    message: Optional[str] = Field(None, description="오류 메시지 (status가 error인 경우)")


class SessionsResponse(BaseModel):
    """STT 세션 목록 응답 모델"""
    status: str = Field(..., description="응답 상태 (success, error)")
    sessions: List[STTSession] = Field(..., description="STT 세션 목록")
    total: int = Field(..., description="전체 개수")
    message: Optional[str] = Field(None, description="오류 메시지 (status가 error인 경우)")


class SessionDetailResponse(BaseModel):
    """STT 세션 상세 조회 응답 모델"""
    status: str = Field(..., description="응답 상태 (success, error)")
    session: STTSession = Field(..., description="STT 세션 정보")
    extraction: Optional[ERPExtraction] = Field(None, description="연결된 ERP 추출 결과")
    message: Optional[str] = Field(None, description="오류 메시지 (status가 error인 경우)")


class RegisterLogsResponse(BaseModel):
    """ERP 등록 로그 목록 응답 모델"""
    status: str = Field(..., description="응답 상태 (success, error)")
    register_logs: List[ERPRegisterLog] = Field(..., description="ERP 등록 로그 목록")
    total: int = Field(..., description="전체 개수")
    message: Optional[str] = Field(None, description="오류 메시지 (status가 error인 경우)")


class StatisticsResponse(BaseModel):
    """시스템 통계 응답 모델"""
    status: str = Field(..., description="응답 상태 (success, error)")
    statistics: SystemStatistics = Field(..., description="시스템 통계 정보")
    message: Optional[str] = Field(None, description="오류 메시지 (status가 error인 경우)")


class AudioFilesResponse(BaseModel):
    """음성 파일 목록 응답 모델"""
    status: str = Field(..., description="응답 상태 (success, error)")
    message: Optional[str] = Field(None, description="응답 메시지")
    files: List[AudioFileInfo] = Field(..., description="전체 파일 목록")
    daily_files: Dict[str, List[AudioFileInfo]] = Field(..., description="일자별 파일 목록")
    directory: str = Field(..., description="디렉토리 경로")
    today_folder: str = Field(..., description="오늘 폴더명")


class ERPReExtractionResponse(BaseModel):
    """ERP 재추출 응답 모델"""
    status: str = Field(..., description="처리 상태 (success, error)")
    message: str = Field(..., description="처리 메시지")
    session_id: int = Field(..., description="세션 ID")
    extraction_id: int = Field(..., description="새로 생성된 추출 결과 ID")
    erp_data: ERPData = Field(..., description="추출된 ERP 데이터")