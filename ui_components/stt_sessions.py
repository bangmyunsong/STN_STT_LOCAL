"""
STT 세션 관리 페이지 컴포넌트
"""

import streamlit as st
import requests
from .api_helpers import (
    check_api_connection, get_stt_sessions, get_erp_extractions,
    get_batch_erp_status, get_erp_status_for_session, API_BASE_URL,
    get_erp_register_logs
)
from .utils import render_erp_status_badge, show_session_detail, safe_get_string


def show_stt_sessions():
    """STT 세션 관리 페이지"""
    st.header("📊 STT 세션 관리")
    
    if not check_api_connection()[0]:
        st.error("API 서버에 연결할 수 없습니다.")
        return
    
    # 새로고침 버튼 추가
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.write("")  # 공백
    with col_header2:
        if st.button("🔄 새로고침", key="refresh_sessions"):
            st.cache_data.clear()  # 캐시 클리어
            st.rerun()  # 페이지 새로고침
    
    # 세션 목록
    sessions = get_stt_sessions(limit=100)
    
    if not sessions:
        st.info("아직 처리된 세션이 없습니다.")
        return
    
    st.subheader(f"📋 총 {len(sessions)}개의 세션")
    
    # 필터링 옵션 (개선된 버전)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "STT 상태 필터:",
            ["전체", "completed", "processing", "failed"]
        )
    
    with col2:
        model_filter = st.selectbox(
            "모델 필터:",
            ["전체"] + list(set([s.get('model_name', 'unknown') for s in sessions]))
        )
    
    with col3:
        # 대시보드에서 전달된 필터 상태 확인
        default_erp_filter = "전체"
        if hasattr(st.session_state, 'erp_filter'):
            default_erp_filter = st.session_state.erp_filter
            del st.session_state.erp_filter  # 한 번 사용 후 삭제
        
        erp_filter = st.selectbox(
            "ERP 상태 필터:",
            ["전체", "완료", "추출됨", "미처리"],
            index=["전체", "완료", "추출됨", "미처리"].index(default_erp_filter) if default_erp_filter in ["전체", "완료", "추출됨", "미처리"] else 0
        )
    
    # 필터링 적용 (개선된 버전)
    filtered_sessions = sessions
    if status_filter != "전체":
        filtered_sessions = [s for s in filtered_sessions if s.get('status') == status_filter]
    if model_filter != "전체":
        filtered_sessions = [s for s in filtered_sessions if s.get('model_name') == model_filter]
    
    # ERP 상태 필터링 (배치 조회로 성능 최적화)
    if erp_filter != "전체":
        # 필터된 세션들의 ERP 상태를 한 번에 조회
        session_ids = [s.get('id') for s in filtered_sessions]
        batch_erp_status = get_batch_erp_status(session_ids)
        
        def filter_by_erp_status(session):
            erp_status = batch_erp_status.get(session.get('id'), {'extracted': False, 'registered': False, 'extraction_id': None})
            if erp_filter == "완료":
                return erp_status['registered']
            elif erp_filter == "추출됨":
                return erp_status['extracted'] and not erp_status['registered']
            elif erp_filter == "미처리":
                return not erp_status['extracted']
            return True
        
        filtered_sessions = [s for s in filtered_sessions if filter_by_erp_status(s)]
    
    # 세션 목록 표시 (배치 조회로 성능 최적화)
    # 표시할 세션들의 ERP 상태를 한 번에 조회
    if filtered_sessions:
        display_session_ids = [s.get('id') for s in filtered_sessions]
        display_batch_erp_status = get_batch_erp_status(display_session_ids)
    
    for session in filtered_sessions:
        session_id = session.get('id', 'N/A')
        erp_status = display_batch_erp_status.get(session_id, {'extracted': False, 'registered': False, 'extraction_id': None}) if filtered_sessions else get_erp_status_for_session(session_id)
        status_badge = render_erp_status_badge(erp_status)
        
        with st.expander(f"🎙️ 세션 {session_id} - {session.get('file_name', 'N/A')} | {status_badge}"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**파일 ID:** {session.get('file_id', 'N/A')}")
                st.write(f"**모델:** {session.get('model_name', 'N/A')}")
                st.write(f"**언어:** {session.get('language', 'auto')}")
                st.write(f"**STT 상태:** {session.get('status', 'N/A')}")
            
            with col2:
                st.write(f"**처리 시간:** {session.get('processing_time', 'N/A')}초")
                st.write(f"**생성일:** {session.get('created_at', 'N/A')}")
                st.write(f"**ERP 상태:** {status_badge}")
            
            with col3:
                # 액션 버튼들
                if st.button(f"상세 보기", key=f"detail_{session_id}"):
                    show_session_detail(session_id, lambda sid: get_session_detail(sid))
                
                # ERP 액션 버튼
                if not erp_status['extracted']:
                    if st.button("🔄 ERP 추출", key=f"extract_{session_id}", type="secondary"):
                        with st.spinner(f"세션 {session_id}의 ERP 데이터를 추출하는 중..."):
                            try:
                                # 새로운 ERP 추출 API 호출
                                response = requests.post(
                                    f"{API_BASE_URL}/api/sessions/{session_id}/extract-erp",
                                    timeout=30
                                )
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    st.success(f"✅ ERP 추출 완료!")
                                    st.info(f"추출 ID: {result.get('extraction_id', 'N/A')}")
                                    
                                    # 관련 캐시 무효화
                                    get_erp_extractions.clear()
                                    get_batch_erp_status.clear()
                                    # get_statistics.clear()  # api_helpers에서 import 필요
                                    
                                    # 페이지 새로고침
                                    st.rerun()
                                else:
                                    error_detail = response.json().get('detail', '알 수 없는 오류') if response.status_code != 500 else "서버 오류"
                                    st.error(f"❌ ERP 추출 실패: {error_detail}")
                                    
                            except requests.exceptions.Timeout:
                                st.error("❌ ERP 추출 시간 초과 (30초)")
                            except requests.exceptions.RequestException as e:
                                st.error(f"❌ 네트워크 오류: {str(e)}")
                            except Exception as e:
                                st.error(f"❌ ERP 추출 중 오류 발생: {str(e)}")
                elif erp_status['extracted'] and not erp_status['registered']:
                    if st.button("📤 ERP 등록", key=f"register_{session_id}", type="primary"):
                        # ERP 등록 로직 (기존 코드 재사용)
                        extractions = get_erp_extractions()
                        if extractions:
                            target_extraction = next((e for e in extractions if e.get('id') == erp_status['extraction_id']), None)
                            if target_extraction:
                                erp_data = {
                                    "AS 및 지원": safe_get_string(target_extraction, 'as_지원'),
                                    "요청기관": safe_get_string(target_extraction, '요청기관'),
                                    "작업국소": safe_get_string(target_extraction, '작업국소'),
                                    "요청일": safe_get_string(target_extraction, '요청일'),
                                    "요청시간": safe_get_string(target_extraction, '요청시간'),
                                    "요청자": safe_get_string(target_extraction, '요청자'),
                                    "지원인원수": safe_get_string(target_extraction, '지원인원수'),
                                    "지원요원": safe_get_string(target_extraction, '지원요원'),
                                    "장비명": safe_get_string(target_extraction, '장비명'),
                                    "기종명": safe_get_string(target_extraction, '기종명'),
                                    "A/S기간만료여부": safe_get_string(target_extraction, 'as_기간만료여부'),
                                    "시스템명(고객사명)": safe_get_string(target_extraction, '시스템명'),
                                    "요청 사항": safe_get_string(target_extraction, '요청사항')
                                }
                                
                                from .api_helpers import register_erp_sample
                                success, result = register_erp_sample(erp_data, erp_status['extraction_id'])
                                if success:
                                    st.success(f"ERP 등록 성공: {result.get('erp_id', 'N/A')}")
                                    st.rerun()
                                else:
                                    st.error("ERP 등록 실패")
                else:
                    st.success("✅ 완료")


# 세션 상세 정보를 위한 get_session_detail import
from .api_helpers import get_session_detail 