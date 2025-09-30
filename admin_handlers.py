"""
관리/시스템 관련 핸들러
세션 관리, 통계, 파일 관리, 시스템 상태 등 관리 기능
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.params import Path as FastAPIPath
from typing import Optional, Dict, List
import os
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from supabase_client import get_supabase_manager
from stt_handlers import whisper_model, cached_whisper_models, clear_model_cache, clear_whisper_file_cache
from models import (
    ExtractionsResponse, SessionsResponse, SessionDetailResponse, 
    RegisterLogsResponse, StatisticsResponse, AudioFilesResponse,
    ERPReExtractionResponse, AudioFileInfo, SystemStatistics
)

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api", tags=["Admin"])

# 전역 변수들
AUDIO_DIRECTORY = "src_record"
SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac']


def get_supabase_manager_dep():
    """Supabase 매니저 의존성"""
    return get_supabase_manager()


@router.get("/sessions", response_model=SessionsResponse)
async def get_stt_sessions(
    limit: int = Query(50, description="조회할 세션 개수", ge=1, le=1000),
    offset: int = Query(0, description="시작 위치 (페이징)", ge=0),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    STT 세션 목록 조회
    
    처리된 STT 세션들의 목록을 조회합니다. 페이징을 지원하여 대량의 데이터를 효율적으로 처리할 수 있습니다.
    
    - **limit**: 한 번에 조회할 세션 개수 (1-1000)
    - **offset**: 시작 위치 (0부터 시작)
    
    Returns:
        STT 세션 목록과 전체 개수
    """
    try:
        if supabase_mgr:
            sessions = supabase_mgr.get_stt_sessions(limit=limit, offset=offset)
            return SessionsResponse(
                status="success",
                sessions=sessions,
                total=len(sessions)
            )
        else:
            return SessionsResponse(
                status="error",
                message="Supabase 연결이 없습니다",
                sessions=[],
                total=0
            )
    except Exception as e:
        logger.error(f"세션 목록 조회 실패: {e}")
        return SessionsResponse(
            status="error",
            message=f"데이터베이스 연결 실패: {str(e)}",
            sessions=[],
            total=0
        )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_stt_session(
    session_id: int = FastAPIPath(..., description="조회할 세션 ID", ge=1),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    특정 STT 세션 상세 조회
    
    지정된 세션 ID의 STT 세션 정보와 연결된 ERP 추출 결과를 함께 조회합니다.
    
    - **session_id**: 조회할 세션의 고유 ID (1 이상)
    
    Returns:
        STT 세션 상세 정보와 연결된 ERP 추출 결과
    """
    try:
        session = supabase_mgr.get_stt_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # ERP 추출 결과도 함께 조회
        extraction = supabase_mgr.get_erp_extraction(session_id)
        
        return SessionDetailResponse(
            status="success",
            session=session,
            extraction=extraction
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 조회 실패 - ID: {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"세션 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/extractions", response_model=ExtractionsResponse)
async def get_erp_extractions(
    limit: int = Query(50, description="조회할 추출 결과 개수", ge=1, le=1000),
    offset: int = Query(0, description="시작 위치 (페이징)", ge=0),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    ERP 추출 결과 목록 조회
    
    STT 처리 후 추출된 ERP 데이터들의 목록을 조회합니다. 페이징을 지원하여 대량의 데이터를 효율적으로 처리할 수 있습니다.
    
    - **limit**: 한 번에 조회할 추출 결과 개수 (1-1000)
    - **offset**: 시작 위치 (0부터 시작)
    
    Returns:
        ERP 추출 결과 목록과 전체 개수
    """
    try:
        extractions = supabase_mgr.get_erp_extractions(limit=limit, offset=offset)
        return ExtractionsResponse(
            status="success",
            extractions=extractions,
            total=len(extractions)
        )
    except Exception as e:
        logger.error(f"ERP 추출 결과 조회 실패: {e}")
        return ExtractionsResponse(
            status="error",
            message=f"데이터베이스 연결 실패: {str(e)}",
            extractions=[],
            total=0
        )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_system_statistics(
    date_filter: Optional[str] = Query(None, description="날짜 필터 (YYYY-MM-DD 형식)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    month_filter: Optional[str] = Query(None, description="월 필터 (YYYY-MM 형식)", regex=r"^\d{4}-\d{2}$"),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    시스템 통계 조회
    
    STT 세션, ERP 추출, 등록 현황 등의 시스템 통계를 조회합니다. 날짜별 또는 월별 필터링을 지원합니다.
    
    - **date_filter**: 특정 날짜의 통계 조회 (YYYY-MM-DD 형식)
    - **month_filter**: 특정 월의 통계 조회 (YYYY-MM 형식)
    
    Returns:
        시스템 통계 정보 (세션 수, 추출 수, 등록 현황, 평균 처리 시간 등)
    """
    try:
        stats = {
            "total_sessions": 0,
            "completed_sessions": 0,
            "failed_sessions": 0,
            "total_extractions": 0,
            "total_registers": 0,
            "success_registers": 0,
            "failed_registers": 0,
            "avg_processing_time": 0.0,
            "model_usage": {},
            "date_range": {
                "from": None,
                "to": None
            }
        }
        
        if supabase_mgr:
            # SupabaseManager의 get_statistics 메서드 사용 (필터링 지원)
            filter_params = {}
            if date_filter:
                filter_params['date_filter'] = date_filter
            elif month_filter:
                filter_params['month_filter'] = month_filter
            
            stats = supabase_mgr.get_statistics(**filter_params)
        
        return StatisticsResponse(
            status="success",
            statistics=stats
        )
        
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        return StatisticsResponse(
            status="error",
            message=f"통계 조회 실패: {str(e)}",
            statistics=SystemStatistics(
                total_sessions=0,
                completed_sessions=0,
                failed_sessions=0,
                total_extractions=0,
                total_registers=0,
                success_registers=0,
                failed_registers=0,
                avg_processing_time=0.0,
                model_usage={}
            )
        )


@router.get("/audio-files", response_model=AudioFilesResponse)
async def get_audio_files():
    """
    음성 파일 목록 조회
    
    src_record 디렉토리에서 사용 가능한 음성 파일들의 목록을 조회합니다.
    직접 하위 파일들과 일자별 폴더(YYYY-MM-DD) 내의 파일들을 모두 포함합니다.
    
    지원하는 파일 형식: MP3, WAV, M4A, FLAC
    
    Returns:
        음성 파일 목록 (전체 파일과 일자별 파일 분류)
    """
    try:
        audio_files = []  # 루트 디렉토리 파일들
        daily_files = {}  # 일자별 폴더 파일들
        
        if not os.path.exists(AUDIO_DIRECTORY):
            return {
                "status": "success",
                "files": [],
                "daily_files": {},
                "total": 0,
                "message": f"디렉토리가 존재하지 않습니다: {AUDIO_DIRECTORY}"
            }
        
        # 1. 직접 하위 파일들 검색
        try:
            for file in os.listdir(AUDIO_DIRECTORY):
                file_path = os.path.join(AUDIO_DIRECTORY, file)
                if os.path.isfile(file_path):
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in SUPPORTED_AUDIO_EXTENSIONS:
                        file_info = {
                            "filename": file,
                            "path": file,
                            "size": os.path.getsize(file_path),
                            "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                            "type": "direct",
                            "extension": file_ext,
                            "location": "direct"
                        }
                        audio_files.append(file_info)
        except Exception as e:
            logger.warning(f"직접 하위 파일 검색 실패: {e}")
        
        # 2. 일자별 폴더 내 파일들 검색
        try:
            for item in os.listdir(AUDIO_DIRECTORY):
                item_path = os.path.join(AUDIO_DIRECTORY, item)
                if os.path.isdir(item_path):
                    # YYYY-MM-DD 형식인지 확인
                    try:
                        datetime.strptime(item, "%Y-%m-%d")
                        daily_files[item] = []  # 일자별 폴더 초기화
                        
                        # 일자별 폴더 내 파일들 검색
                        for file in os.listdir(item_path):
                            file_path = os.path.join(item_path, file)
                            if os.path.isfile(file_path):
                                file_ext = os.path.splitext(file)[1].lower()
                                if file_ext in SUPPORTED_AUDIO_EXTENSIONS:
                                    file_info = {
                                        "filename": file,
                                        "path": f"{item}/{file}",  # 상대 경로
                                        "size": os.path.getsize(file_path),
                                        "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                                        "type": "daily_folder",
                                        "folder": item,
                                        "extension": file_ext,
                                        "location": "daily"
                                    }
                                    daily_files[item].append(file_info)
                    except ValueError:
                        # YYYY-MM-DD 형식이 아닌 폴더는 무시
                        continue
        except Exception as e:
            logger.warning(f"일자별 폴더 검색 실패: {e}")
        
        # 파일명으로 정렬
        audio_files.sort(key=lambda x: x["filename"])
        for date_folder in daily_files:
            daily_files[date_folder].sort(key=lambda x: x["filename"])
        
        # 전체 파일 수 계산
        total_files = len(audio_files) + sum(len(files) for files in daily_files.values())
        
        return AudioFilesResponse(
            status="success",
            message=f"총 {total_files}개의 음성 파일을 찾았습니다",
            files=audio_files,  # 루트 파일들
            daily_files=daily_files,  # 일자별 폴더 파일들
            directory=AUDIO_DIRECTORY,
            today_folder=datetime.now().strftime("%Y-%m-%d")
        )
        
    except Exception as e:
        logger.error(f"음성 파일 목록 조회 실패: {e}")
        return AudioFilesResponse(
            status="error",
            message=f"음성 파일 목록 조회 실패: {str(e)}",
            files=[],
            daily_files={},
            directory=AUDIO_DIRECTORY,
            today_folder=datetime.now().strftime("%Y-%m-%d")
        )


@router.get("/register-logs", response_model=RegisterLogsResponse)
async def get_register_logs(
    limit: int = Query(50, description="조회할 등록 로그 개수", ge=1, le=1000),
    offset: int = Query(0, description="시작 위치 (페이징)", ge=0),
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """
    ERP 등록 로그 조회
    
    ERP 시스템으로 등록을 시도한 로그들의 목록을 조회합니다. 
    등록 성공/실패 상태와 ERP 시스템 응답 데이터를 포함합니다.
    
    - **limit**: 한 번에 조회할 등록 로그 개수 (1-1000)
    - **offset**: 시작 위치 (0부터 시작)
    
    Returns:
        ERP 등록 로그 목록과 전체 개수
    """
    try:
        if supabase_mgr:
            logs = supabase_mgr.get_erp_register_logs(limit=limit, offset=offset)
            return RegisterLogsResponse(
                status="success",
                register_logs=logs,
                total=len(logs)
            )
        else:
            return RegisterLogsResponse(
                status="error",
                message="Supabase 연결이 없습니다",
                register_logs=[],
                total=0
            )
    except Exception as e:
        logger.error(f"등록 로그 조회 실패: {e}")
        return RegisterLogsResponse(
            status="error",
            message=f"등록 로그 조회 실패: {str(e)}",
            register_logs=[],
            total=0
        )


@router.get("/directory-summary")
async def get_directory_summary(folder: str = None, supabase_mgr=Depends(get_supabase_manager_dep)):
    """디렉토리별 처리 현황 요약 조회"""
    # Supabase가 없는 경우 빈 요약 반환
    if not supabase_mgr:
        return {
            "status": "success",
            "summary": {
                "total_files": 0,
                "processed_files": 0,
                "pending_files": 0,
                "processing_rate": 0.0
            },
            "message": "Supabase가 설정되지 않아 기본 요약만 제공됩니다."
        }
    
    try:
        # 전체 파일 목록 조회
        audio_files_response = await get_audio_files()
        all_files = audio_files_response.get("files", [])
        
        # 폴더별 필터링
        if folder:
            filtered_files = [f for f in all_files if f.get("folder") == folder]
        else:
            filtered_files = all_files
        
        total_files = len(filtered_files)
        
        # 처리된 파일 수 계산 (Supabase에서 확인)
        processed_count = 0
        for file_info in filtered_files:
            file_path = file_info["path"]
            # 파일이 처리되었는지 확인
            is_processed = supabase_mgr.check_file_processed(file_path)
            if is_processed:
                processed_count += 1
        
        pending_count = total_files - processed_count
        processing_rate = (processed_count / total_files * 100) if total_files > 0 else 0.0
        
        summary = {
            "total_files": total_files,
            "processed_files": processed_count,
            "pending_files": pending_count,
            "processing_rate": round(processing_rate, 2)
        }
        
        return {
            "status": "success",
            "summary": summary,
            "folder": folder,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"디렉토리 요약 조회 실패: {e}")
        return {
            "status": "error",
            "message": f"디렉토리 요약 조회 실패: {str(e)}",
            "summary": {}
        }


@router.get("/file-processing-status")
async def get_file_processing_status(
    directory: str = None,
    limit: int = 200,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """파일별 처리 상태 상세 조회"""
    try:
        # 전체 파일 목록 조회
        audio_files_response = await get_audio_files()
        all_files = audio_files_response.get("files", [])
        
        # 디렉토리별 필터링
        if directory:
            filtered_files = [f for f in all_files if f.get("folder") == directory]
        else:
            filtered_files = all_files
        
        # 제한 적용
        if limit > 0:
            filtered_files = filtered_files[:limit]
        
        # 각 파일의 처리 상태 확인
        file_statuses = []
        for file_info in filtered_files:
            file_path = file_info["path"]
            
            # 처리 상태 확인
            is_processed = False
            session_info = None
            
            if supabase_mgr:
                is_processed = supabase_mgr.check_file_processed(file_path)
                if is_processed:
                    # 세션 정보 조회
                    session_info = supabase_mgr.get_session_by_file_path(file_path)
            
            status_info = {
                "filename": file_info["filename"],
                "path": file_info["path"],
                "size": file_info["size"],
                "modified": file_info["modified"],
                "type": file_info["type"],
                "folder": file_info.get("folder"),
                "processed": is_processed,
                "session": session_info
            }
            file_statuses.append(status_info)
        
        return {
            "status": "success",
            "files": file_statuses,
            "total": len(file_statuses),
            "directory": directory,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"파일 처리 상태 조회 실패: {e}")
        return {
            "status": "error",
            "message": f"파일 처리 상태 조회 실패: {str(e)}",
            "files": [],
            "total": 0
        }


@router.get("/check-file-processed")
async def check_file_processed(
    file_path: str,
    supabase_mgr=Depends(get_supabase_manager_dep)
):
    """특정 파일의 처리 상태 확인"""
    try:
        is_processed = False
        session_info = None
        
        if supabase_mgr:
            is_processed = supabase_mgr.check_file_processed(file_path)
            if is_processed:
                session_info = supabase_mgr.get_session_by_file_path(file_path)
        
        return {
            "status": "success",
            "file_path": file_path,
            "processed": is_processed,
            "session": session_info
        }
        
    except Exception as e:
        logger.error(f"파일 처리 상태 확인 실패: {e}")
        return {
            "status": "error",
            "message": f"파일 처리 상태 확인 실패: {str(e)}",
            "file_path": file_path,
            "processed": False
        }


@router.get("/processing-summary-enhanced")
async def get_processing_summary_enhanced(supabase_mgr=Depends(get_supabase_manager_dep)):
    """향상된 전체 처리 상태 요약 (디렉토리별 포함)"""
    # Supabase가 없는 경우 기본 요약 반환
    if not supabase_mgr:
        return {
            "status": "success",
            "summary": {
                "total_files": 0,
                "processed_files": 0,
                "pending_files": 0,
                "processing_rate": 0.0,
                "directories": {}
            },
            "message": "Supabase가 설정되지 않아 기본 요약만 제공됩니다."
        }
    
    try:
        # 전체 파일 목록 조회
        audio_files_response = await get_audio_files()
        all_files = audio_files_response.get("files", [])
        
        # 전체 통계
        total_files = len(all_files)
        processed_count = 0
        directories = {}
        
        # 파일별 처리 상태 확인 및 디렉토리별 통계
        for file_info in all_files:
            file_path = file_info["path"]
            folder = file_info.get("folder", "direct")
            
            # 디렉토리별 통계 초기화
            if folder not in directories:
                directories[folder] = {
                    "total_files": 0,
                    "processed_files": 0,
                    "pending_files": 0,
                    "processing_rate": 0.0
                }
            
            directories[folder]["total_files"] += 1
            
            # 처리 상태 확인
            is_processed = supabase_mgr.check_file_processed(file_path)
            if is_processed:
                processed_count += 1
                directories[folder]["processed_files"] += 1
            else:
                directories[folder]["pending_files"] += 1
        
        # 전체 처리율 계산
        processing_rate = (processed_count / total_files * 100) if total_files > 0 else 0.0
        
        # 디렉토리별 처리율 계산
        for folder, stats in directories.items():
            if stats["total_files"] > 0:
                stats["processing_rate"] = round(stats["processed_files"] / stats["total_files"] * 100, 2)
        
        summary = {
            "total_files": total_files,
            "processed_files": processed_count,
            "pending_files": total_files - processed_count,
            "processing_rate": round(processing_rate, 2),
            "directories": directories
        }
        
        return {
            "status": "success",
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"향상된 처리 요약 조회 실패: {e}")
        return {
            "status": "error",
            "message": f"향상된 처리 요약 조회 실패: {str(e)}",
            "summary": {}
        }


@router.get("/environment-status")
async def get_environment_status():
    """환경변수 설정 상태 확인"""
    env_status = {}
    
    # 디버깅: 환경변수 로드 상태 확인
    logger.info("환경변수 상태 확인 시작")
    
    # OpenAI API Key 확인
    openai_key = os.getenv('OPENAI_API_KEY')
    logger.info(f"OPENAI_API_KEY 로드됨: {bool(openai_key)}")
    env_status['openai_api_key'] = {
        'configured': bool(openai_key),
        'length': len(openai_key) if openai_key else 0,
        'preview': f"{openai_key[:8]}..." if openai_key and len(openai_key) > 8 else "Not set"
    }
    
    # Supabase 설정 확인
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    logger.info(f"SUPABASE_URL 로드됨: {bool(supabase_url)}")
    logger.info(f"SUPABASE_ANON_KEY 로드됨: {bool(supabase_key)}")
    env_status['supabase'] = {
        'url_configured': bool(supabase_url),
        'key_configured': bool(supabase_key),
        'url_preview': f"{supabase_url[:30]}..." if supabase_url and len(supabase_url) > 30 else "Not set"
    }
    
    # Whisper 모델 경로 확인
    whisper_cache_paths = [
        os.path.expanduser("~/.cache/whisper"),
        os.path.join(os.getenv('LOCALAPPDATA', ''), 'whisper')
    ]
    
    env_status['whisper_cache'] = {}
    for path in whisper_cache_paths:
        if os.path.exists(path):
            env_status['whisper_cache'][path] = {
                'exists': True,
                'size_mb': round(sum(os.path.getsize(os.path.join(dirpath, filename))
                                   for dirpath, dirnames, filenames in os.walk(path)
                                   for filename in filenames) / (1024 * 1024), 2)
            }
        else:
            env_status['whisper_cache'][path] = {'exists': False}
    
    # HuggingFace Token 확인
    hf_token = os.getenv('HUGGINGFACE_HUB_TOKEN')
    logger.info(f"HUGGINGFACE_HUB_TOKEN 로드됨: {bool(hf_token)}")
    
    # 프론트엔드가 기대하는 형식으로 변환
    environment_variables = {
        'OPENAI_API_KEY': bool(openai_key),
        'SUPABASE_URL': bool(supabase_url),
        'SUPABASE_ANON_KEY': bool(supabase_key),
        'HUGGINGFACE_HUB_TOKEN': bool(hf_token)
    }
    
    logger.info(f"환경변수 상태: {environment_variables}")
    
    return {
        "status": "success",
        "environment_variables": environment_variables,
        "environment": env_status,  # 기존 상세 정보도 유지
        "timestamp": datetime.now().isoformat()
    }


@router.get("/model-status")
async def get_model_status():
    """모델 로딩 상태 확인"""
    try:
        model_status = {
            "whisper_base_loaded": whisper_model is not None,
            "cached_models": list(cached_whisper_models.keys()),
            "total_cached_models": len(cached_whisper_models),
            "model_details": {}
        }
        
        # 각 캐시된 모델의 상세 정보
        for model_name, model in cached_whisper_models.items():
            try:
                model_status["model_details"][model_name] = {
                    "loaded": True,
                    "type": str(type(model)),
                    "device": getattr(model, 'device', 'unknown')
                }
            except Exception as e:
                model_status["model_details"][model_name] = {
                    "loaded": False,
                    "error": str(e)
                }
        
        return {
            "status": "success",
            "model_status": model_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"모델 상태 확인 실패: {e}")
        return {
            "status": "error",
            "message": f"모델 상태 확인 실패: {str(e)}",
            "model_status": {}
        }


@router.post("/clear-whisper-cache")
async def clear_whisper_cache():
    """손상된 Whisper 모델 캐시를 정리합니다"""
    try:
        clear_whisper_file_cache()
        return {
            "status": "success",
            "message": "Whisper 캐시가 정리되었습니다",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Whisper 캐시 정리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Whisper 캐시 정리 실패: {str(e)}")


@router.post("/reload-base-model")
async def reload_base_model():
    """기본 Whisper 모델을 다시 로딩합니다"""
    global whisper_model
    
    try:
        logger.info("기본 Whisper 모델 재로딩 시작...")
        
        # 기존 모델 캐시 정리
        clear_model_cache()
        
        # 새 모델 로딩
        import whisper
        whisper_model = whisper.load_model("base")
        cached_whisper_models["base"] = whisper_model
        
        logger.info("기본 Whisper 모델 재로딩 완료")
        
        return {
            "status": "success",
            "message": "기본 Whisper 모델이 재로딩되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"기본 모델 재로딩 실패: {e}")
        raise HTTPException(status_code=500, detail=f"기본 모델 재로딩 실패: {str(e)}")


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(..., description="업로드할 음성 파일"),
    target_date: Optional[str] = None
):
    """음성 파일을 특정 날짜 폴더에 업로드"""
    try:
        # 파일 확장자 검증
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in SUPPORTED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(SUPPORTED_AUDIO_EXTENSIONS)}"
            )
        
        # 대상 날짜 설정 (기본값: 오늘)
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        # 대상 폴더 경로 생성
        target_folder = os.path.join(AUDIO_DIRECTORY, target_date)
        
        # 폴더가 없으면 생성
        if not os.path.exists(target_folder):
            os.makedirs(target_folder, exist_ok=True)
            logger.info(f"폴더 생성: {target_folder}")
        
        # 파일 저장 경로
        file_path = os.path.join(target_folder, file.filename)
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"파일 업로드 완료: {file_path}")
        
        return {
            "status": "success",
            "message": f"파일이 성공적으로 업로드되었습니다: {file.filename}",
            "file_path": file_path,
            "target_date": target_date,
            "file_size": os.path.getsize(file_path),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")
