"""
STN 고객센터 STT 시스템 API 서버
FastAPI 기반 REST API 서버 - ERP 연동 및 STT 처리
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import os
import logging
import threading
from datetime import datetime

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

# 환경변수 로드
from dotenv import load_dotenv
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
            "detail": "요청 데이터 검증 실패",
            "errors": exc.errors(),
                "url": str(request.url),
            "method": request.method
        }
    )

# 스케줄러 설정
scheduler = None
if SCHEDULER_AVAILABLE:
    scheduler = BackgroundScheduler()
    logger.info("✅ 스케줄러가 활성화되었습니다")
else:
    logger.warning("⚠️ 스케줄러가 비활성화되었습니다")

# 일일 폴더 생성 함수들
def create_daily_directory():
    """오늘 날짜의 일일 폴더를 생성합니다"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    daily_path = os.path.join("src_record", today)
    
    if not os.path.exists(daily_path):
        os.makedirs(daily_path, exist_ok=True)
        logger.info(f"일일 폴더 생성: {daily_path}")
    else:
        logger.info(f"일일 폴더 이미 존재: {daily_path}")
            
    return daily_path

def create_daily_directory_with_date(target_date=None, auto_create=True):
    """특정 날짜의 일일 폴더를 생성합니다"""
    from datetime import datetime, timedelta
    
    if target_date is None:
        target_date = datetime.now()
    elif isinstance(target_date, str):
        try:
            target_date = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"잘못된 날짜 형식: {target_date}")
            return None
    
    date_str = target_date.strftime("%Y-%m-%d")
    daily_path = os.path.join("src_record", date_str)
    
    if not os.path.exists(daily_path):
        if auto_create:
            os.makedirs(daily_path, exist_ok=True)
            logger.info(f"일일 폴더 생성: {daily_path}")
        else:
            logger.info(f"일일 폴더가 존재하지 않음: {daily_path}")
            return None
    else:
        logger.info(f"일일 폴더 이미 존재: {daily_path}")
            
    return daily_path

def ensure_today_folder_exists():
    """오늘 폴더가 존재하는지 확인하고 없으면 생성"""
    create_daily_directory()

def scheduled_daily_folder_creation():
    """스케줄된 일일 폴더 생성 작업"""
    try:
        logger.info("🕐 스케줄된 일일 폴더 생성 작업 실행")
        create_daily_directory()
        logger.info("✅ 일일 폴더 생성 작업 완료")
    except Exception as e:
        logger.error(f"❌ 일일 폴더 생성 작업 실패: {e}")

def get_daily_directory_path(date_str=None):
    """일일 디렉토리 경로를 반환합니다"""
    from datetime import datetime
    
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    return os.path.join("src_record", date_str)

# 기본 엔드포인트들
@app.get("/")
async def root():
    """API 서버 상태 확인"""
    return {
        "message": "STN 고객센터 STT 시스템 API 서버가 정상적으로 실행 중입니다",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # Whisper 모델 상태 확인
        whisper_status = "not_loaded"
        try:
            from stt_handlers import whisper_model, cached_whisper_models
            if whisper_model is not None or cached_whisper_models:
                whisper_status = "loaded"
        except:
            whisper_status = "error"
        
        # 기본 상태 확인 (Admin UI 호환성을 위해 models 구조 사용)
        health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models": {
                "whisper": whisper_status == "loaded",  # boolean으로 변환
                "erp_extractor": True,  # GPT 모델은 항상 사용 가능
                "supabase": bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'))
            },
            "services": {
                "api_server": "running",
                "scheduler": "active" if scheduler and scheduler.running else "inactive",
                "whisper": whisper_status  # 실제 whisper 모델 상태
            }
        }
        
        # 환경변수 확인
        env_check = {
            "openai_api_key": bool(os.getenv('OPENAI_API_KEY')),
            "supabase_url": bool(os.getenv('SUPABASE_URL')),
            "supabase_key": bool(os.getenv('SUPABASE_ANON_KEY'))
        }
        health_status["environment"] = env_check
        
        return health_status
        
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    
@app.get("/test")
async def test_endpoint():
    """테스트 엔드포인트"""
    return {
        "message": "테스트 엔드포인트가 정상적으로 작동합니다",
        "timestamp": datetime.now().isoformat()
    }

# 라우터 등록
from stt_handlers import router as stt_router
from erp_handlers import router as erp_router
from admin_handlers import router as admin_router

app.include_router(stt_router)
app.include_router(erp_router)
app.include_router(admin_router)

# 앱 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행되는 이벤트"""
    logger.info("🚀 STN STT 시스템 API 서버 시작 중...")
    
    # 1. STT 모델 초기화
    try:
        from stt_handlers import initialize_models
        initialize_models()
        logger.info("✅ STT 모델 초기화 완료")
    except Exception as e:
        logger.error(f"❌ STT 모델 초기화 실패: {e}")
    
    # 2. 스케줄러 시작
    if scheduler and not scheduler.running:
        try:
            # 매일 자정에 일일 폴더 생성 작업 스케줄
            scheduler.add_job(
                scheduled_daily_folder_creation,
                CronTrigger(hour=0, minute=0),  # 매일 자정
                id='daily_folder_creation',
                name='일일 폴더 생성',
                replace_existing=True
            )
            
            scheduler.start()
            logger.info("✅ 스케줄러 시작 완료")
        except Exception as e:
            logger.error(f"❌ 스케줄러 시작 실패: {e}")
        
    # 3. 오늘 폴더 확인 및 생성
    try:
        ensure_today_folder_exists()
        logger.info("✅ 오늘 폴더 확인 완료")
    except Exception as e:
        logger.error(f"❌ 오늘 폴더 확인 실패: {e}")

    logger.info("🎉 STN STT 시스템 API 서버 시작 완료!")

# 앱 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행되는 이벤트"""
    logger.info("🛑 STN STT 시스템 API 서버 종료 중...")
    
    # 스케줄러 종료
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("✅ 스케줄러 종료 완료")
        except Exception as e:
            logger.error(f"❌ 스케줄러 종료 실패: {e}")
    
    # 모델 캐시 정리
    try:
        from stt_handlers import clear_model_cache
        clear_model_cache()
        logger.info("✅ 모델 캐시 정리 완료")
    except Exception as e:
        logger.error(f"❌ 모델 캐시 정리 실패: {e}")
    
    logger.info("👋 STN STT 시스템 API 서버 종료 완료!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
