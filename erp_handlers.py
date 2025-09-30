"""
ERP 추출 관련 핸들러
ERP 데이터 추출, 등록 및 관련 기능
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, List
import uuid
import json
import os
import openai
from datetime import datetime
import logging

from models import ERPData, ERPRegisterResponse, ERPExtractionRequest
from domain_manager import domain_manager
from postprocessor import postprocess_to_codes, convert_to_legacy_erp_format
from payload_schema import validate_payload, get_validation_stats
from gpt_extractor import ERPExtractor
from supabase_client import get_supabase_manager

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api", tags=["ERP"])

# 전역 변수들 (의존성 주입용)
erp_extractor = None


def get_erp_extractor():
    """ERP Extractor 의존성 (지연 초기화)"""
    global erp_extractor
    if erp_extractor is None:
        try:
            logger.info("ERP Extractor 지연 초기화 중...")
            erp_extractor = ERPExtractor()
            logger.info("✅ ERP Extractor 초기화 완료")
        except Exception as e:
            logger.error(f"❌ ERP Extractor 초기화 실패: {e}")
            return None
    return erp_extractor


def _build_enhanced_user_prompt(transcript_text: str, domain_data: dict) -> str:
    """개선된 사용자 프롬프트 구성"""
    equipment_list = domain_data.get('equipment', [])
    error_list = domain_data.get('errors', [])
    request_list = domain_data.get('requests', [])
    
    prompt = f"""
다음 고객센터 통화 내용에서 ERP 항목을 추출해주세요:

=== 통화 내용 ===
{transcript_text}

=== 추출할 항목 ===
1. 장비명: {', '.join(equipment_list[:10])} 등
2. 장애유형: {', '.join(error_list[:10])} 등  
3. 요청유형: {', '.join(request_list[:10])} 등
4. 위치: 지역명, 건물명, 사무실명 등

=== 응답 형식 ===
JSON 형식으로 응답해주세요:
{{
    "장비명": "추출된 장비명 또는 null",
    "장애유형": "추출된 장애유형 또는 null", 
    "요청유형": "추출된 요청유형 또는 null",
    "위치": "추출된 위치 정보 또는 null"
}}

통화 내용에서 명확하게 언급된 정보만 추출하고, 추측하지 마세요.
"""
    return prompt


@router.post("/erp-sample-register", response_model=ERPRegisterResponse)
async def register_erp_sample(
    erp_data: ERPData, 
    extraction_id: Optional[int] = None,
    supabase_mgr=Depends(get_supabase_manager)
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


@router.post("/extract-erp")
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


@router.get("/domain-stats")
async def get_domain_stats():
    """도메인 데이터 통계 조회"""
    try:
        return domain_manager.get_domain_stats()
    except Exception as e:
        logger.error(f"도메인 통계 조회 실패: {e}")
        return {"available": False, "error": str(e)}


@router.post("/reload-domain")
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


@router.post("/extract-erp-enhanced")
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


@router.post("/sessions/{session_id}/extract-erp")
async def extract_erp_for_session(
    session_id: int,
    erp_extractor=Depends(get_erp_extractor),
    supabase_mgr=Depends(get_supabase_manager)
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
