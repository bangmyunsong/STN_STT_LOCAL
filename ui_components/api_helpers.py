"""
API 관련 헬퍼 함수들
"""

import streamlit as st
import requests
from typing import Optional


# API 서버 설정
API_BASE_URL = "http://localhost:8000"


# 캐시된 헬퍼 함수들 (성능 최적화)
@st.cache_data(ttl=10)  # 10초 캐시 - API 상태는 자주 체크
def check_api_connection():
    """API 서버 연결 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except:
        return False, None


@st.cache_data(ttl=60)  # 1분 캐시 - 통계는 자주 변하지 않음
def get_statistics():
    """시스템 통계 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/statistics", timeout=10)
        if response.status_code == 200:
            return response.json().get('statistics', {})
        return {}
    except:
        return {}


@st.cache_data(ttl=5)  # 5초 캐시로 단축 - 세션 목록
def get_stt_sessions(limit=50, offset=0):
    """STT 세션 목록 조회"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/sessions", 
            params={"limit": limit, "offset": offset},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('sessions', [])
        return []
    except:
        return []


@st.cache_data(ttl=60)  # 1분 캐시 - ERP 추출 결과
def get_erp_extractions(limit=50, offset=0):
    """ERP 추출 결과 목록 조회"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/extractions", 
            params={"limit": limit, "offset": offset},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('extractions', [])
        return []
    except:
        return []


@st.cache_data(ttl=60)  # 1분 캐시 - 등록 로그
def get_erp_register_logs(limit=50, offset=0):
    """ERP 등록 로그 목록 조회"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/register-logs", 
            params={"limit": limit, "offset": offset},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('register_logs', [])
        return []
    except:
        return []


@st.cache_data(ttl=120)  # 2분 캐시 - 세션 상세 정보
def get_session_detail(session_id):
    """특정 세션 상세 정보 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


@st.cache_data(ttl=30)  # 30초 캐시 - 배치 ERP 상태 조회
def get_batch_erp_status(session_ids):
    """여러 세션의 ERP 상태를 배치로 조회 (N+1 문제 해결)"""
    try:
        # 모든 추출 결과와 등록 로그를 한 번에 가져오기
        extractions = get_erp_extractions(limit=200)
        register_logs = get_erp_register_logs(limit=200)
        
        # 세션별 상태 매핑 생성
        status_map = {}
        
        for session_id in session_ids:
            # 해당 세션의 추출 결과 찾기
            session_extraction = next((e for e in extractions if e.get('session_id') == session_id), None)
            
            if not session_extraction:
                status_map[session_id] = {'extracted': False, 'registered': False, 'extraction_id': None}
                continue
            
            # 등록 상태 확인
            extraction_id = session_extraction.get('id')
            is_registered = any(log.get('extraction_id') == extraction_id and 
                              log.get('status') == 'success' for log in register_logs)
            
            status_map[session_id] = {
                'extracted': True, 
                'registered': is_registered,
                'extraction_id': extraction_id
            }
        
        return status_map
    except:
        # 오류 시 기본값 반환
        return {session_id: {'extracted': False, 'registered': False, 'extraction_id': None} 
                for session_id in session_ids}


# 기존 함수 유지 (호환성 위해)
def get_erp_status_for_session(session_id):
    """세션별 ERP 추출 및 등록 상태 확인 (단일 세션용 - 호환성 유지)"""
    batch_result = get_batch_erp_status([session_id])
    return batch_result.get(session_id, {'extracted': False, 'registered': False, 'extraction_id': None})


@st.cache_data(ttl=30)  # 30초 캐시 - 음성 파일 목록
def get_audio_files():
    """src_record 디렉토리의 음성 파일 목록 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/audio-files", timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None
    except:
        return False, None


@st.cache_data(ttl=60)  # 1분 캐시 - 디렉토리별 요약
def get_directory_processing_summary(folder=None):
    """디렉토리별 처리 현황 요약 조회"""
    try:
        params = {}
        if folder and folder != "전체 폴더":
            params['folder'] = folder
            
        response = requests.get(f"{API_BASE_URL}/api/directory-summary", params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get('summary', [])
        return []
    except:
        return []


@st.cache_data(ttl=60)  # 1분 캐시 - 파일 처리 상태
def get_file_processing_status(directory=None, limit=200):
    """파일 처리 상태 조회 (디렉토리별)"""
    try:
        params = {"limit": limit}
        if directory:
            params["directory"] = directory
        
        response = requests.get(
            f"{API_BASE_URL}/api/file-processing-status", 
            params=params,
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('files', [])
        return []
    except:
        return []


@st.cache_data(ttl=30)  # 30초 캐시 - 특정 파일 상태
def check_file_processed(file_path):
    """특정 파일의 처리 여부 확인"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/check-file-processed",
            params={"file_path": file_path},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return {'processed': False, 'status': '미처리', 'progress': 0}
    except:
        return {'processed': False, 'status': '오류', 'progress': 0}


# 캐시되지 않는 함수들 (실시간 처리 필요)
def register_erp_sample(erp_data, extraction_id=None):
    """ERP 샘플 등록 (캐시 안함 - 실시간 처리 필요)"""
    try:
        # extraction_id를 쿼리 파라미터로 전송
        params = {}
        if extraction_id:
            params['extraction_id'] = extraction_id
        
        # 디버깅: 전송할 데이터 로깅
        print(f"[DEBUG] ERP 등록 요청")
        print(f"[DEBUG] 전송 URL: {API_BASE_URL}/api/erp-sample-register")
        print(f"[DEBUG] 쿼리 파라미터: {params}")
        print(f"[DEBUG] 전송 데이터:")
        for key, value in erp_data.items():
            print(f"[DEBUG]   {key}: '{value}' (타입: {type(value).__name__})")
        
        response = requests.post(
            f"{API_BASE_URL}/api/erp-sample-register",
            json=erp_data,  # ERP 데이터만 JSON body로 전송
            params=params,   # extraction_id는 쿼리 파라미터로 전송
            timeout=10
        )
        
        # 디버깅: 응답 정보 로깅
        print(f"[DEBUG] 응답 상태 코드: {response.status_code}")
        print(f"[DEBUG] 응답 헤더: {dict(response.headers)}")
        print(f"[DEBUG] 응답 내용: {response.text}")
        
        # 성공 시 관련 캐시 무효화
        if response.status_code == 200:
            get_erp_register_logs.clear()
            get_batch_erp_status.clear()
        
        return response.status_code == 200, response.json() if response.status_code == 200 else response.text
    except Exception as e:
        print(f"[DEBUG] 예외 발생: {e}")
        return False, str(e)


def process_audio_file_from_directory(filename, model_name="base", extract_erp=True, save_to_db=True):
    """디렉토리의 음성 파일로 STT 처리 (캐시 안함 - 실시간 처리 필요)"""
    try:
        data = {
            "filename": filename,
            "model_name": model_name,
            "extract_erp": extract_erp,
            "save_to_db": save_to_db
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/stt-process-file",
            params=data,
            timeout=600  # STT 처리 시간 고려 (10분) - VAD 필터 옵션 추가로 인한 시간 증가
        )
        
        # 성공 시 관련 캐시 무효화
        if response.status_code == 200:
            get_stt_sessions.clear()
            get_erp_extractions.clear()
            get_statistics.clear()
            get_batch_erp_status.clear()
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json() if response.status_code != 500 else {"detail": "서버 오류"}
    except Exception as e:
        return False, {"detail": str(e)} 


def update_directory_view():
    """디렉토리별 처리 현황 뷰를 업데이트합니다"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/update-directory-view", timeout=30)
        if response.status_code == 200:
            return True, response.json().get('message', '뷰가 성공적으로 업데이트되었습니다')
        else:
            return False, f"API 호출 실패: {response.status_code}"
    except Exception as e:
        return False, f"네트워크 오류: {str(e)}" 