"""
공통 유틸리티 함수들
"""

import streamlit as st
import os
import json
from typing import Dict, Any


def safe_get_string(data: Dict[str, Any], key: str, default: str = '') -> str:
    """딕셔너리에서 값을 가져오되, None인 경우 빈 문자열로 변환"""
    value = data.get(key, default)
    return '' if value is None else str(value)


def render_erp_status_badge(status):
    """ERP 상태 배지 렌더링"""
    if status['registered']:
        return "🟢 **완료** (추출+등록)"
    elif status['extracted']:
        return "🟡 **추출됨** (등록필요)"
    else:
        return "🔴 **미처리** (추출필요)"


def display_stt_result(result, extract_erp):
    """STT 처리 결과 표시"""
    # 전체 텍스트 표시
    st.write("**📝 전체 텍스트:**")
    st.text_area("", result.get('transcript', ''), height=100, key=f"transcript_{result.get('file_id', 'unknown')}")
    
    # 세그먼트 표시
    if result.get('segments'):
        with st.expander("📋 세그먼트 정보"):
            segments = result['segments']
            for i, segment in enumerate(segments[:10]):  # 처음 10개만 표시
                st.write(f"**{i+1}.** [{segment.get('start', 0):.1f}s - {segment.get('end', 0):.1f}s] **{segment.get('speaker', 'Unknown')}**: {segment.get('text', '')}")
            
            if len(segments) > 10:
                st.info(f"+ {len(segments) - 10}개의 세그먼트가 더 있습니다.")
    
    # ERP 추출 결과 표시
    if result.get('erp_data') and extract_erp:
        with st.expander("🔍 ERP 추출 결과"):
            erp_data = result['erp_data']
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**AS 및 지원:** {erp_data.get('AS 및 지원', 'N/A')}")
                st.write(f"**요청기관:** {erp_data.get('요청기관', 'N/A')}")
                st.write(f"**작업국소:** {erp_data.get('작업국소', 'N/A')}")
                st.write(f"**요청일:** {erp_data.get('요청일', 'N/A')}")
                st.write(f"**요청시간:** {erp_data.get('요청시간', 'N/A')}")
                st.write(f"**요청자:** {erp_data.get('요청자', 'N/A')}")
                st.write(f"**지원인원수:** {erp_data.get('지원인원수', 'N/A')}")
                st.write(f"**지원요원:** {erp_data.get('지원요원', 'N/A')}")
            
            with col2:
                st.write(f"**장비명:** {erp_data.get('장비명', 'N/A')}")
                st.write(f"**기종명:** {erp_data.get('기종명', 'N/A')}")
                st.write(f"**A/S기간만료여부:** {erp_data.get('A/S기간만료여부', 'N/A')}")
                st.write(f"**시스템명(고객사명):** {erp_data.get('시스템명(고객사명)', 'N/A')}")
                st.write(f"**요청 사항:** {erp_data.get('요청 사항', 'N/A')}")


def get_file_emoji(filename):
    """파일 확장자에 따른 이모지 반환"""
    ext = os.path.splitext(filename)[1].lower()
    emoji_map = {
        '.mp3': '🎵',
        '.wav': '🎶', 
        '.m4a': '🎤',
        '.flac': '🎼',
        '.aac': '🔊',
        '.ogg': '📻'
    }
    return emoji_map.get(ext, '🎵')  # 기본값: 🎵


def show_session_detail(session_id, get_session_detail_func):
    """세션 상세 정보 표시"""
    detail = get_session_detail_func(session_id)
    
    if not detail:
        st.error("세션 정보를 가져올 수 없습니다.")
        return
    
    session = detail.get('session', {})
    erp_extraction = detail.get('erp_extraction', {})
    
    st.subheader(f"세션 {session_id} 상세 정보")
    
    # 전체 텍스트
    if session.get('transcript'):
        st.write("**전체 텍스트:**")
        st.text_area("", value=session['transcript'], height=150, disabled=True)
    
    # 세그먼트 정보
    if session.get('segments'):
        st.write("**세그먼트 정보:**")
        try:
            segments = json.loads(session['segments']) if isinstance(session['segments'], str) else session['segments']
            for i, segment in enumerate(segments[:10]):  # 처음 10개만 표시
                st.write(f"**{i+1}.** [{segment.get('start', 0):.1f}s - {segment.get('end', 0):.1f}s] {segment.get('speaker', 'Unknown')}: {segment.get('text', '')}")
        except:
            st.write("세그먼트 데이터 파싱 오류")
    
    # ERP 추출 결과
    if erp_extraction:
        st.write("**🔍 ERP 추출 결과:**")
        st.write(f"**AS 및 지원:** {erp_extraction.get('as_지원', 'N/A')}")
        st.write(f"**요청기관:** {erp_extraction.get('요청기관', 'N/A')}")
        st.write(f"**작업국소:** {erp_extraction.get('작업국소', 'N/A')}")
        st.write(f"**요청일:** {erp_extraction.get('요청일', 'N/A')}")
        st.write(f"**요청시간:** {erp_extraction.get('요청시간', 'N/A')}")
        st.write(f"**요청자:** {erp_extraction.get('요청자', 'N/A')}")
        st.write(f"**지원인원수:** {erp_extraction.get('지원인원수', 'N/A')}")
        st.write(f"**지원요원:** {erp_extraction.get('지원요원', 'N/A')}")
        st.write(f"**장비명:** {erp_extraction.get('장비명', 'N/A')}")
        st.write(f"**기종명:** {erp_extraction.get('기종명', 'N/A')}")
        st.write(f"**A/S기간만료여부:** {erp_extraction.get('as_기간만료여부', 'N/A')}")
        st.write(f"**시스템명(고객사명):** {erp_extraction.get('시스템명', 'N/A')}")
        st.write(f"**요청 사항:** {erp_extraction.get('요청사항', 'N/A')}")
    else:
        st.info("ERP 추출 결과가 없습니다.")


def process_bulk_files(selected_files, model_name, extract_erp, auto_register, process_func, register_func, save_to_db=True):
    """일괄 파일 처리"""
    total_files = len(selected_files)
    success_count = 0
    error_count = 0
    
    # 진행 상태 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    for i, file_path in enumerate(selected_files):
        # 진행률 업데이트
        progress = (i + 1) / total_files
        progress_bar.progress(progress)
        
        # 표시용 파일명 추출 (경로에서 파일명만)
        display_filename = os.path.basename(file_path)
        status_text.text(f"처리 중: {display_filename} ({i+1}/{total_files})")
        
        try:
            # STT 처리
            success, result = process_func(file_path, model_name, extract_erp, save_to_db)
            
            if success:
                success_count += 1
                
                # 자동 등록 옵션이 활성화되고 ERP 추출이 성공한 경우
                if auto_register and extract_erp and result.get('erp_data') and result.get('extraction_id'):
                    try:
                        register_success, register_result = register_func(
                            result['erp_data'], 
                            result['extraction_id']
                        )
                        if register_success:
                            result['auto_registered'] = True
                            result['erp_id'] = register_result.get('erp_id', 'N/A')
                    except Exception as e:
                        result['auto_register_error'] = str(e)
                
                # 결과 표시
                with results_container.expander(f"✅ {display_filename} - 성공"):
                    display_stt_result(result, extract_erp)
                    if result.get('auto_registered'):
                        st.success(f"🎉 ERP 자동 등록 완료: {result.get('erp_id')}")
                    elif result.get('auto_register_error'):
                        st.warning(f"⚠️ ERP 자동 등록 실패: {result.get('auto_register_error')}")
            else:
                error_count += 1
                with results_container.expander(f"❌ {display_filename} - 실패"):
                    st.error(f"오류: {result}")
                    
        except Exception as e:
            error_count += 1
            with results_container.expander(f"❌ {display_filename} - 실패"):
                st.error(f"처리 중 오류 발생: {str(e)}")
    
    # 최종 결과 요약
    progress_bar.progress(1.0)
    status_text.text(f"일괄 처리 완료!")
    
    st.success(f"""
    🎯 **일괄 처리 완료!**
    - **성공:** {success_count}개
    - **실패:** {error_count}개
    - **전체:** {total_files}개
    """)
    
    if auto_register:
        st.info(f"📤 **ERP 자동 등록:** 시도됨 (성공한 STT 처리 건에 대해)") 