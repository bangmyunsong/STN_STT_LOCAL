"""
STT 처리 관련 핸들러
음성 파일 STT 처리 및 관련 기능
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import Optional, Dict, List
import uuid
import os
import tempfile
import whisper
from datetime import datetime
import logging

from models import STTResponse, ERPData
from domain_manager import domain_manager
from postprocessor import comprehensive_postprocess
from gpt_extractor import ERPExtractor
from supabase_client import get_supabase_manager

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api", tags=["STT"])

# 전역 변수
whisper_model = None
erp_extractor = None
cached_whisper_models = {}
AUDIO_DIRECTORY = "src_record"
SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac']

def initialize_models():
    """모델들을 초기화하는 함수 (안전한 단계별 초기화)"""
    global whisper_model, erp_extractor
    
    logger.info("🚀 STT 모델 초기화 시작...")
    
    # 1. Whisper 모델 초기화
    logger.info("1️⃣ Whisper 모델들 로딩 중... (인터넷 연결 필요)")
    try:
        # 기본 모델들 로딩
        model_names = ["base", "small", "medium", "large"]
        for model_name in model_names:
            logger.info(f"   - {model_name} 모델 로딩 중...")
            try:
                model = whisper.load_model(model_name)
                cached_whisper_models[model_name] = model
                logger.info(f"   ✅ {model_name} 모델 로딩 완료")
            except Exception as e:
                logger.error(f"   ❌ {model_name} 모델 로딩 실패: {e}")
                return False
        
        # 기본 모델 설정
        whisper_model = cached_whisper_models.get("base")
        logger.info(f"✅ Whisper 모델 초기화 완료 - 기본 모델: {list(cached_whisper_models.keys())}")
        
    except Exception as e:
        logger.error(f"❌ Whisper 모델 초기화 실패: {e}")
        return False
    
    # 2. ERP Extractor 초기화
    logger.info("2️⃣ ERP Extractor 초기화 중...")
    try:
        erp_extractor = ERPExtractor()
        logger.info("✅ ERP Extractor 초기화 완료")
    except Exception as e:
        logger.error(f"❌ ERP Extractor 초기화 실패: {e}")
        return False
    
    logger.info("🎉 STT 모델 초기화 완료!")
    return True

def get_whisper_model(model_name: str = "small"):
    """요청된 Whisper 모델을 반환"""
    if model_name in cached_whisper_models:
        return cached_whisper_models[model_name]
    elif cached_whisper_models:
        # 요청된 모델이 없으면 기본 모델 반환
        default_model = list(cached_whisper_models.values())[0]
        logger.warning(f"요청된 모델 '{model_name}'이 없습니다. 기본 모델을 사용합니다.")
        return default_model
    else:
        raise HTTPException(status_code=500, detail="Whisper 모델이 로드되지 않았습니다.")

def clear_model_cache():
    """모델 캐시를 정리합니다"""
    global whisper_model, cached_whisper_models
    logger.info("모델 캐시 정리 중...")
    cached_whisper_models.clear()
    whisper_model = None
    logger.info("모델 캐시 정리 완료")

def clear_whisper_file_cache():
    """Whisper 파일 캐시를 정리합니다"""
    import shutil
    import os
    
    # Whisper 캐시 디렉토리 경로들
    cache_paths = [
        os.path.expanduser("~/.cache/whisper"),
        os.path.expanduser("~/AppData/Local/whisper"),
        os.path.expanduser("~/AppData/Roaming/whisper")
    ]
    
    logger.info("Whisper 파일 캐시 정리 중...")
    
    for cache_path in cache_paths:
        if os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path)
                logger.info(f"Whisper 캐시 디렉토리 삭제: {cache_path}")
            except Exception as e:
                logger.warning(f"Whisper 캐시 디렉토리 삭제 실패: {cache_path}, 오류: {e}")
    
    logger.info("Whisper 파일 캐시 정리 완료")

def _create_simple_summary(transcript: str, erp_data: dict) -> str:
    """
    패턴 매칭 기반 요약 생성 (고객센터 통화 특화)
    """
    try:
        import re
        
        # ERP 데이터에서 주요 정보 추출
        as_support = erp_data.get("AS 및 지원", "정보 없음")
        request_org = erp_data.get("요청기관", "정보 없음")
        request_type = erp_data.get("요청유형", "정보 없음")
        location = erp_data.get("작업국소", "정보 없음")
        
        # 1. 핵심 문장 추출 (패턴 매칭)
        key_sentences = _extract_key_sentences(transcript)
        
        # 2. 요청 유형 분석
        request_analysis = _analyze_request_type(transcript)
        
        # 3. 문제 상황 추출
        problem_info = _extract_problem_info(transcript)
        
        # 4. 시간/장소 정보 추출
        time_location = _extract_time_location(transcript)
        
        # 5. 요약 생성
        summary = f"""[요약] {request_org} {as_support} 요청
[유형] {request_type} | {request_analysis}
[위치] {location} | {time_location}
[문제] {problem_info}
[핵심] {key_sentences}"""
        
        logger.info("패턴 매칭 기반 요약 생성 완료")
        return summary
        
    except Exception as e:
        logger.warning(f"패턴 매칭 요약 생성 실패: {e}")
        return f"[요약] 요청 내용: {transcript[:100]}..."

def _extract_key_sentences(transcript: str) -> str:
    """핵심 문장 추출 (패턴 매칭)"""
    import re
    
    # 고객 요청 관련 패턴
    request_patterns = [
        r'[가-힣]*[가-힣]*(?:문제|장애|오류|안됨|안돼|안되|고장|이상)[가-힣]*',
        r'[가-힣]*[가-힣]*(?:요청|부탁|해주세요|도와주세요|지원)[가-힣]*',
        r'[가-힣]*[가-힣]*(?:급함|급해|빨리|오늘|내일)[가-힣]*'
    ]
    
    sentences = transcript.split('.')
    key_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:  # 너무 짧은 문장 제외
            continue
            
        for pattern in request_patterns:
            if re.search(pattern, sentence):
                key_sentences.append(sentence)
                break
    
    # 최대 3개 문장만 선택
    return ' | '.join(key_sentences[:3]) if key_sentences else "핵심 문장 없음"

def _analyze_request_type(transcript: str) -> str:
    """요청 유형 분석"""
    import re
    
    # 장애 관련 패턴
    if re.search(r'(?:장애|오류|고장|이상|안됨|안돼)', transcript):
        return "장애신고"
    
    # 기술지원 관련 패턴
    if re.search(r'(?:지원|도움|해결|수리|점검)', transcript):
        return "기술지원"
    
    # 문의 관련 패턴
    if re.search(r'(?:문의|질문|확인|알려주세요)', transcript):
        return "문의사항"
    
    # 긴급 관련 패턴
    if re.search(r'(?:급함|급해|빨리|즉시)', transcript):
        return "긴급요청"
    
    return "일반요청"

def _extract_problem_info(transcript: str) -> str:
    """문제 상황 정보 추출"""
    import re
    
    # 장비/시스템 관련 패턴
    equipment_patterns = [
        r'(?:MSPP|1646SMC|공유기|라우터|스위치|서버)',
        r'(?:장비|시스템|네트워크|회선|인터넷)'
    ]
    
    # 문제 상황 패턴
    problem_patterns = [
        r'(?:꺼져|꺼짐|안됨|안돼|고장|이상)',
        r'(?:느려|느림|끊어|끊김|불안정)'
    ]
    
    problems = []
    
    for eq_pattern in equipment_patterns:
        for prob_pattern in problem_patterns:
            pattern = f'{eq_pattern}.*?{prob_pattern}|{prob_pattern}.*?{eq_pattern}'
            matches = re.findall(pattern, transcript)
            problems.extend(matches)
    
    return ' | '.join(problems[:2]) if problems else "문제 정보 없음"

def _extract_time_location(transcript: str) -> str:
    """시간/장소 정보 추출"""
    import re
    
    # 시간 관련 패턴
    time_patterns = [
        r'(?:오늘|내일|모레)',
        r'(?:오전|오후|저녁)',
        r'(?:[0-9]{1,2}시|[0-9]{1,2}:00)'
    ]
    
    # 장소 관련 패턴
    location_patterns = [
        r'(?:[0-9]+층|[0-9]+F)',
        r'(?:서울|부산|대전|대구|광주|인천)',
        r'(?:사무실|회의실|서버실|기계실)'
    ]
    
    time_info = []
    location_info = []
    
    for pattern in time_patterns:
        matches = re.findall(pattern, transcript)
        time_info.extend(matches)
    
    for pattern in location_patterns:
        matches = re.findall(pattern, transcript)
        location_info.extend(matches)
    
    time_str = ' | '.join(time_info[:2]) if time_info else ""
    location_str = ' | '.join(location_info[:2]) if location_info else ""
    
    return f"{time_str} {location_str}".strip()

def get_erp_extractor():
    """ERP Extractor를 반환"""
    global erp_extractor
    if erp_extractor is None:
        logger.warning("ERP Extractor가 초기화되지 않았습니다.")
    return erp_extractor

@router.post("/stt-process", response_model=STTResponse)
async def process_audio_file(
    file: UploadFile = File(..., description="업로드할 음성 파일"),
    model_name: str = "base",
    language: Optional[str] = None,
    enable_diarization: bool = True,
    extract_erp: bool = True,
    save_to_db: bool = True,
    whisper_model=Depends(get_whisper_model),
    erp_extractor=Depends(get_erp_extractor),
    supabase_mgr=Depends(get_supabase_manager)
):
    start_time = datetime.now()
    file_id = f"stt_{uuid.uuid4().hex[:8]}"
    if language == 'auto':
        language = None
    
    try:
        logger.info(f"STT 처리 시작 - File ID: {file_id}, 파일명: {file.filename}")
        logger.info(f"요청 옵션 - model_name={model_name}, language={language}, extract_erp={extract_erp}, save_to_db={save_to_db}, enable_diarization={enable_diarization}")
        
        # 파일 확장자 확인
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.flac']
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}")
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Whisper STT 처리
            logger.info(f"Whisper STT 처리 중 - 모델: {model_name}")
            
            # 모델 캐싱으로 성능 최적화
            current_model = get_whisper_model(model_name)
            
            # STT 실행
            result = current_model.transcribe(
                temp_file_path, 
                language=language,
                beam_size=1,
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
                processed_text = comprehensive_postprocess(original_text, domain_data)
                
                # 세그먼트 처리 로그 출력
                logger.info(f"세그먼트 {i+1}: 원본='{original_text}' → 후처리='{processed_text}'")
                
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
                    session = supabase_mgr.create_stt_session(
                        file_name=file.filename,
                        file_id=file_id,
                        model_name=model_name,
                        language=language
                    )
                    session_id = session['id']
                    supabase_mgr.update_stt_session(
                        session_id=session_id,
                        transcript=processed_text,
                        original_transcript=original_text,
                        segments=segments,
                        original_segments=original_segments,
                        processing_time=processing_time,
                        status="completed"
                    )
                    if erp_data:
                        erp_dict = erp_data.dict(by_alias=True)
                        
                        # 전사 요약 통합 (성능 최적화 - 간단한 요약)
                        try:
                            # 간단한 요약 생성 (GPT API 호출 없이)
                            simple_summary = _create_simple_summary(processed_text, erp_dict)
                            erp_dict["요청 사항"] = simple_summary
                            logger.info("간단한 요약 기반 요청사항 생성 완료")
                        except Exception as e:
                            logger.warning(f"요약 생성 실패: {e}")
                            # 실패 시 기본 메시지 설정
                            erp_dict["요청 사항"] = "요약 생성 실패"
                        
                        extraction = supabase_mgr.save_erp_extraction(
                            session_id=session_id,
                            erp_data=erp_dict
                        )
                        extraction_id = extraction['id']
                        logger.info(f"ERP 추출 결과 저장 완료 - 추출 ID: {extraction_id}")
                    if save_to_db and extraction_id:
                        try:
                            logger.info("ERP 시스템에 자동 등록 중...")
                            erp_id = f"auto{uuid.uuid4().hex[:8]}"
                            erp_response_data = {
                                "status": "success",
                                "erp_id": erp_id,
                                "message": "STT 처리 중 ERP 시스템에 자동 등록되었습니다"
                            }
                            supabase_mgr.save_erp_register_log(
                                extraction_id=extraction_id,
                                erp_id=erp_id,
                                status="success",
                                response_data=erp_response_data
                            )
                            logger.info(f"ERP 자동 등록 완료 - ERP ID: {erp_id}, 추출 ID: {extraction_id}")
                        except Exception as e:
                            logger.warning(f"ERP 자동 등록 실패 (계속 진행): {e}")
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
            
            response = STTResponse(
                status="success",
                transcript=processed_text,
                segments=segments,
                erp_data=erp_data,
                processing_time=processing_time,
                file_id=file_id,
                original_transcript=original_text,
                original_segments=original_segments
            )
            if session_id:
                response.session_id = session_id
            if extraction_id:
                response.extraction_id = extraction_id
            logger.info(f"STT 처리 완료 - File ID: {file_id}, 처리시간: {processing_time:.2f}초")
            return response
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT 처리 실패 - File ID: {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"STT 처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/stt-process-file", response_model=STTResponse)
async def process_audio_file_from_directory(
    filename: str,
    model_name: str = "base",
    language: Optional[str] = None,
    enable_diarization: bool = True,
    extract_erp: bool = True,
    save_to_db: bool = True,
    whisper_model=Depends(get_whisper_model),
    erp_extractor=Depends(get_erp_extractor),
    supabase_mgr=Depends(get_supabase_manager)
):
    start_time = datetime.now()
    file_id = f"stt_{uuid.uuid4().hex[:8]}"
    if language == 'auto':
        language = None
    
    try:
        logger.info(f"요청 옵션 - model_name={model_name}, language={language}, extract_erp={extract_erp}, save_to_db={save_to_db}, enable_diarization={enable_diarization}")
        file_path = os.path.join(AUDIO_DIRECTORY, filename)
        file_path = os.path.normpath(file_path)
        file_path = os.path.abspath(file_path)
        logger.info(f"파일 경로 확인 - 요청된 파일명: {filename}")
        logger.info(f"파일 경로 확인 - 구성된 경로: {file_path}")
        logger.info(f"파일 경로 확인 - 파일 존재 여부: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {filename} (경로: {file_path})")
        
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=400, detail=f"유효한 파일이 아닙니다: {filename} (경로: {file_path})")
        
        actual_filename = os.path.basename(filename)
        file_extension = os.path.splitext(actual_filename)[1].lower()
        if file_extension not in SUPPORTED_AUDIO_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(SUPPORTED_AUDIO_EXTENSIONS)}")
        
        logger.info(f"STT 처리 시작 - File ID: {file_id}, 파일경로: {file_path}")
        logger.info(f"Whisper STT 처리 중 - 모델: {model_name}")
        
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
                import time
                start_loading_time = time.time()
                current_model = whisper.load_model(model_name)
                loading_time = time.time() - start_loading_time
                logger.info(f"✅ 모델 '{model_name}' 로딩 완료 (소요시간: {loading_time:.2f}초)")
                cached_whisper_models[model_name] = current_model
            except Exception as model_error:
                logger.error(f"❌ 모델 '{model_name}' 로딩 실패: {model_error}")
                if model_name != "base" and whisper_model is not None:
                    logger.info("🔄 기본 'base' 모델로 폴백합니다...")
                    current_model = whisper_model
                    cached_whisper_models["base"] = whisper_model
                else:
                    raise HTTPException(status_code=500, detail=f"Whisper 모델 '{model_name}' 로딩에 실패했습니다: {str(model_error)}")
        
        # STT 실행
        logger.info(f"Whisper transcribe 시작 - 파일: {file_path}")
        logger.info(f"Whisper transcribe 시작 - 언어: {language}")
        try:
            result = current_model.transcribe(
                file_path, 
                language=language,
                beam_size=1,
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
            error_msg = str(transcribe_error)
            if "WinError 2" in error_msg or "CreateProcess" in error_msg:
                raise HTTPException(status_code=500, detail="FFmpeg가 설치되지 않았습니다. Whisper는 오디오 처리를 위해 FFmpeg가 필요합니다. FFmpeg를 설치한 후 다시 시도해주세요.")
            else:
                raise HTTPException(status_code=500, detail=f"음성 인식 처리 실패: {str(transcribe_error)}")
        
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
            processed_text = comprehensive_postprocess(original_text, domain_data)
            
            # 세그먼트 처리 로그 출력
            logger.info(f"세그먼트 {i+1}: 원본='{original_text}' → 후처리='{processed_text}'")
            
            original_segment = {
                "id": i,
                "text": original_text,
                "start": segment["start"],
                "end": segment["end"],
                "speaker": f"Speaker_{i % 2}"
            }
            original_segments.append(original_segment)
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
                session = supabase_mgr.create_stt_session(
                    file_name=filename,
                    file_id=file_id,
                    model_name=model_name,
                    language=language
                )
                session_id = session['id']
                supabase_mgr.update_stt_session(
                    session_id=session_id,
                    transcript=processed_text,
                    original_transcript=original_text,
                    segments=segments,
                    original_segments=original_segments,
                    processing_time=processing_time,
                    status="completed"
                )
                if erp_data:
                    erp_dict = erp_data.dict(by_alias=True)
                    
                    # 전사 요약 통합 (성능 최적화 - 간단한 요약)
                    try:
                        # 간단한 요약 생성 (GPT API 호출 없이)
                        simple_summary = _create_simple_summary(processed_text, erp_dict)
                        erp_dict["요청 사항"] = simple_summary
                        logger.info("간단한 요약 기반 요청사항 생성 완료")
                    except Exception as e:
                        logger.warning(f"요약 생성 실패: {e}")
                        # 실패 시 기본 메시지 설정
                        erp_dict["요청 사항"] = "요약 생성 실패"
                    
                    extraction = supabase_mgr.save_erp_extraction(
                        session_id=session_id,
                        erp_data=erp_dict
                    )
                    extraction_id = extraction['id']
                    logger.info(f"ERP 추출 결과 저장 완료 - 추출 ID: {extraction_id}")
                if save_to_db and extraction_id:
                    try:
                        logger.info("ERP 시스템에 자동 등록 중...")
                        erp_id = f"auto{uuid.uuid4().hex[:8]}"
                        erp_response_data = {
                            "status": "success",
                            "erp_id": erp_id,
                            "message": "STT 처리 중 ERP 시스템에 자동 등록되었습니다"
                        }
                        supabase_mgr.save_erp_register_log(
                            extraction_id=extraction_id,
                            erp_id=erp_id,
                            status="success",
                            response_data=erp_response_data
                        )
                        logger.info(f"ERP 자동 등록 완료 - ERP ID: {erp_id}, 추출 ID: {extraction_id}")
                    except Exception as e:
                        logger.warning(f"ERP 자동 등록 실패 (계속 진행): {e}")
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
        
        response = STTResponse(
            status="success",
            transcript=processed_text,
            segments=segments,
            erp_data=erp_data,
            processing_time=processing_time,
            file_id=file_id,
            original_transcript=original_text,
            original_segments=original_segments
        )
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

@router.get("/models")
async def get_available_models():
    """사용 가능한 Whisper 모델 목록 반환"""
    global cached_whisper_models
    
    available_models = list(cached_whisper_models.keys())
    
    return {
        "available_models": available_models,
        "default_model": "base",
        "model_info": {
            "base": "가장 빠른 모델, 정확도 낮음",
            "small": "균형잡힌 모델, 속도와 정확도 중간",
            "medium": "정확도 높음, 속도 느림",
            "large": "가장 정확한 모델, 속도 매우 느림"
        }
    }

@router.get("/health")
async def stt_health_check():
    """STT 서비스 상태 확인"""
    global whisper_model, erp_extractor, cached_whisper_models
    
    return {
        "status": "healthy",
        "whisper_model_loaded": whisper_model is not None,
        "erp_extractor_loaded": erp_extractor is not None,
        "cached_models": list(cached_whisper_models.keys()),
        "timestamp": datetime.now().isoformat()
    }