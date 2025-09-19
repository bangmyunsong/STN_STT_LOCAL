"""
대시보드 페이지 컴포넌트
"""

import streamlit as st
import pandas as pd
from .api_helpers import (
    check_api_connection, get_statistics, get_stt_sessions, 
    get_erp_extractions, get_batch_erp_status
)


def show_dashboard():
    """대시보드 페이지"""
    st.header("📈 시스템 대시보드")
    
    if not check_api_connection()[0]:
        st.error("API 서버에 연결할 수 없습니다. 서버를 시작해주세요.")
        return
    
    # 통계 데이터 가져오기
    stats = get_statistics()
    
    if not stats:
        st.warning("통계 데이터를 가져올 수 없습니다. Supabase 설정을 확인해주세요.")
        return
    
    # 메트릭 카드들 (개선된 버전)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📝 총 STT 세션",
            value=stats.get('total_stt_sessions', 0)
        )
    
    with col2:
        st.metric(
            label="🔍 ERP 추출 수",
            value=stats.get('total_erp_extractions', 0)
        )
    
    with col3:
        st.metric(
            label="✅ ERP 등록 수",
            value=stats.get('total_erp_registrations', 0)
        )
    
    with col4:
        st.metric(
            label="📅 최근 7일 세션",
            value=stats.get('recent_sessions_7days', 0)
        )
    
    # ERP 연동 상태 요약 추가
    st.markdown("---")
    st.subheader("🎯 ERP 연동 상태 현황")
    
    # ERP 연동 상태 계산 (배치 조회로 성능 최적화)
    sessions = get_stt_sessions(limit=100)  # 최근 100개 세션
    if sessions:
        total_sessions = len(sessions)
        extracted_count = 0
        registered_count = 0
        pending_extract = 0
        pending_register = 0
        
        # 모든 세션의 ERP 상태를 한 번에 조회 (N+1 문제 해결)
        with st.spinner(f"🔄 {total_sessions}개 세션의 ERP 상태를 조회하는 중..."):
            session_ids = [session.get('id') for session in sessions]
            batch_erp_status = get_batch_erp_status(session_ids)
        
        for session_id in session_ids:
            erp_status = batch_erp_status.get(session_id, {'extracted': False, 'registered': False, 'extraction_id': None})
            
            if erp_status['registered']:
                registered_count += 1
            elif erp_status['extracted']:
                extracted_count += 1
                pending_register += 1
            else:
                pending_extract += 1
        
        # 상태별 메트릭
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🟢 완료 (추출+등록)",
                value=registered_count,
                delta=f"{(registered_count/total_sessions*100):.1f}%" if total_sessions > 0 else "0%"
            )
        
        with col2:
            st.metric(
                label="🟡 추출됨 (등록필요)",
                value=pending_register,
                delta=f"{(pending_register/total_sessions*100):.1f}%" if total_sessions > 0 else "0%"
            )
        
        with col3:
            st.metric(
                label="🔴 미처리 (추출필요)",
                value=pending_extract,
                delta=f"{(pending_extract/total_sessions*100):.1f}%" if total_sessions > 0 else "0%"
            )
        
        with col4:
            completion_rate = (registered_count / total_sessions * 100) if total_sessions > 0 else 0
            st.metric(
                label="📊 완료율",
                value=f"{completion_rate:.1f}%",
                delta="목표: 95%"
            )
        
        # 액션 버튼들
        st.markdown("### 🚀 빠른 액션")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if pending_register > 0:
                if st.button(f"📤 등록 대기 중인 {pending_register}건 확인", key="goto_pending_register"):
                    st.session_state.page = "📊 STT 세션 관리"
                    st.session_state.erp_filter = "추출됨"
                    st.rerun()
        
        with col2:
            if pending_extract > 0:
                if st.button(f"🔄 추출 필요한 {pending_extract}건 확인", key="goto_pending_extract"):
                    st.session_state.page = "📊 STT 세션 관리"
                    st.session_state.erp_filter = "미처리"
                    st.rerun()
        
        with col3:
            if st.button("🎙️ 새로운 STT 처리", key="goto_stt_processing"):
                st.session_state.page = "🎙️ STT 처리"
                st.rerun()
        
        # 진행률 바
        if total_sessions > 0:
            progress_value = registered_count / total_sessions
            st.progress(progress_value)
            st.caption(f"전체 진행률: {progress_value*100:.1f}% ({registered_count}/{total_sessions})")
    else:
        st.info("아직 처리된 세션이 없습니다. STT 처리를 시작해보세요!")
    
    st.markdown("---")
    
    # 최근 세션들
    st.subheader("🕐 최근 STT 세션")
    sessions = get_stt_sessions(limit=10)
    
    if sessions:
        df_sessions = pd.DataFrame(sessions)
        
        # 필요한 컬럼만 선택하여 표시
        display_columns = ['id', 'file_name', 'model_name', 'status', 'processing_time', 'created_at']
        available_columns = [col for col in display_columns if col in df_sessions.columns]
        
        if available_columns:
            st.dataframe(
                df_sessions[available_columns].head(10),
                use_container_width=True
            )
        else:
            st.write("세션 데이터 구조를 확인 중...")
            st.json(sessions[0] if sessions else {})
    else:
        st.info("아직 처리된 세션이 없습니다.")
    
    # 최근 ERP 추출들
    st.subheader("🎯 최근 ERP 추출 결과")
    extractions = get_erp_extractions(limit=5)
    
    if extractions:
        for extraction in extractions:
            with st.expander(f"추출 ID: {extraction.get('id', 'N/A')} - {extraction.get('장비명', 'N/A')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div class="erp-field">
                        <strong>AS 및 지원:</strong> {extraction.get('as_지원', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>요청기관:</strong> {extraction.get('요청기관', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>작업국소:</strong> {extraction.get('작업국소', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>요청일:</strong> {extraction.get('요청일', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>요청시간:</strong> {extraction.get('요청시간', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>요청자:</strong> {extraction.get('요청자', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>지원인원수:</strong> {extraction.get('지원인원수', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="erp-field">
                        <strong>지원요원:</strong> {extraction.get('지원요원', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>장비명:</strong> {extraction.get('장비명', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>기종명:</strong> {extraction.get('기종명', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>A/S기간만료여부:</strong> {extraction.get('as_기간만료여부', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>시스템명(고객사명):</strong> {extraction.get('시스템명', 'N/A')}
                    </div>
                    <div class="erp-field">
                        <strong>요청 사항:</strong> {extraction.get('요청사항', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("아직 추출된 ERP 데이터가 없습니다.") 