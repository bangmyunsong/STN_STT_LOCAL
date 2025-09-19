"""
STN 고객센터 STT 시스템 관리자 UI
Streamlit 기반 통합 관리 대시보드 - 리팩토링된 버전
"""

import streamlit as st
import os
from dotenv import load_dotenv

# UI 컴포넌트 import
from ui_components.api_helpers import check_api_connection
from ui_components.dashboard import show_dashboard
from ui_components.stt_sessions import show_stt_sessions
from ui_components.stt_processing import show_stt_processing
from ui_components.other_pages import (
    show_erp_extractions, show_file_processing_status, show_system_settings
)

# 환경변수 로드
load_dotenv('config.env')

# 페이지 설정
st.set_page_config(
    page_title="STN STT 시스템 관리자",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
}
.success-box {
    background-color: #d4edda;
    color: #155724;
    padding: 10px;
    border-radius: 5px;
    border-left: 5px solid #28a745;
}
.warning-box {
    background-color: #fff3cd;
    color: #856404;
    padding: 10px;
    border-radius: 5px;
    border-left: 5px solid #ffc107;
}
.error-box {
    background-color: #f8d7da;
    color: #721c24;
    padding: 10px;
    border-radius: 5px;
    border-left: 5px solid #dc3545;
}
.erp-field {
    background-color: #e9ecef;
    padding: 8px;
    border-radius: 4px;
    margin: 2px 0;
}
</style>
""", unsafe_allow_html=True)


def main():
    """메인 UI 함수"""
    st.title("🎛️ STN STT 시스템 관리자 대시보드")
    st.markdown("---")
    
    # 사이드바
    with st.sidebar:
        st.header("📋 메뉴")
        
        # 페이지 상태 관리 (대시보드에서 페이지 이동을 위해)
        if 'page' not in st.session_state:
            st.session_state.page = "🏠 대시보드"
        
        # selectbox 옵션 정의
        page_options = ["🏠 대시보드", "🎙️ STT 처리", "📊 STT 세션 관리", "🔍 ERP 추출 관리", "📁 파일 처리 상태", "⚙️ 시스템 설정"]
        
        # 현재 페이지의 인덱스 계산
        try:
            current_index = page_options.index(st.session_state.page)
        except ValueError:
            current_index = 0  # 기본값: 대시보드
        
        page = st.selectbox(
            "페이지 선택:",
            page_options,
            index=current_index,
            key="page_selector"
        )
        
        # 페이지 상태 업데이트 (단순한 동기화)
        if page != st.session_state.page:
            st.session_state.page = page
        
        st.markdown("---")
        
        # API 연결 상태 확인
        api_connected, health_data = check_api_connection()
        
        if api_connected:
            st.markdown("""
            <div class="success-box">
                ✅ <strong>API 서버 연결됨</strong><br>
                서버가 정상 작동 중입니다.
            </div>
            """, unsafe_allow_html=True)
            
            if health_data:
                st.write("**모델 상태:**")
                models = health_data.get('models', {})
                for model, status in models.items():
                    status_emoji = "✅" if status else "❌"
                    st.write(f"{status_emoji} {model}: {'OK' if status else 'Error'}")
        else:
            st.markdown("""
            <div class="error-box">
                ❌ <strong>API 서버 연결 실패</strong><br>
                API 서버를 시작해주세요:<br>
                <code>python api_server.py</code>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**🔗 빠른 링크**")
        st.markdown("- [API 문서](http://localhost:8000/docs)")
        st.markdown("- [헬스 체크](http://localhost:8000/health)")
        
        st.markdown("---")
        st.markdown("**⚡ 성능 도구**")
        if st.button("🗑️ 캐시 초기화"):
            st.cache_data.clear()
            st.success("✅ 모든 캐시가 초기화되었습니다!")
            st.rerun()
    
    # 페이지별 콘텐츠
    if page == "🏠 대시보드":
        show_dashboard()
    elif page == "🎙️ STT 처리":
        show_stt_processing()
    elif page == "📊 STT 세션 관리":
        show_stt_sessions()
    elif page == "🔍 ERP 추출 관리":
        show_erp_extractions()
    elif page == "📁 파일 처리 상태":
        show_file_processing_status()
    elif page == "⚙️ 시스템 설정":
        show_system_settings()


if __name__ == "__main__":
    main() 