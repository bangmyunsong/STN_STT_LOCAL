"""
STN 고객센터 STT 시스템 API 서버
FastAPI 기반 REST API 서버 - ERP 연동 및 STT 처리
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import uuid
import json
import os
import tempfile
import whisper
from datetime import datetime, timedelta
import logging
import threading
from postprocessor import postprocess_to_codes, convert_to_legacy_erp_format, extract_requester_name
from domain_manager import domain_manager

# 스케줄러 관련 import (선택적)
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    BackgroundScheduler = None
    CronTrigger = None
    SCHEDULER_AVAILABLE = False
    print("⚠️ APScheduler가 설치되지 않았습니다. 스케줄러 기능이 비활성화됩니다.")
    print("⚠️ 설치하려면: pip install APScheduler>=3.10.0")

# 로컬 모듈 import
from gpt_extractor import ERPExtractor, extract_erp_from_segments
from supabase_client import get_supabase_manager, save_stt_result, save_erp_result
from dotenv import load_dotenv

# 핫리로드 및 도메인 데이터 관련 import
from importlib import reload
import gpt_extractor as ge
import domain_loader as dl
from payload_schema import validate_payload, get_validation_stats
import openai
import json

# 환경변수 로드
import os
config_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(config_path)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="STN 고객센터 STT 시스템 API",
    description="Whisper STT + GPT-3.5-turbo 기반 ERP 항목 추출 및 연동 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 422 오류 디버깅을 위한 예외 핸들러
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"422 검증 오류 발생 - URL: {request.url}")
    logger.error(f"요청 메소드: {request.method}")
    logger.error(f"요청 헤더: {dict(request.headers)}")
    
    # 요청 본문 로깅
    try:
        body = await request.body()
        logger.error(f"요청 본문: {body.decode('utf-8')}")
    except Exception as e:
        logger.error(f"요청 본문 읽기 실패: {e}")
    
    # 쿼리 파라미터 로깅
    logger.error(f"쿼리 파라미터: {dict(request.query_params)}")
    
    # 상세한 검증 오류 로깅
    logger.error(f"검증 오류 상세:")
    for error in exc.errors():
        logger.error(f"  - 필드: {error.get('loc')}")
        logger.error(f"  - 오류: {error.get('msg')}")
        logger.error(f"  - 타입: {error.get('type')}")
        logger.error(f"  - 입력값: {error.get('input', 'N/A')}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "message": "요청 데이터 검증 실패",
            "debug_info": {
                "url": str(request.url),
                "method": request.method,
                "errors": exc.errors()
            }
        }
    )

# 전역 변수
whisper_model = None
erp_extractor = None
supabase_manager = None

# 모델 캐싱용 딕셔너리 (성능 최적화)
cached_whisper_models = {}

# 도메인 데이터 캐시 (핫리로드용)
# 도메인 데이터는 domain_manager에서 관리

def clear_model_cache():
    """메모리 관리를 위한 모델 캐시 정리 함수"""
    global cached_whisper_models
    cached_whisper_models.clear()
    logger.info("모델 캐시가 정리되었습니다.")

def clear_whisper_file_cache():
    """손상된 Whisper 파일 캐시를 정리하는 함수"""
    import os
    import shutil
    from pathlib import Path
    
    try:
        # Windows 환경에서 Whisper 캐시 경로
        cache_paths = [
            Path.home() / ".cache" / "whisper",  # Linux/Mac
            Path(os.getenv('LOCALAPPDATA', '')) / "whisper",  # Windows
            Path(os.getenv('APPDATA', '')) / "whisper",  # Windows 대안
        ]
        
        cleared_paths = []
        for cache_path in cache_paths:
            if cache_path.exists() and cache_path.is_dir():
                try:
                    shutil.rmtree(cache_path)
                    cleared_paths.append(str(cache_path))
                    logger.info(f"Whisper 캐시 폴더 삭제됨: {cache_path}")
                except Exception as e:
                    logger.warning(f"캐시 폴더 삭제 실패 ({cache_path}): {e}")
        
        if cleared_paths:
            logger.info(f"총 {len(cleared_paths)}개의 캐시 폴더가 정리되었습니다.")
            return True, cleared_paths
        else:
            logger.info("정리할 Whisper 캐시 폴더를 찾을 수 없습니다.")
            return False, []
            
    except Exception as e:
        logger.error(f"Whisper 캐시 정리 중 오류: {e}")
        return False, []

# 상수 정의
import os
# 스크립트가 있는 디렉토리 기준으로 src_record 경로 설정
AUDIO_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src_record")

# 지원되는 오디오 파일 확장자
SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg']

# 일자별 폴더 관리 함수
def create_daily_directory():
    """
    오늘 날짜 기준으로 src_record 하위에 YYYY-MM-DD 형식의 폴더 생성
    """
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        daily_path = os.path.join(AUDIO_DIRECTORY, today)
        
        # 기본 src_record 디렉토리가 없으면 생성
        if not os.path.exists(AUDIO_DIRECTORY):
            os.makedirs(AUDIO_DIRECTORY)
            logger.info(f"기본 음성 파일 디렉토리 생성: {AUDIO_DIRECTORY}")
        
        # 오늘 날짜 폴더가 없으면 생성
        if not os.path.exists(daily_path):
            os.makedirs(daily_path)
            logger.info(f"일자별 폴더 생성: {daily_path}")
        else:
            logger.info(f"일자별 폴더 이미 존재: {daily_path}")
            
        return daily_path
        
    except Exception as e:
        logger.error(f"일자별 폴더 생성 실패: {e}")
        return None

# 스케줄러 관련 변수
scheduler = None

def create_daily_directory_with_date(target_date=None, auto_create=True):
    """
    특정 날짜의 폴더를 생성 (스케줄러용)
    
    Args:
        target_date: 생성할 날짜 (기본값: 오늘)
        auto_create: 자동 생성 여부
    """
    try:
        if target_date is None:
            target_date = datetime.now()
        
        date_str = target_date.strftime('%Y-%m-%d')
        daily_path = os.path.join(AUDIO_DIRECTORY, date_str)
        
        # 기본 src_record 디렉토리가 없으면 생성
        if not os.path.exists(AUDIO_DIRECTORY):
            os.makedirs(AUDIO_DIRECTORY)
            logger.info(f"기본 음성 파일 디렉토리 생성: {AUDIO_DIRECTORY}")
        
        # 해당 날짜 폴더가 없으면 생성
        if not os.path.exists(daily_path):
            if auto_create:
                os.makedirs(daily_path)
                logger.info(f"스케줄러: 일자별 폴더 생성 완료 - {daily_path}")
            else:
                logger.info(f"스케줄러: 폴더 생성 필요 - {daily_path} (auto_create=False)")
        else:
            logger.info(f"스케줄러: 일자별 폴더 이미 존재 - {daily_path}")
            
        return daily_path
        
    except Exception as e:
        logger.error(f"스케줄러: 일자별 폴더 생성 실패 - {e}")
        return None

def ensure_today_folder_exists():
    """
    오늘 날짜 폴더가 존재하는지 확인하고 없으면 생성
    """
    return create_daily_directory_with_date(datetime.now(), auto_create=True)

def scheduled_daily_folder_creation():
    """
    매일 0시에 실행되는 일별 폴더 생성 함수
    """
    try:
        today = datetime.now()
        daily_path = create_daily_directory_with_date(today, auto_create=True)
        
        if daily_path:
            logger.info(f"✅ 스케줄러: {today.strftime('%Y-%m-%d')} 폴더 생성 완료")
        else:
            logger.error(f"❌ 스케줄러: {today.strftime('%Y-%m-%d')} 폴더 생성 실패")
            
    except Exception as e:
        logger.error(f"❌ 스케줄러 실행 중 오류: {e}")

def get_daily_directory_path(date_str=None):
    """
    특정 날짜의 폴더 경로를 반환 (기본값: 오늘)
    
    Args:
        date_str (str): YYYY-MM-DD 형식의 날짜 문자열
    
    Returns:
        str: 일자별 폴더 경로
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    return os.path.join(AUDIO_DIRECTORY, date_str)

# Pydantic 모델들
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
                "요청기관": "수자원공사 FA망",
                "작업국소": "대전",
                "요청일": "2025-04-18",
                "요청시간": "15",
                "요청자": "이정순",
                "지원인원수": "1명",
                "지원요원": "임선묵",
                "장비명": "MSPP",
                "기종명": "1646SMC",
                "A/S기간만료여부": "유상",
                "시스템명(고객사명)": "수자원공사 FA망",
                "요청 사항": "수자원 회선 문의건"
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

# 초기화 함수들
def initialize_models():
    """모델들을 초기화하는 함수 (안전한 단계별 초기화)"""
    global whisper_model, erp_extractor, supabase_manager
    
    logger.info("🚀 모델 초기화 시작...")
    
    # 1. Whisper 모델들 로드 (가장 중요)
    try:
        logger.info("1️⃣ Whisper 모델들 로딩 중... (인터넷 연결 필요)")
        
        # 로드할 모델 목록 (우선순위 순)
        models_to_load = ["base", "small", "medium", "large"]
        
        import time
        total_start_time = time.time()
        
        for model_name in models_to_load:
            try:
                logger.info(f"📥 {model_name} 모델 로딩 중...")
                start_time = time.time()
                model = whisper.load_model(model_name)
                loading_time = time.time() - start_time
                
                # 캐시에 저장
                cached_whisper_models[model_name] = model
                
                # base 모델은 전역 변수에도 저장
                if model_name == "base":
                    whisper_model = model
                
                logger.info(f"✅ {model_name} 모델 로딩 완료 (소요시간: {loading_time:.2f}초)")
                
            except Exception as model_error:
                logger.warning(f"⚠️ {model_name} 모델 로딩 실패: {model_error}")
                if model_name == "base":
                    # base 모델은 필수이므로 실패 시 에러
                    raise
                else:
                    # 다른 모델은 선택적이므로 계속 진행
                    continue
        
        total_loading_time = time.time() - total_start_time
        loaded_models = list(cached_whisper_models.keys())
        logger.info(f"🎉 Whisper 모델 로딩 완료! (총 소요시간: {total_loading_time:.2f}초)")
        logger.info(f"📋 로드된 모델: {', '.join(loaded_models)}")
        
    except Exception as e:
        logger.error(f"❌ Whisper 모델 로딩 실패: {e}")
        logger.error("💡 해결방법: 인터넷 연결 확인 또는 캐시된 모델 사용")
        logger.error("💡 체크섬 오류 시: ~/.cache/whisper 폴더 삭제 후 재시도")
        raise
    
    # 2. ERP Extractor 초기화 (선택적)
    try:
        logger.info("2️⃣ ERP Extractor 초기화 중...")
        erp_extractor = ERPExtractor()
        logger.info("✅ ERP Extractor 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ ERP Extractor 초기화 실패 (계속 진행): {e}")
        logger.warning("💡 해결방법: config.env에서 OPENAI_API_KEY 확인")
        erp_extractor = None
    
    # 3. Supabase 매니저 초기화 (선택적)
    try:
        logger.info("3️⃣ Supabase 매니저 초기화 중...")
        supabase_manager = get_supabase_manager()
        logger.info("✅ Supabase 매니저 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ Supabase 초기화 실패 (계속 진행): {e}")
        logger.warning("💡 해결방법: config.env에서 Supabase 설정 확인")
        supabase_manager = None
    
    logger.info("🎉 모델 초기화 완료!")

# 의존성 함수
def get_whisper_model():
    """Whisper 모델 의존성"""
    if whisper_model is None:
        raise HTTPException(status_code=500, detail="Whisper 모델이 초기화되지 않았습니다")
    return whisper_model

def get_erp_extractor():
    """ERP Extractor 의존성 (선택적)"""
    if erp_extractor is None:
        logger.warning("ERP Extractor가 초기화되지 않았습니다. ERP 추출 기능이 비활성화됩니다.")
        # 기본 객체 반환 또는 None 반환하여 처리 로직에서 확인하게 함
        return None
    return erp_extractor

def get_supabase_manager_dep():
    """Supabase 매니저 의존성 (자동 초기화 포함)"""
    global supabase_manager
    
    # 항상 새로운 매니저 인스턴스를 반환 (싱글톤 문제 해결)
    try:
        logger.info("🔄 Supabase 매니저 새 인스턴스 생성...")
        fresh_manager = get_supabase_manager()
        logger.info("✅ Supabase 매니저 새 인스턴스 생성 성공")
        return fresh_manager
    except Exception as e:
        logger.error(f"❌ Supabase 매니저 새 인스턴스 생성 실패: {e}")
        return None

# API 엔드포인트들

@app.get("/")
async def root():
    """API 서버 상태 확인"""
    return {
        "message": "STN 고객센터 STT 시스템 API 서버",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    supabase_status = False
    if supabase_manager:
        try:
            supabase_status = supabase_manager.health_check()
        except:
            supabase_status = False
    else:
        # supabase_manager가 None인 경우 직접 테스트
        try:
            from supabase_client import get_supabase_manager
            test_manager = get_supabase_manager()
            supabase_status = test_manager.health_check()
        except:
            supabase_status = False
    
    scheduler_status = False
    if SCHEDULER_AVAILABLE and scheduler:
        try:
            scheduler_status = scheduler.running
        except:
            scheduler_status = False
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models": {
            "whisper": whisper_model is not None,
            "erp_extractor": erp_extractor is not None,
            "supabase": supabase_status
        },
        "scheduler": {
            "available": SCHEDULER_AVAILABLE,
            "running": scheduler_status
        }
    }

@app.get("/test")
async def test_endpoint():
    """간단한 테스트 엔드포인트"""
    return {
        "status": "ok",
        "message": "API 서버가 정상적으로 동작하고 있습니다",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/erp-sample-register", response_model=ERPRegisterResponse)
async def register_erp_sample(
    erp_data: ERPData, 
    extraction_id: Optional[int] = None,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    ERP 연동용 샘플 등록 API
    PRD 요구사항에 따른 테스트용 인터페이스
    """
    try:
        # Mock ERP ID 생성
        erp_id = f"mock{uuid.uuid4().hex[:8]}"
        
        logger.info(f"ERP 샘플 등록 요청 - ID: {erp_id}")
        logger.info(f"등록 데이터: {erp_data.dict()}")
        
        # 실제 ERP 시스템 연동 시뮬레이션 (여기서는 단순히 성공 응답)
        response_data = {
            "status": "success",
            "erp_id": erp_id,
            "message": "ERP 시스템에 정상적으로 등록되었습니다"
        }
        
        # Supabase에 등록 로그 저장
        if extraction_id and supabase_mgr:
            try:
                supabase_mgr.save_erp_register_log(
                    extraction_id=extraction_id,
                    erp_id=erp_id,
                    status="success",
                    response_data=response_data
                )
                logger.info(f"ERP 등록 로그 저장 완료 - 추출 ID: {extraction_id}")
            except Exception as e:
                logger.warning(f"ERP 등록 로그 저장 실패: {e}")
        
        response = ERPRegisterResponse(**response_data)
        return response
        
    except Exception as e:
        logger.error(f"ERP 등록 실패: {e}")
        
        # 실패 로그도 저장
        if extraction_id and supabase_mgr:
            try:
                supabase_mgr.save_erp_register_log(
                    extraction_id=extraction_id,
                    erp_id="",
                    status="failed",
                    response_data={"error": str(e)}
                )
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"ERP 등록 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/stt-process", response_model=STTResponse)
async def process_audio_file(
    file: UploadFile = File(..., description="업로드할 음성 파일"),
    model_name: str = "base",
    language: Optional[str] = None,
    enable_diarization: bool = True,
    extract_erp: bool = True,
    save_to_db: bool = True,
    whisper_model=Depends(get_whisper_model),
    erp_extractor=Depends(get_erp_extractor),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    음성 파일 STT 처리 및 ERP 항목 추출 API
    """
    start_time = datetime.now()
    file_id = f"stt_{uuid.uuid4().hex[:8]}"
    
    # 'auto' 언어 설정을 None으로 변환
    if language == 'auto':
        language = None
    
    try:
        logger.info(f"STT 처리 시작 - File ID: {file_id}, 파일명: {file.filename}")
        
        # 파일 형식 검증
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.flac']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
            )
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Whisper STT 처리
            logger.info(f"Whisper STT 처리 중 - 모델: {model_name}")
            
            # 모델 캐싱으로 성능 최적화
            if model_name in cached_whisper_models:
                logger.info(f"캐시된 모델 사용: {model_name}")
                current_model = cached_whisper_models[model_name]
            elif model_name == "base" and whisper_model is not None:
                logger.info("기본 base 모델 사용")
                current_model = whisper_model
                cached_whisper_models["base"] = whisper_model
            else:
                logger.info(f"새 모델 로딩 중: {model_name}")
                logger.warning(f"⚠️ 모델 '{model_name}' 다운로드가 필요할 수 있습니다. 시간이 오래 걸릴 수 있습니다.")
                
                try:
                    # 모델 로딩에 시간이 오래 걸릴 수 있으므로 로깅 강화
                    import time
                    start_loading_time = time.time()
                    current_model = whisper.load_model(model_name)
                    loading_time = time.time() - start_loading_time
                    logger.info(f"✅ 모델 '{model_name}' 로딩 완료 (소요시간: {loading_time:.2f}초)")
                    cached_whisper_models[model_name] = current_model
                except Exception as model_error:
                    logger.error(f"❌ 모델 '{model_name}' 로딩 실패: {model_error}")
                    
                    # 모델 로딩 실패 시 기본 모델로 폴백
                    if model_name != "base" and whisper_model is not None:
                        logger.info("🔄 기본 'base' 모델로 폴백합니다...")
                        current_model = whisper_model
                        cached_whisper_models["base"] = whisper_model
                    else:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Whisper 모델 '{model_name}' 로딩에 실패했습니다: {str(model_error)}"
                        )
            
            # STT 실행 (VAD 필터 옵션 적용 - 속도 향상)
            result = current_model.transcribe(
                temp_file_path, 
                language=language,
                verbose=True,
                no_speech_threshold=0.6,  # 음성 없는 구간 감지 임계값 (속도 향상)
                logprob_threshold=-1.0,   # 로그 확률 임계값 (품질 향상)
                compression_ratio_threshold=2.4,  # 압축 비율 임계값 (효율성 향상)
                condition_on_previous_text=True,  # 이전 텍스트 조건화 (정확도 향상)
                word_timestamps=False  # 단어별 타임스탬프 비활성화 (속도 최적화)
            )
            
            # 세그먼트 데이터 처리 (단순화: 원본 + 후처리)
            segments = []
            original_segments = []  # 원본 세그먼트 보존
            
            # 도메인 데이터 가져오기 (통합 후처리용)
            domain_data = None
            if extract_erp and erp_extractor is not None:
                try:
                    domain_data = domain_manager.get_domain_data()
                except Exception as e:
                    logger.warning(f"도메인 데이터 로드 실패: {e}")
            
            for i, segment in enumerate(result.get("segments", [])):
                original_text = segment["text"].strip()
                
                # 통합 후처리 적용 (음성 정규화 + 유사도 매핑)
                from postprocessor import comprehensive_postprocess
                processed_text = comprehensive_postprocess(original_text, domain_data)
                
                # 원본 세그먼트 저장
                original_segment = {
                    "id": i,
                    "text": original_text,
                    "start": segment["start"],
                    "end": segment["end"],
                    "speaker": f"Speaker_{i % 2}"
                }
                original_segments.append(original_segment)
                
                # 후처리된 세그먼트 저장 (메인 사용)
                segment_data = {
                    "id": i,
                    "text": processed_text,
                    "start": segment["start"],
                    "end": segment["end"],
                    "speaker": f"Speaker_{i % 2}"
                }
                segments.append(segment_data)
            
            # ERP 데이터 추출 (타임아웃 처리 개선)
            erp_data = None
            if extract_erp and segments and erp_extractor is not None:
                try:
                    logger.info("ERP 데이터 추출 중... (30초 타임아웃)")
                    erp_dict = erp_extractor.extract_from_segments(segments, filename=file.filename)
                    logger.info(f"추출된 ERP 딕셔너리: {erp_dict}")
                    
                    # ERPData 모델 생성 시 더 자세한 에러 로깅
                    try:
                        erp_data = ERPData(**erp_dict)
                        logger.info(f"ERP 데이터 추출 완료: {erp_dict}")
                    except Exception as validation_error:
                        logger.error(f"ERPData 모델 생성 실패: {validation_error}")
                        logger.error(f"문제가 된 데이터: {erp_dict}")
                        logger.info("ERP 추출을 건너뛰고 STT 결과만 반환합니다.")
                        erp_data = None
                        
                except TimeoutError as e:
                    logger.warning(f"ERP 데이터 추출 타임아웃: {e}")
                    logger.info("ERP 추출을 건너뛰고 STT 결과만 반환합니다.")
                except Exception as e:
                    logger.warning(f"ERP 데이터 추출 실패: {e}")
                    logger.info("ERP 추출을 건너뛰고 STT 결과만 반환합니다.")
            elif extract_erp and erp_extractor is None:
                logger.info("⚠️ ERP Extractor가 비활성화되어 있습니다. STT 결과만 반환합니다.")
            
            # 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 하이브리드 텍스트 생성 (원본 + 후처리)
            original_text = result["text"]
            processed_text = comprehensive_postprocess(original_text, domain_data)
            
            # Supabase에 STT 세션 저장 (항상 저장)
            session_id = None
            extraction_id = None
            
            if supabase_mgr:
                try:
                    logger.info("Supabase에 STT 결과 저장 중...")
                    
                    # STT 세션 생성 및 업데이트
                    session = supabase_mgr.create_stt_session(
                        file_name=file.filename,
                        file_id=file_id,
                        model_name=model_name,
                        language=language
                    )
                    session_id = session['id']
                    
                    # STT 결과 업데이트 (하이브리드: 원본 + 후처리)
                    supabase_mgr.update_stt_session(
                        session_id=session_id,
                        transcript=processed_text,  # 후처리된 텍스트를 메인으로 저장
                        original_transcript=original_text,  # 원본 텍스트 별도 저장
                        segments=segments,  # 후처리된 세그먼트
                        original_segments=original_segments,  # 원본 세그먼트 별도 저장
                        processing_time=processing_time,
                        status="completed"
                    )
                    
                    # ERP 추출 결과 저장 (save_to_db 옵션에 따라)
                    if erp_data and save_to_db:
                        erp_dict = erp_data.dict(by_alias=True)
                        extraction = supabase_mgr.save_erp_extraction(
                            session_id=session_id,
                            erp_data=erp_dict
                        )
                        extraction_id = extraction['id']
                        logger.info(f"ERP 추출 결과 저장 완료 - 추출 ID: {extraction_id}")
                    elif erp_data and not save_to_db:
                        logger.info("ERP 추출 결과는 생성되었지만 데이터베이스에 저장하지 않음 (save_to_db=false)")
                        
                    # ERP 시스템에 자동 등록 (DB 저장 옵션이 활성화된 경우)
                    if save_to_db and extraction_id:
                        try:
                            logger.info("ERP 시스템에 자동 등록 중...")
                            
                            # Mock ERP ID 생성
                            erp_id = f"auto{uuid.uuid4().hex[:8]}"
                            
                            # ERP 등록 시뮬레이션 (실제 ERP 시스템 연동 시 이 부분을 수정)
                            erp_response_data = {
                                "status": "success",
                                "erp_id": erp_id,
                                "message": "STT 처리 중 ERP 시스템에 자동 등록되었습니다"
                            }
                            
                            # ERP 등록 로그 저장
                            supabase_mgr.save_erp_register_log(
                                extraction_id=extraction_id,
                                erp_id=erp_id,
                                status="success",
                                response_data=erp_response_data
                            )
                            
                            logger.info(f"ERP 자동 등록 완료 - ERP ID: {erp_id}, 추출 ID: {extraction_id}")
                            
                        except Exception as e:
                            logger.warning(f"ERP 자동 등록 실패 (계속 진행): {e}")
                            # 실패 로그도 저장
                            try:
                                supabase_mgr.save_erp_register_log(
                                    extraction_id=extraction_id,
                                    erp_id="",
                                    status="failed",
                                    response_data={"error": str(e)}
                                )
                            except:
                                pass
                    
                    logger.info(f"Supabase 저장 완료 - 세션 ID: {session_id}")
                    
                except Exception as e:
                    logger.warning(f"Supabase 저장 실패 (계속 진행): {e}")
            
            # 응답 생성 (하이브리드: 원본 + 후처리)
            response = STTResponse(
                status="success",
                transcript=processed_text,  # 후처리된 텍스트를 메인으로 반환
                segments=segments,  # 후처리된 세그먼트
                erp_data=erp_data,
                processing_time=processing_time,
                file_id=file_id,
                original_transcript=original_text,  # 원본 텍스트
                original_segments=original_segments  # 원본 세그먼트
            )
            
            # 응답에 DB 저장 정보 추가 (동적 필드)
            if session_id:
                response.session_id = session_id
            if extraction_id:
                response.extraction_id = extraction_id
            
            logger.info(f"STT 처리 완료 - File ID: {file_id}, 처리시간: {processing_time:.2f}초")
            return response
            
        finally:
            # 임시 파일 정리
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT 처리 실패 - File ID: {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"STT 처리 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/stt-process-file", response_model=STTResponse)
async def process_audio_file_from_directory(
    filename: str,
    model_name: str = "base",
    language: Optional[str] = None,
    enable_diarization: bool = True,
    extract_erp: bool = True,
    save_to_db: bool = True,
    whisper_model=Depends(get_whisper_model),
    erp_extractor=Depends(get_erp_extractor),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    src_record 디렉토리의 음성 파일 STT 처리 및 ERP 항목 추출 API
    """
    start_time = datetime.now()
    file_id = f"stt_{uuid.uuid4().hex[:8]}"
    
    # 'auto' 언어 설정을 None으로 변환
    if language == 'auto':
        language = None
    
    try:
        # 파일 경로 검증 (일자별 폴더 구조 지원)
        # filename이 "날짜폴더/파일명" 형식이거나 단순히 "파일명"일 수 있음
        file_path = os.path.join(AUDIO_DIRECTORY, filename)
        
        # Windows 경로 정규화
        file_path = os.path.normpath(file_path)
        
        # 절대 경로로 변환 (Whisper가 상대 경로에서 문제가 있을 수 있음)
        file_path = os.path.abspath(file_path)
        
        logger.info(f"파일 경로 확인 - 요청된 파일명: {filename}")
        logger.info(f"파일 경로 확인 - 구성된 경로: {file_path}")
        logger.info(f"파일 경로 확인 - 파일 존재 여부: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, 
                detail=f"파일을 찾을 수 없습니다: {filename} (경로: {file_path})"
            )
        
        if not os.path.isfile(file_path):
            raise HTTPException(
                status_code=400, 
                detail=f"유효한 파일이 아닙니다: {filename} (경로: {file_path})"
            )
        
        # 파일 형식 검증 (실제 파일명에서 확장자 추출)
        actual_filename = os.path.basename(filename)  # 경로에서 파일명만 추출
        file_extension = os.path.splitext(actual_filename)[1].lower()
        
        if file_extension not in SUPPORTED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(SUPPORTED_AUDIO_EXTENSIONS)}"
            )
        
        logger.info(f"STT 처리 시작 - File ID: {file_id}, 파일경로: {file_path}")
        
        # Whisper STT 처리
        logger.info(f"Whisper STT 처리 중 - 모델: {model_name}")
        
        # 모델 캐싱으로 성능 최적화
        if model_name in cached_whisper_models:
            logger.info(f"캐시된 모델 사용: {model_name}")
            current_model = cached_whisper_models[model_name]
        elif model_name == "base" and whisper_model is not None:
            logger.info("기본 base 모델 사용")
            current_model = whisper_model
            cached_whisper_models["base"] = whisper_model
        else:
            logger.info(f"새 모델 로딩 중: {model_name}")
            logger.warning(f"⚠️ 모델 '{model_name}' 다운로드가 필요할 수 있습니다. 시간이 오래 걸릴 수 있습니다.")
            
            try:
                # 모델 로딩에 시간이 오래 걸릴 수 있으므로 로깅 강화
                import time
                start_loading_time = time.time()
                current_model = whisper.load_model(model_name)
                loading_time = time.time() - start_loading_time
                logger.info(f"✅ 모델 '{model_name}' 로딩 완료 (소요시간: {loading_time:.2f}초)")
                cached_whisper_models[model_name] = current_model
            except Exception as model_error:
                logger.error(f"❌ 모델 '{model_name}' 로딩 실패: {model_error}")
                
                # 모델 로딩 실패 시 기본 모델로 폴백
                if model_name != "base" and whisper_model is not None:
                    logger.info("🔄 기본 'base' 모델로 폴백합니다...")
                    current_model = whisper_model
                    cached_whisper_models["base"] = whisper_model
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Whisper 모델 '{model_name}' 로딩에 실패했습니다: {str(model_error)}"
                    )
        
        # STT 실행
        logger.info(f"Whisper transcribe 시작 - 파일: {file_path}")
        logger.info(f"Whisper transcribe 시작 - 언어: {language}")
        
        try:
            result = current_model.transcribe(
                file_path, 
                language=language,
                verbose=True,
                no_speech_threshold=0.6,  # 음성 없는 구간 감지 임계값 (속도 향상)
                logprob_threshold=-1.0,   # 로그 확률 임계값 (품질 향상)
                compression_ratio_threshold=2.4,  # 압축 비율 임계값 (효율성 향상)
                condition_on_previous_text=True,  # 이전 텍스트 조건화 (정확도 향상)
                word_timestamps=False  # 단어별 타임스탬프 비활성화 (속도 최적화)
            )
            logger.info(f"Whisper transcribe 완료 - 텍스트 길이: {len(result.get('text', ''))}")
        except Exception as transcribe_error:
            logger.error(f"Whisper transcribe 실패 - 파일: {file_path}")
            logger.error(f"Whisper transcribe 실패 - 오류: {transcribe_error}")
            logger.error(f"Whisper transcribe 실패 - 오류 타입: {type(transcribe_error).__name__}")
            
            # FFmpeg 관련 오류 감지
            error_msg = str(transcribe_error)
            if "WinError 2" in error_msg or "CreateProcess" in error_msg:
                raise HTTPException(
                    status_code=500,
                    detail="FFmpeg가 설치되지 않았습니다. Whisper는 오디오 처리를 위해 FFmpeg가 필요합니다. FFmpeg를 설치한 후 다시 시도해주세요."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"음성 인식 처리 실패: {str(transcribe_error)}"
                )
        
        # 세그먼트 데이터 처리 (단순화: 원본 + 후처리)
        segments = []
        original_segments = []  # 원본 세그먼트 보존
        
        # 도메인 데이터 가져오기 (통합 후처리용)
        domain_data = None
        if extract_erp and erp_extractor is not None:
            try:
                domain_data = domain_manager.get_domain_data()
            except Exception as e:
                logger.warning(f"도메인 데이터 로드 실패: {e}")
        
        for i, segment in enumerate(result.get("segments", [])):
            original_text = segment["text"].strip()
            
            # 통합 후처리 적용 (음성 정규화 + 유사도 매핑)
            from postprocessor import comprehensive_postprocess
            processed_text = comprehensive_postprocess(original_text, domain_data)
            
            # 원본 세그먼트 저장
            original_segment = {
                "id": i,
                "text": original_text,
                "start": segment["start"],
                "end": segment["end"],
                "speaker": f"Speaker_{i % 2}"
            }
            original_segments.append(original_segment)
            
            # 후처리된 세그먼트 저장 (메인 사용)
            segment_data = {
                "id": i,
                "text": processed_text,
                "start": segment["start"],
                "end": segment["end"],
                "speaker": f"Speaker_{i % 2}"
            }
            segments.append(segment_data)
        
        # ERP 데이터 추출 (타임아웃 처리 개선)
        erp_data = None
        if extract_erp and segments and erp_extractor is not None:
            try:
                logger.info("ERP 데이터 추출 중... (30초 타임아웃)")
                erp_dict = erp_extractor.extract_from_segments(segments, filename=filename)
                logger.info(f"추출된 ERP 딕셔너리: {erp_dict}")
                
                # ERPData 모델 생성 시 더 자세한 에러 로깅
                try:
                    erp_data = ERPData(**erp_dict)
                    logger.info(f"ERP 데이터 추출 완료: {erp_dict}")
                except Exception as validation_error:
                    logger.error(f"ERPData 모델 생성 실패: {validation_error}")
                    logger.error(f"문제가 된 데이터: {erp_dict}")
                    logger.info("ERP 추출을 건너뛰고 STT 결과만 반환합니다.")
                    erp_data = None
                    
            except TimeoutError as e:
                logger.warning(f"ERP 데이터 추출 타임아웃: {e}")
                logger.info("ERP 추출을 건너뛰고 STT 결과만 반환합니다.")
            except Exception as e:
                logger.warning(f"ERP 데이터 추출 실패: {e}")
                logger.info("ERP 추출을 건너뛰고 STT 결과만 반환합니다.")
        elif extract_erp and erp_extractor is None:
            logger.info("⚠️ ERP Extractor가 비활성화되어 있습니다. STT 결과만 반환합니다.")
        
        # 처리 시간 계산
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 하이브리드 텍스트 생성 (원본 + 후처리)
        original_text = result["text"]
        processed_text = comprehensive_postprocess(original_text, domain_data)
        
        # Supabase에 STT 세션 저장 (항상 저장)
        session_id = None
        extraction_id = None
        
        if supabase_mgr:
            try:
                logger.info("Supabase에 STT 결과 저장 중...")
                
                # STT 세션 생성 및 업데이트
                session = supabase_mgr.create_stt_session(
                    file_name=filename,
                    file_id=file_id,
                    model_name=model_name,
                    language=language
                )
                session_id = session['id']
                
                # STT 결과 업데이트 (하이브리드: 원본 + 후처리)
                supabase_mgr.update_stt_session(
                    session_id=session_id,
                    transcript=processed_text,  # 후처리된 텍스트를 메인으로 저장
                    original_transcript=original_text,  # 원본 텍스트 별도 저장
                    segments=segments,  # 후처리된 세그먼트
                    original_segments=original_segments,  # 원본 세그먼트 별도 저장
                    processing_time=processing_time,
                    status="completed"
                )
                
                # ERP 추출 결과 저장 (save_to_db 옵션에 따라)
                if erp_data and save_to_db:
                    erp_dict = erp_data.dict(by_alias=True)
                    extraction = supabase_mgr.save_erp_extraction(
                        session_id=session_id,
                        erp_data=erp_dict
                    )
                    extraction_id = extraction['id']
                    logger.info(f"ERP 추출 결과 저장 완료 - 추출 ID: {extraction_id}")
                elif erp_data and not save_to_db:
                    logger.info("ERP 추출 결과는 생성되었지만 데이터베이스에 저장하지 않음 (save_to_db=false)")
                
                # ERP 시스템에 자동 등록 (DB 저장 옵션이 활성화된 경우)
                if save_to_db and extraction_id:
                    try:
                        logger.info("ERP 시스템에 자동 등록 중...")
                        
                        # Mock ERP ID 생성
                        erp_id = f"auto{uuid.uuid4().hex[:8]}"
                        
                        # ERP 등록 시뮬레이션 (실제 ERP 시스템 연동 시 이 부분을 수정)
                        erp_response_data = {
                            "status": "success",
                            "erp_id": erp_id,
                            "message": "STT 처리 중 ERP 시스템에 자동 등록되었습니다"
                        }
                        
                        # ERP 등록 로그 저장
                        supabase_mgr.save_erp_register_log(
                            extraction_id=extraction_id,
                            erp_id=erp_id,
                            status="success",
                            response_data=erp_response_data
                        )
                        
                        logger.info(f"ERP 자동 등록 완료 - ERP ID: {erp_id}, 추출 ID: {extraction_id}")
                        
                    except Exception as e:
                        logger.warning(f"ERP 자동 등록 실패 (계속 진행): {e}")
                        # 실패 로그도 저장
                        try:
                            supabase_mgr.save_erp_register_log(
                                extraction_id=extraction_id,
                                erp_id="",
                                status="failed",
                                response_data={"error": str(e)}
                            )
                        except:
                            pass
                
                logger.info(f"Supabase 저장 완료 - 세션 ID: {session_id}")
                
            except Exception as e:
                logger.warning(f"Supabase 저장 실패 (계속 진행): {e}")
        
        # 응답 생성 (하이브리드: 원본 + 후처리)
        response = STTResponse(
            status="success",
            transcript=processed_text,  # 후처리된 텍스트를 메인으로 반환
            segments=segments,  # 후처리된 세그먼트
            erp_data=erp_data,
            processing_time=processing_time,
            file_id=file_id,
            original_transcript=original_text,  # 원본 텍스트
            original_segments=original_segments  # 원본 세그먼트
        )
        
        # 응답에 DB 저장 정보 추가 (동적 필드)
        if session_id:
            response.session_id = session_id
        if extraction_id:
            response.extraction_id = extraction_id
        
        logger.info(f"STT 처리 완료 - File ID: {file_id}, 처리시간: {processing_time:.2f}초")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT 처리 실패 - File ID: {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"STT 처리 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/extract-erp")
async def extract_erp_from_text(
    conversation_text: str,
    erp_extractor=Depends(get_erp_extractor)
):
    """
    텍스트에서 직접 ERP 항목을 추출하는 API
    """
    try:
        logger.info("텍스트에서 ERP 데이터 추출 중...")
        
        erp_dict = erp_extractor.extract_erp_data(conversation_text)
        erp_data = ERPData(**erp_dict)
        
        return {
            "status": "success",
            "erp_data": erp_data,
            "message": "ERP 데이터 추출 완료"
        }
        
    except Exception as e:
        logger.error(f"ERP 데이터 추출 실패: {e}")
        raise HTTPException(status_code=500, detail=f"ERP 데이터 추출 중 오류가 발생했습니다: {str(e)}")

# STN 도메인 데이터 연동 API들

@app.get("/api/domain-stats")
async def get_domain_stats():
    """도메인 데이터 통계 조회"""
    try:
        return domain_manager.get_domain_stats()
    except Exception as e:
        logger.error(f"도메인 통계 조회 실패: {e}")
        return {"available": False, "error": str(e)}

@app.post("/api/reload-domain")
async def reload_domain():
    """
    도메인 데이터 핫리로드 API
    - 서버 재시작 없이 Excel 파일 변경사항 반영
    - 캐시 초기화 및 새 데이터 로드
    """
    try:
        logger.info("🔄 도메인 데이터 핫리로드 시작...")
        
        # 도메인 매니저에서 새 데이터 로드
        domain_manager._load_domain_data()
        
        # 통계 정보
        stats = domain_manager.get_domain_stats()
        
        logger.info("✅ 도메인 데이터 핫리로드 완료")
        return {
            "status": "success",
            "message": "도메인 데이터 리로드 완료",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 도메인 데이터 리로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"도메인 데이터 리로드 실패: {str(e)}")

class ERPExtractionRequest(BaseModel):
    """ERP 추출 요청 모델"""
    transcript_text: str
    use_legacy_format: bool = True
    temperature: float = 0.1
    max_tokens: int = 500

@app.post("/api/extract-erp-enhanced")
async def extract_erp_enhanced(request: ERPExtractionRequest):
    """
    개선된 ERP 추출 API
    - STN 도메인 데이터 활용
    - 실시간 검증 및 후처리
    - 레거시 호환성 지원
    """
    try:
        logger.info("🔍 개선된 ERP 추출 시작...")
        
        # 도메인 데이터 확인
        domain_data = domain_manager.get_domain_data()
        
        # 1. 프롬프트 구성
        system_prompt = domain_manager.build_enhanced_system_prompt()
        user_prompt = _build_enhanced_user_prompt(request.transcript_text, domain_data)
        
        # 2. OpenAI API 호출
        api_key = os.getenv('OPENAI_API_KEY')
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        raw_content = response.choices[0].message.content.strip()
        logger.info(f"GPT 원시 응답: {raw_content}")
        
        # 3. JSON 파싱
        try:
            raw_json = json.loads(raw_content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            # 기본값 반환
            raw_json = {"장비명": None, "장애유형": None, "요청유형": None, "위치": None}
        
        # 4. 후처리 (라벨→코드 변환, 모델명 매핑 등)
        processed_payload = postprocess_to_codes(raw_json, domain_data)
        
        # 5. 스키마 검증
        try:
            validate_payload(processed_payload, domain_data)
            validation_stats = get_validation_stats(processed_payload, domain_data)
        except Exception as e:
            logger.warning(f"스키마 검증 실패: {e}")
            # 검증 실패해도 계속 진행
            validation_stats = {"valid_equipment": False, "valid_error": False, "valid_request": False, "warnings": [str(e)]}
        
        # 6. 응답 구성
        result = {
            "status": "success",
            "stn_format": processed_payload,
            "validation": validation_stats,
            "raw_gpt_response": raw_json,
            "processing_info": {
                "model": "gpt-3.5-turbo",
                "temperature": request.temperature,
                "domain_data_used": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # 7. 레거시 형식 변환 (옵션)
        if request.use_legacy_format:
            # 파일명 정보가 없으므로 빈 문자열 전달 (세션 재처리 시에는 파일명 정보 없음)
            legacy_data = convert_to_legacy_erp_format(processed_payload, request.transcript_text, "")
            result["legacy_format"] = legacy_data
        
        logger.info("✅ 개선된 ERP 추출 완료")
        return result
        
    except Exception as e:
        logger.error(f"❌ ERP 추출 실패: {e}")
        raise HTTPException(status_code=500, detail=f"ERP 추출 중 오류 발생: {str(e)}")

# 데이터 관리 엔드포인트들

@app.get("/api/sessions")
async def get_stt_sessions(
    limit: int = 50, 
    offset: int = 0
):
    """STT 세션 목록 조회"""
    try:
        # 환경변수 강제 로드 (절대 경로 사용)
        from dotenv import load_dotenv
        import os
        config_path = os.path.join(os.getcwd(), 'config.env')
        load_dotenv(config_path)
        
        # 환경변수 확인
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            return {
                "status": "error",
                "message": f"환경변수 로드 실패 - URL: {bool(supabase_url)}, KEY: {bool(supabase_key)}",
                "sessions": [],
                "total": 0
            }
        
        # 직접 Supabase 매니저 생성
        from supabase_client import get_supabase_manager
        supabase_mgr = get_supabase_manager()
        
        sessions = supabase_mgr.get_stt_sessions(limit=limit, offset=offset)
        return {
            "status": "success",
            "sessions": sessions,
            "total": len(sessions)
        }
    except Exception as e:
        logger.error(f"세션 목록 조회 실패: {e}")
        return {
            "status": "error",
            "message": f"데이터베이스 연결 실패: {str(e)}",
            "sessions": [],
            "total": 0
        }

@app.get("/api/sessions/{session_id}")
async def get_stt_session(
    session_id: int,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """특정 STT 세션 상세 조회"""
    if not supabase_mgr:
        raise HTTPException(status_code=503, detail="Supabase가 설정되지 않았습니다")
    
    try:
        session = supabase_mgr.get_stt_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # ERP 추출 결과도 함께 조회
        erp_extraction = supabase_mgr.get_erp_extraction(session_id)
        
        return {
            "status": "success",
            "session": session,
            "erp_extraction": erp_extraction
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"세션 조회 실패: {str(e)}")

@app.post("/api/sessions/{session_id}/extract-erp")
async def extract_erp_for_session(
    session_id: int,
    erp_extractor=Depends(get_erp_extractor),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """기존 STT 세션에 대한 ERP 재추출"""
    if not supabase_mgr:
        raise HTTPException(status_code=503, detail="Supabase가 설정되지 않았습니다")
    
    try:
        logger.info(f"세션 {session_id}에 대한 ERP 재추출 시작")
        
        # 세션 정보 조회
        session = supabase_mgr.get_stt_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # transcript 또는 segments 확인
        transcript = session.get('transcript')
        segments = session.get('segments')
        filename = session.get('file_name', '')  # 파일명 정보 추가
        
        if not transcript and not segments:
            raise HTTPException(status_code=400, detail="세션에 텍스트 데이터가 없습니다")
        
        # ERP 데이터 추출
        erp_data = None
        try:
            if segments:
                # 세그먼트가 있으면 세그먼트에서 추출
                logger.info("세그먼트에서 ERP 데이터 추출 중...")
                
                # segments가 문자열인 경우 JSON으로 파싱
                if isinstance(segments, str):
                    try:
                        segments = json.loads(segments)
                        logger.info("세그먼트 JSON 파싱 완료")
                    except json.JSONDecodeError as e:
                        logger.warning(f"세그먼트 JSON 파싱 실패: {e}")
                        # 파싱 실패 시 전체 텍스트 사용
                        segments = None
                
                if segments and isinstance(segments, list):
                    erp_dict = erp_extractor.extract_from_segments(segments, filename=filename)
                else:
                    logger.info("세그먼트 데이터가 유효하지 않아 전체 텍스트 사용")
                    erp_dict = erp_extractor.extract_erp_data(transcript, filename=filename)
            else:
                # 세그먼트가 없으면 전체 텍스트에서 추출
                logger.info("전체 텍스트에서 ERP 데이터 추출 중...")
                erp_dict = erp_extractor.extract_erp_data(transcript, filename=filename)
            
            erp_data = ERPData(**erp_dict)
            logger.info(f"ERP 데이터 추출 완료: {erp_dict}")
            
        except Exception as e:
            logger.error(f"ERP 데이터 추출 실패: {e}")
            raise HTTPException(status_code=500, detail=f"ERP 데이터 추출 실패: {str(e)}")
        
        # 기존 ERP 추출 결과 확인
        existing_extraction = supabase_mgr.get_erp_extraction(session_id)
        
        extraction_id = None
        if existing_extraction:
            # 기존 추출 결과 업데이트
            logger.info(f"기존 ERP 추출 결과 업데이트 - 추출 ID: {existing_extraction['id']}")
            updated_extraction = supabase_mgr.update_erp_extraction(
                extraction_id=existing_extraction['id'],
                erp_data=erp_data.dict(by_alias=True)
            )
            extraction_id = updated_extraction['id']
        else:
            # 새로운 ERP 추출 결과 저장
            logger.info("새로운 ERP 추출 결과 저장")
            new_extraction = supabase_mgr.save_erp_extraction(
                session_id=session_id,
                erp_data=erp_data.dict(by_alias=True)
            )
            extraction_id = new_extraction['id']
        
        logger.info(f"ERP 재추출 완료 - 세션 ID: {session_id}, 추출 ID: {extraction_id}")
        
        return {
            "status": "success",
            "message": "ERP 재추출이 완료되었습니다",
            "session_id": session_id,
            "extraction_id": extraction_id,
            "erp_data": erp_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ERP 재추출 실패 - 세션 ID: {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"ERP 재추출 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/extractions")
async def get_erp_extractions(
    limit: int = 50, 
    offset: int = 0,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """ERP 추출 결과 목록 조회"""
    # Supabase가 없는 경우 빈 목록 반환
    if not supabase_mgr:
        logger.warning("⚠️ Supabase 연결 없음. 빈 추출 결과 목록 반환")
        return {
            "status": "success",
            "message": "Supabase 연결 없음 - 빈 목록",
            "extractions": [],
            "total": 0,
            "note": "데이터베이스 연결이 필요한 기능입니다."
        }
    
    try:
        extractions = supabase_mgr.get_erp_extractions(limit=limit, offset=offset)
        return {
            "status": "success",
            "extractions": extractions,
            "total": len(extractions)
        }
    except Exception as e:
        logger.error(f"추출 결과 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"추출 결과 목록 조회 실패: {str(e)}")

@app.get("/api/statistics")
async def get_system_statistics(
    date_filter: Optional[str] = None,
    month_filter: Optional[str] = None,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    시스템 통계 조회
    
    Args:
        date_filter: YYYY-MM-DD 형식의 특정 날짜 필터
        month_filter: YYYY-MM 형식의 월별 필터
    """
    # Supabase가 없는 경우 기본 통계 반환
    if not supabase_mgr:
        logger.warning("⚠️ Supabase 연결 없음. 기본 통계 반환")
        return {
            "status": "success",
            "message": "Supabase 연결 없음 - 기본 통계",
            "statistics": {
                "total_sessions": 0,
                "total_extractions": 0,
                "success_rate": 0.0,
                "today_processed": 0,
                "avg_processing_time": 0.0,
                "note": "Supabase 연결이 필요한 상세 통계는 제공되지 않습니다."
            },
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # 날짜 필터링 파라미터 결정
        filter_params = {}
        if date_filter:
            filter_params['date_filter'] = date_filter
        elif month_filter:
            filter_params['month_filter'] = month_filter
        
        stats = supabase_mgr.get_statistics(**filter_params)
        return {
            "status": "success",
            "statistics": stats,
            "applied_filter": {
                "date_filter": date_filter,
                "month_filter": month_filter
            }
        }
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@app.get("/api/audio-files")
async def get_audio_files():
    """
    src_record 디렉토리에서 사용 가능한 음성 파일 목록을 조회
    - 기존 src_record 직접 하위 파일들
    - 일자별 폴더(YYYY-MM-DD) 내의 파일들
    """
    try:
        if not os.path.exists(AUDIO_DIRECTORY):
            return {
                "status": "error",
                "message": f"음성 파일 디렉토리({AUDIO_DIRECTORY})가 존재하지 않습니다.",
                "files": [],
                "daily_files": {}
            }
        
        # 기존 src_record 직접 하위 음성 파일들 검색
        audio_files = []
        daily_files = {}
        
        for item in os.listdir(AUDIO_DIRECTORY):
            item_path = os.path.join(AUDIO_DIRECTORY, item)
            logger.info(f"Processing item: {item}, path: {item_path}")
            
            # 파일인 경우 (기존 방식)
            if os.path.isfile(item_path):
                file_extension = os.path.splitext(item)[1].lower()
                if file_extension in SUPPORTED_AUDIO_EXTENSIONS:
                    # 파일 정보 수집
                    file_stat = os.stat(item_path)
                    file_info = {
                        "filename": item,
                        "path": item,  # 기존 파일은 파일명만
                        "size": file_stat.st_size,
                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "extension": file_extension,
                        "location": "root"  # 루트 디렉토리 표시
                    }
                    audio_files.append(file_info)
            
            # 디렉토리인 경우 (일자별 폴더 확인)
            elif os.path.isdir(item_path):
                logger.info(f"Found directory: {item}")
                # YYYY-MM-DD 형식인지 확인
                try:
                    # 날짜 형식 검증
                    datetime.strptime(item, '%Y-%m-%d')
                    logger.info(f"Valid date format: {item}")
                    
                    # 일자별 폴더 내 음성 파일들 검색
                    daily_audio_files = []
                    for daily_filename in os.listdir(item_path):
                        daily_file_path = os.path.join(item_path, daily_filename)
                        
                        if os.path.isfile(daily_file_path):
                            file_extension = os.path.splitext(daily_filename)[1].lower()
                            if file_extension in SUPPORTED_AUDIO_EXTENSIONS:
                                # 파일 정보 수집
                                file_stat = os.stat(daily_file_path)
                                file_info = {
                                    "filename": daily_filename,
                                    "path": f"{item}/{daily_filename}",  # 날짜폴더/파일명
                                    "size": file_stat.st_size,
                                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                                    "extension": file_extension,
                                    "location": item  # 날짜 폴더명
                                }
                                daily_audio_files.append(file_info)
                    
                    # 폴더가 존재하면 음성 파일이 없어도 daily_files에 포함 (대시보드 필터링용)
                    daily_files[item] = daily_audio_files
                    logger.info(f"Added folder to daily_files: {item} with {len(daily_audio_files)} files")
                        
                except ValueError:
                    # 날짜 형식이 아닌 디렉토리는 무시
                    continue
        
        # 전체 파일 수 계산
        total_files = len(audio_files) + sum(len(files) for files in daily_files.values())
        
        # 파일명으로 정렬
        audio_files.sort(key=lambda x: x['filename'])
        for date_folder in daily_files:
            daily_files[date_folder].sort(key=lambda x: x['filename'])
        
        logger.info(f"발견된 음성 파일 수: 루트 {len(audio_files)}개, 일자별 {sum(len(files) for files in daily_files.values())}개 (총 {total_files}개)")
        
        return {
            "status": "success",
            "message": f"{total_files}개의 음성 파일을 발견했습니다.",
            "files": audio_files,  # 기존 루트 파일들
            "daily_files": daily_files,  # 일자별 폴더의 파일들
            "directory": AUDIO_DIRECTORY,
            "today_folder": datetime.now().strftime('%Y-%m-%d')  # 오늘 날짜 폴더명
        }
        
    except Exception as e:
        logger.error(f"음성 파일 목록 조회 실패: {e}")
        return {
            "status": "error",
            "message": f"음성 파일 목록 조회 중 오류가 발생했습니다: {str(e)}",
            "files": [],
            "daily_files": {}
        }

@app.get("/api/register-logs")
async def get_register_logs(
    limit: int = 50, 
    offset: int = 0,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """ERP 등록 로그 목록 조회"""
    # Supabase가 없는 경우 빈 목록 반환
    if not supabase_mgr:
        logger.warning("⚠️ Supabase 연결 없음. 빈 등록 로그 목록 반환")
        return {
            "status": "success",
            "message": "Supabase 연결 없음 - 빈 목록",
            "register_logs": [],
            "total": 0,
            "note": "데이터베이스 연결이 필요한 기능입니다."
        }
    
    try:
        register_logs = supabase_mgr.get_erp_register_logs(limit=limit, offset=offset)
        return {
            "status": "success",
            "register_logs": register_logs,
            "total": len(register_logs)
        }
    except Exception as e:
        logger.error(f"등록 로그 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"등록 로그 목록 조회 실패: {str(e)}")

# 디렉토리별 파일 처리 상태 관련 API

@app.get("/api/directory-summary")
async def get_directory_summary(folder: str = None, supabase_mgr=Depends(get_supabase_manager_dep)):
    """디렉토리별 처리 현황 요약 조회"""
    # Supabase가 없는 경우 빈 요약 반환
    if not supabase_mgr:
        logger.warning("⚠️ Supabase 연결 없음. 빈 디렉토리 요약 반환")
        return {
            "status": "success",
            "message": "Supabase 연결 없음 - 빈 요약",
            "summary": [],
            "total_directories": 0,
            "folder_filter": folder,
            "note": "데이터베이스 연결이 필요한 기능입니다."
        }
    
    try:
        summary = supabase_mgr.get_directory_processing_summary(folder=folder)
        return {
            "status": "success",
            "summary": summary,
            "total_directories": len(summary),
            "folder_filter": folder
        }
    except Exception as e:
        logger.error(f"디렉토리별 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"디렉토리별 요약 조회 실패: {str(e)}")

@app.get("/api/file-processing-status")
async def get_file_processing_status(
    directory: str = None,
    limit: int = 200,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """파일 처리 상태 조회 (디렉토리별 필터링 지원)"""
    # Supabase가 없는 경우 빈 목록 반환
    if not supabase_mgr:
        logger.warning("⚠️ Supabase 연결 없음. 빈 파일 처리 상태 목록 반환")
        return {
            "status": "success",
            "message": "Supabase 연결 없음 - 빈 목록",
            "files": [],
            "total": 0,
            "directory": directory if directory else "전체",
            "note": "데이터베이스 연결이 필요한 기능입니다."
        }
    
    try:
        if directory:
            files = supabase_mgr.get_file_processing_status_by_directory(directory=directory, limit=limit)
        else:
            files = supabase_mgr.get_file_processing_status(limit=limit)
        
        return {
            "status": "success",
            "files": files,
            "total": len(files),
            "directory": directory if directory else "전체"
        }
    except Exception as e:
        logger.error(f"파일 처리 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 처리 상태 조회 실패: {str(e)}")

@app.get("/api/check-file-processed")
async def check_file_processed(
    file_path: str,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """특정 파일의 처리 여부 확인"""
    if not supabase_mgr:
        raise HTTPException(status_code=503, detail="Supabase가 설정되지 않았습니다")
    
    try:
        result = supabase_mgr.check_file_processed(file_path)
        return {
            "status": "success",
            **result
        }
    except Exception as e:
        logger.error(f"파일 처리 상태 확인 실패 ({file_path}): {e}")
        raise HTTPException(status_code=500, detail=f"파일 처리 상태 확인 실패: {str(e)}")

@app.get("/api/processing-summary-enhanced")
async def get_processing_summary_enhanced(supabase_mgr=Depends(get_supabase_manager_dep)):
    """향상된 전체 처리 상태 요약 (디렉토리별 포함)"""
    # Supabase가 없는 경우 기본 요약 반환
    if not supabase_mgr:
        logger.warning("⚠️ Supabase 연결 없음. 기본 처리 요약 반환")
        return {
            "status": "success",
            "message": "Supabase 연결 없음 - 기본 요약",
            "overall_summary": {
                "total_files": 0,
                "processed_files": 0,
                "success_rate": 0.0,
                "avg_processing_time": 0.0
            },
            "directory_summaries": [],
            "recent_activity": [],
            "note": "데이터베이스 연결이 필요한 상세 정보입니다."
        }
    
    try:
        summary = supabase_mgr.get_processing_summary_enhanced()
        return {
            "status": "success",
            **summary
        }
    except Exception as e:
        logger.error(f"향상된 처리 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"향상된 처리 요약 조회 실패: {str(e)}")

@app.post("/api/update-directory-view")
async def update_directory_view(supabase_mgr=Depends(get_supabase_manager_dep)):
    """디렉토리별 처리 현황 뷰를 업데이트합니다"""
    if not supabase_mgr:
        raise HTTPException(status_code=503, detail="Supabase가 설정되지 않았습니다")
    
    try:
        success = supabase_mgr.update_directory_view()
        if success:
            return {
                "status": "success",
                "message": "directory_processing_summary 뷰가 성공적으로 업데이트되었습니다"
            }
        else:
            raise HTTPException(status_code=500, detail="뷰 업데이트에 실패했습니다")
    except Exception as e:
        logger.error(f"뷰 업데이트 API 오류: {e}")
        raise HTTPException(status_code=500, detail=f"뷰 업데이트 오류: {str(e)}")

@app.post("/api/ensure-daily-folder")
async def ensure_daily_folder():
    """
    수동으로 오늘 날짜 폴더 생성
    스케줄러와 별개로 필요시 수동으로 폴더를 생성할 수 있습니다.
    """
    try:
        today = datetime.now()
        daily_path = ensure_today_folder_exists()
        
        if daily_path:
            return {
                "success": True,
                "message": "일별 폴더 생성 완료",
                "path": daily_path,
                "date": today.strftime('%Y-%m-%d'),
                "created_at": today.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="폴더 생성에 실패했습니다")
            
    except Exception as e:
        logger.error(f"수동 폴더 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail=f"폴더 생성 실패: {str(e)}")

@app.get("/api/check-daily-folders")
async def check_daily_folders():
    """
    현재 생성된 일별 폴더들의 목록을 확인
    """
    try:
        if not os.path.exists(AUDIO_DIRECTORY):
            return {
                "success": True,
                "folders": [],
                "total_count": 0,
                "message": "src_record 디렉토리가 존재하지 않습니다"
            }
        
        # YYYY-MM-DD 형식의 폴더들만 필터링
        all_items = os.listdir(AUDIO_DIRECTORY)
        date_folders = []
        
        for item in all_items:
            item_path = os.path.join(AUDIO_DIRECTORY, item)
            if os.path.isdir(item_path):
                # YYYY-MM-DD 형식 검증
                try:
                    datetime.strptime(item, '%Y-%m-%d')
                    date_folders.append(item)
                except ValueError:
                    continue  # 날짜 형식이 아닌 폴더는 제외
        
        date_folders.sort(reverse=True)  # 최신 날짜부터 정렬
        
        return {
            "success": True,
            "folders": date_folders,
            "total_count": len(date_folders),
            "latest_folder": date_folders[0] if date_folders else None,
            "today_exists": datetime.now().strftime('%Y-%m-%d') in date_folders
        }
        
    except Exception as e:
        logger.error(f"일별 폴더 확인 API 오류: {e}")
        raise HTTPException(status_code=500, detail=f"폴더 확인 실패: {str(e)}")

@app.get("/api/environment-status")
async def get_environment_status():
    """환경변수 설정 상태 확인"""
    env_status = {}
    
    # OpenAI API Key 확인
    openai_key = os.getenv('OPENAI_API_KEY')
    env_status['OPENAI_API_KEY'] = bool(openai_key and openai_key not in ['your_openai_api_key_here', ''])
    
    # Supabase 설정 확인
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    env_status['SUPABASE_URL'] = bool(supabase_url and supabase_url not in ['your_supabase_url_here', ''])
    env_status['SUPABASE_ANON_KEY'] = bool(supabase_key and supabase_key not in ['your_supabase_anon_key_here', ''])
    
    # HuggingFace Token 확인
    hf_token = os.getenv('HUGGINGFACE_HUB_TOKEN')
    env_status['HUGGINGFACE_HUB_TOKEN'] = bool(hf_token and hf_token not in ['your_huggingface_token_here', ''])
    
    return {
        "status": "success",
        "environment_variables": env_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/model-status")
async def get_model_status():
    """모델 로딩 상태 확인"""
    try:
        model_status = {
            "whisper_base_loaded": whisper_model is not None,
            "cached_models": list(cached_whisper_models.keys()),
            "erp_extractor_loaded": erp_extractor is not None,
            "supabase_connected": supabase_manager is not None
        }
        
        # 캐시된 모델들의 상세 정보
        model_details = {}
        for model_name, model in cached_whisper_models.items():
            model_details[model_name] = {
                "loaded": model is not None,
                "type": str(type(model).__name__) if model else None
            }
        
        return {
            "status": "success",
            "model_status": model_status,
            "model_details": model_details,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"모델 상태 확인 중 오류: {e}")
        return {
            "status": "error",
            "message": f"모델 상태 확인 실패: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/clear-whisper-cache")
async def clear_whisper_cache():
    """손상된 Whisper 모델 캐시를 정리합니다"""
    try:
        # 메모리 캐시 정리
        clear_model_cache()
        
        # 파일 캐시 정리
        success, cleared_paths = clear_whisper_file_cache()
        
        if success:
            return {
                "status": "success",
                "message": "Whisper 캐시가 성공적으로 정리되었습니다.",
                "cleared_paths": cleared_paths,
                "action_required": "API 서버를 재시작하거나 새 모델을 로딩해주세요.",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "warning",
                "message": "정리할 캐시 파일이 없거나 일부 정리에 실패했습니다.",
                "cleared_paths": cleared_paths,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"캐시 정리 API 오류: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 정리 실패: {str(e)}")

@app.post("/api/reload-base-model")
async def reload_base_model():
    """기본 Whisper 모델을 다시 로딩합니다"""
    global whisper_model
    
    try:
        logger.info("기본 Whisper 모델 재로딩 시작...")
        
        # 기존 모델 정리
        if "base" in cached_whisper_models:
            del cached_whisper_models["base"]
        
        # 새로 로딩
        import time
        start_time = time.time()
        whisper_model = whisper.load_model("base")
        loading_time = time.time() - start_time
        
        # 캐시에 저장
        cached_whisper_models["base"] = whisper_model
        
        logger.info(f"기본 Whisper 모델 재로딩 완료 (소요시간: {loading_time:.2f}초)")
        
        return {
            "status": "success",
            "message": "기본 Whisper 모델이 성공적으로 재로딩되었습니다.",
            "loading_time": round(loading_time, 2),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"모델 재로딩 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 재로딩 실패: {str(e)}")

# 서버 시작 시 모델 초기화
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행되는 이벤트"""
    global scheduler
    logger.info("API 서버 시작 중...")
    
    # FFmpeg 경로 설정 (Windows winget 설치)
    try:
        import os
        ffmpeg_path = r"C:\Users\bangm\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-full_build\bin"
        if os.path.exists(ffmpeg_path):
            current_path = os.environ.get('PATH', '')
            if ffmpeg_path not in current_path:
                os.environ['PATH'] = current_path + os.pathsep + ffmpeg_path
                logger.info(f"FFmpeg 경로 추가됨: {ffmpeg_path}")
            else:
                logger.info("FFmpeg 경로가 이미 PATH에 있습니다.")
        else:
            logger.warning(f"FFmpeg 경로를 찾을 수 없습니다: {ffmpeg_path}")
    except Exception as e:
        logger.warning(f"FFmpeg 경로 설정 실패: {e}")
    
    try:
        # 모델 초기화
        initialize_models()
        
        # 일자별 폴더 생성
        daily_path = create_daily_directory()
        if daily_path:
            logger.info(f"일자별 폴더 설정 완료: {daily_path}")
        
        # 스케줄러 시작 (오류가 있어도 API 서버는 계속 실행)
        if SCHEDULER_AVAILABLE:
            try:
                scheduler = BackgroundScheduler()
                scheduler.add_job(
                    scheduled_daily_folder_creation,
                    CronTrigger(hour=0, minute=0),  # 매일 0시 실행
                    id='daily_folder_creation',
                    name='일별 폴더 자동 생성'
                )
                scheduler.start()
                logger.info("✅ 일별 폴더 생성 스케줄러 시작 완료 (매일 0시 실행)")
            except ImportError as e:
                logger.warning(f"⚠️ APScheduler 패키지가 설치되지 않았습니다: {e}")
                logger.warning("⚠️ 수동으로 설치하세요: pip install APScheduler>=3.10.0")
            except Exception as e:
                logger.error(f"⚠️ 스케줄러 시작 실패 (API 서버는 계속 실행): {e}")
        else:
            logger.warning("⚠️ APScheduler가 사용 불가능합니다. 일별 폴더 생성 스케줄러가 비활성화됩니다.")
        
        logger.info("API 서버 시작 완료")
    except Exception as e:
        logger.error(f"API 서버 시작 중 오류: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행되는 이벤트"""
    global scheduler
    logger.info("API 서버 종료 중...")
    try:
        if SCHEDULER_AVAILABLE and scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("✅ 스케줄러 종료 완료")
        logger.info("API 서버 종료 완료")
    except Exception as e:
        logger.error(f"API 서버 종료 중 오류: {e}")

# STN 도메인 데이터 연동 헬퍼 함수들



def _build_enhanced_user_prompt(transcript_text: str, domain_data: dict) -> str:
    """도메인 데이터 기반 사용자 프롬프트"""
    hints = []
    
    if domain_data and domain_data.get('hints'):
        # 각 카테고리에서 몇 개씩 선택
        hints.extend(domain_data['hints'].get('equipment', [])[:3])
        hints.extend(domain_data['hints'].get('errors', [])[:4])
        hints.extend(domain_data['hints'].get('requests', [])[:4])
    
    prompt = f"""[대화 내용]
{transcript_text}"""
    
    if hints:
        prompt += f"""

[표현 힌트]
{chr(10).join(hints[:10])}"""  # 최대 10개만
    
    return prompt


if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 