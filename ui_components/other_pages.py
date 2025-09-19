"""
기타 페이지 컴포넌트들 (ERP 관리, 파일 상태, 시스템 설정)
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from .api_helpers import (
    check_api_connection, get_erp_extractions, get_erp_register_logs,
    get_audio_files, get_directory_processing_summary, get_file_processing_status,
    register_erp_sample, API_BASE_URL, update_directory_view
)
import requests
from .utils import safe_get_string


def show_erp_extractions():
    """ERP 추출 관리 페이지"""
    st.header("🔍 ERP 추출 관리")
    
    if not check_api_connection()[0]:
        st.error("API 서버에 연결할 수 없습니다.")
        return
    
    extractions = get_erp_extractions(limit=100)
    
    if not extractions:
        st.info("아직 추출된 ERP 데이터가 없습니다.")
        return
    
    st.subheader(f"📋 총 {len(extractions)}개의 추출 결과")
    
    # 등록 로그 가져오기 (등록 상태 확인용)
    register_logs = get_erp_register_logs(limit=200)
    
    # 각 extraction의 등록 상태 매핑 생성
    registration_status = {}
    for log in register_logs:
        extraction_id = log.get('extraction_id')
        if extraction_id and log.get('status') == 'success':
            registration_status[extraction_id] = {
                'registered': True,
                'erp_id': log.get('erp_id', 'N/A'),
                'registered_at': log.get('registered_at', 'N/A')
            }
    
    # ERP 추출 결과 목록
    for extraction in extractions:
        with st.expander(f"추출 ID: {extraction.get('id', 'N/A')} - {extraction.get('장비명', 'N/A')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**세션 ID:** {extraction.get('session_id', 'N/A')}")
                st.write(f"**AS 및 지원:** {extraction.get('as_지원', 'N/A')}")
                st.write(f"**요청기관:** {extraction.get('요청기관', 'N/A')}")
                st.write(f"**작업국소:** {extraction.get('작업국소', 'N/A')}")
                st.write(f"**요청일:** {extraction.get('요청일', 'N/A')}")
                st.write(f"**요청시간:** {extraction.get('요청시간', 'N/A')}")
                st.write(f"**요청자:** {extraction.get('요청자', 'N/A')}")
                st.write(f"**지원인원수:** {extraction.get('지원인원수', 'N/A')}")
            
            with col2:
                st.write(f"**지원요원:** {extraction.get('지원요원', 'N/A')}")
                st.write(f"**장비명:** {extraction.get('장비명', 'N/A')}")
                st.write(f"**기종명:** {extraction.get('기종명', 'N/A')}")
                st.write(f"**A/S기간만료여부:** {extraction.get('as_기간만료여부', 'N/A')}")
                st.write(f"**시스템명(고객사명):** {extraction.get('시스템명', 'N/A')}")
                st.write(f"**요청 사항:** {extraction.get('요청사항', 'N/A')}")
                st.write(f"**신뢰도:** {extraction.get('confidence_score', 'N/A')}")
                st.write(f"**생성일:** {extraction.get('created_at', 'N/A')}")
                
                # 등록 상태 확인
                extraction_id = extraction.get('id')
                is_registered = extraction_id in registration_status
                
                if is_registered:
                    # 이미 등록된 경우
                    reg_info = registration_status[extraction_id]
                    st.success("✅ **ERP 등록 완료**")
                    st.write(f"**ERP ID:** {reg_info['erp_id']}")
                    st.write(f"**등록일:** {reg_info['registered_at'][:19] if reg_info['registered_at'] != 'N/A' else 'N/A'}")
                    
                    # 비활성화된 버튼 표시
                    st.button(f"ERP 등록", key=f"register_{extraction_id}", disabled=True, help="이미 등록된 항목입니다")
                else:
                    # 아직 등록되지 않은 경우
                    if st.button(f"ERP 등록", key=f"register_{extraction_id}", type="primary"):
                        erp_data = {
                            "AS 및 지원": safe_get_string(extraction, 'as_지원'),
                            "요청기관": safe_get_string(extraction, '요청기관'),
                            "작업국소": safe_get_string(extraction, '작업국소'),
                            "요청일": safe_get_string(extraction, '요청일'),
                            "요청시간": safe_get_string(extraction, '요청시간'),
                            "요청자": safe_get_string(extraction, '요청자'),
                            "지원인원수": safe_get_string(extraction, '지원인원수'),
                            "지원요원": safe_get_string(extraction, '지원요원'),
                            "장비명": safe_get_string(extraction, '장비명'),
                            "기종명": safe_get_string(extraction, '기종명'),
                            "A/S기간만료여부": safe_get_string(extraction, 'as_기간만료여부'),
                            "시스템명(고객사명)": safe_get_string(extraction, '시스템명'),
                            "요청 사항": safe_get_string(extraction, '요청사항')
                        }
                        
                        success, result = register_erp_sample(erp_data, extraction_id)
                        
                        if success:
                            st.success(f"ERP 등록 성공: {result.get('erp_id', 'N/A')}")
                            # 등록 성공 후 캐시 초기화하여 상태 업데이트
                            get_erp_register_logs.clear()
                            st.rerun()
                        else:
                            st.error("ERP 등록 실패")


def show_file_processing_status():
    """📁 파일 처리 상태 페이지 (디렉토리별)"""
    st.header("📁 음성파일 처리 상태 (디렉토리별)")
    
    if not check_api_connection()[0]:
        st.error("API 서버에 연결할 수 없습니다.")
        return
    
    # 일자별 폴더 선택 기능 추가
    st.subheader("📅 일자별 폴더 선택")
    
    # 음성 파일 목록에서 일자별 폴더 정보 가져오기
    success, audio_data = get_audio_files()
    available_folders = ["전체 폴더"]
    
    if success and audio_data.get("daily_files"):
        daily_folders = list(audio_data["daily_files"].keys())
        daily_folders.sort(reverse=True)  # 최신 날짜부터 정렬
        available_folders.extend(daily_folders)
        
        # 루트 폴더도 파일이 있으면 추가
        if audio_data.get("files"):
            available_folders.append("루트 폴더")
    
    # 오늘 날짜 폴더 처리를 위한 session_state 확인
    if 'goto_today_folder' in st.session_state and st.session_state.goto_today_folder:
        today_folder = st.session_state.get('today_folder_target', '')
        if today_folder in available_folders:
            # 오늘 폴더의 인덱스를 찾아서 설정
            default_index = available_folders.index(today_folder)
        else:
            default_index = 0
        # 플래그 초기화
        del st.session_state.goto_today_folder
        if 'today_folder_target' in st.session_state:
            del st.session_state.today_folder_target
    else:
        default_index = 0
    
    # 폴더 선택 UI
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        selected_folder = st.selectbox(
            "📂 처리 상태를 확인할 폴더 선택:",
            available_folders,
            index=default_index,
            key="folder_selector"
        )
    
    with col2:
        if st.button("🔄 폴더 목록 새로고침"):
            get_audio_files.clear()
            get_directory_processing_summary.clear()
            get_file_processing_status.clear()
            st.rerun()
    
    with col3:
        # 오늘 날짜 폴더로 바로 이동
        if success and audio_data.get("today_folder"):
            today_folder = audio_data["today_folder"]
            if st.button(f"📅 오늘({today_folder})"):
                if today_folder in available_folders:
                    # session_state 플래그 설정하고 rerun
                    st.session_state.goto_today_folder = True
                    st.session_state.today_folder_target = today_folder
                    st.rerun()
                else:
                    st.warning(f"오늘 폴더({today_folder})에 파일이 없습니다.")
    
    # 선택된 폴더에 대한 정보 표시
    if selected_folder != "전체 폴더":
        st.info(f"📁 **선택된 폴더:** {selected_folder}")
        
        # 선택된 폴더의 파일 수 정보
        if success and audio_data:
            if selected_folder == "루트 폴더":
                file_count = len(audio_data.get("files", []))
                st.write(f"📊 **폴더 내 파일 수:** {file_count}개")
            elif selected_folder in audio_data.get("daily_files", {}):
                file_count = len(audio_data["daily_files"][selected_folder])
                st.write(f"📊 **폴더 내 파일 수:** {file_count}개")
    
    st.markdown("---")
    
    # 캐시 초기화 및 뷰 업데이트 버튼
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 데이터 새로고침", key="refresh_file_status"):
            get_directory_processing_summary.clear()
            get_file_processing_status.clear()
            st.success("✅ 데이터가 새로고침되었습니다!")
            st.rerun()
    
    with col2:
        if st.button("🔧 뷰 업데이트", key="update_view"):
            with st.spinner("뷰를 업데이트하는 중..."):
                success, message = update_directory_view()
                if success:
                    st.success(f"✅ {message}")
                    # 캐시 초기화하여 새로운 데이터 로드
                    get_directory_processing_summary.clear()
                    get_file_processing_status.clear()
                    st.rerun()
                else:
                    st.error(f"❌ 뷰 업데이트 실패: {message}")
    
    # 디렉토리별 요약 (선택된 폴더에 따라 필터링)
    st.subheader("📊 디렉토리별 처리 현황")
    
    # 디버깅: 전체 데이터와 필터링된 데이터 비교
    st.write("**🔍 디버깅 정보:**")
    st.write(f"선택된 폴더: '{selected_folder}'")
    
    # 전체 디렉토리 목록 먼저 확인
    all_directories = get_directory_processing_summary(folder=None)
    st.write("**전체 디렉토리 목록:**")
    for d in all_directories:
        st.write(f"- 디렉토리: '{d.get('디렉토리')}', 파일수: {d.get('총_파일수', 0)}")
    
    # 선택된 폴더로 필터링된 결과
    directory_summary = get_directory_processing_summary(folder=selected_folder)
    st.write(f"**'{selected_folder}' 필터링 후 API 응답:**")
    for d in directory_summary:
        st.write(f"- 디렉토리: '{d.get('디렉토리')}', 파일수: {d.get('총_파일수', 0)}")
    
    st.write(f"**필터링된 결과 개수:** {len(directory_summary)}개 디렉토리")
    
    if directory_summary:
        df_summary = pd.DataFrame(directory_summary)
        
        # 전체 요약 메트릭
        col1, col2, col3, col4 = st.columns(4)
        
        total_files = df_summary['총_파일수'].sum()
        total_completed = df_summary['erp_등록수'].sum()
        avg_completion = (total_completed / total_files * 100) if total_files > 0 else 0
        
        with col1:
            st.metric("총 파일 수", total_files)
        with col2:
            st.metric("완료된 파일", total_completed)
        with col3:
            st.metric("전체 완료율", f"{avg_completion:.1f}%")
        with col4:
            st.metric("디렉토리 수", len(df_summary))
        
        # 디렉토리별 상세 현황
        st.subheader("📂 디렉토리별 상세 현황")
        
        # 진행률 바 포함 테이블
        for _, row in df_summary.iterrows():
            with st.expander(f"📁 {row['디렉토리']} - 완료율: {row['완료율']}% ({row['erp_등록수']}/{row['총_파일수']})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("총 파일", row['총_파일수'])
                    st.metric("STT 완료", row['stt_완료수'])
                
                with col2:
                    st.metric("ERP 추출", row['erp_추출수'])
                    st.metric("ERP 등록", row['erp_등록수'])
                
                with col3:
                    # 진행률 표시
                    progress = row['완료율'] / 100 if row['완료율'] is not None else 0
                    st.progress(progress)
                    st.caption(f"완료율: {row['완료율']}%")
                    
                    # 처리 기간 정보
                    if row.get('최초_처리일시') and row.get('최근_처리일시'):
                        st.caption(f"처리 기간: {row['최초_처리일시'][:10]} ~ {row['최근_처리일시'][:10]}")
                
                # 해당 디렉토리의 파일 목록 보기 버튼
                if st.button(f"📋 {row['디렉토리']} 파일 목록 보기", key=f"view_{row['디렉토리']}"):
                    st.session_state.selected_directory = row['디렉토리']
                    st.rerun()
    else:
        if selected_folder == "전체 폴더":
            st.info("아직 처리된 파일이 없습니다.")
        else:
            st.info(f"선택된 폴더 '{selected_folder}'에서 처리된 파일이 없습니다.")
    
    # 선택된 디렉토리의 파일 목록 표시
    if hasattr(st.session_state, 'selected_directory'):
        selected_dir = st.session_state.selected_directory
        show_directory_files(selected_dir)


def show_directory_files(directory: str):
    """특정 디렉토리의 파일 목록 표시"""
    st.markdown("---")
    st.subheader(f"📂 {directory} 디렉토리 파일 목록")
    
    # 디렉토리 닫기 버튼
    if st.button("❌ 디렉토리 목록 닫기", key="close_directory"):
        if hasattr(st.session_state, 'selected_directory'):
            del st.session_state.selected_directory
        st.rerun()
    
    # 선택된 폴더 정보 표시
    selected_folder = getattr(st.session_state, 'folder_selector', '전체 폴더')
    if selected_folder != "전체 폴더":
        st.info(f"📁 필터: {selected_folder} 폴더의 {directory} 디렉토리 파일들")
    
    files = get_file_processing_status(directory=directory if directory != "루트" else None)
    
    # 선택된 폴더에 따른 추가 필터링
    if files and selected_folder != "전체 폴더":
        if selected_folder == "루트 폴더":
            # 루트 폴더: 경로에 날짜 폴더가 없는 파일들만
            files = [f for f in files if '/' not in f.get('전체파일경로', '').replace('src_record/', '')]
        else:
            # 특정 날짜 폴더: 해당 날짜가 경로에 포함된 파일들만
            files = [f for f in files if selected_folder in f.get('전체파일경로', '')]
    
    if files:
        df = pd.DataFrame(files)
        
        # 필터링 옵션
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "처리 상태 필터:",
                ["전체"] + list(df['전체_처리상태'].unique()),
                key=f"filter_{directory}"
            )
        
        with col2:
            search_filename = st.text_input(
                "파일명 검색:",
                key=f"search_{directory}"
            )
        
        with col3:
            # 새로고침 버튼
            if st.button("🔄 새로고침", key=f"refresh_{directory}"):
                get_file_processing_status.clear()
                st.rerun()
        
        # 필터 적용
        if status_filter != "전체":
            df = df[df['전체_처리상태'] == status_filter]
        if search_filename:
            df = df[df['파일명'].str.contains(search_filename, case=False)]
        
        # 결과 표시
        if not df.empty:
            st.write(f"**검색 결과:** {len(df)}개 파일")
            
            # 상태별 색상 적용을 위한 함수
            def get_status_color(status):
                color_map = {
                    '완료': '🟢',
                    '추출완료': '🟡', 
                    'STT완료': '🔵',
                    '처리중': '🟠',
                    '미처리': '🔴'
                }
                return color_map.get(status, '⚫')
            
            # 상태에 이모지 추가
            df['상태'] = df['전체_처리상태'].apply(lambda x: f"{get_status_color(x)} {x}")
            
            # 표시할 컬럼 선택
            display_df = df[['파일명', '상태', '처리_진행률', 'stt_처리시간', '최종_업데이트']].copy()
            display_df['처리_진행률'] = display_df['처리_진행률'].apply(lambda x: f"{x}%")
            display_df['stt_처리시간'] = display_df['stt_처리시간'].apply(
                lambda x: f"{x:.2f}초" if x is not None else "N/A"
            )
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("필터 조건에 맞는 파일이 없습니다.")
    else:
        st.info(f"{directory} 디렉토리에 처리된 파일이 없습니다.")


def show_system_settings():
    """시스템 설정 페이지"""
    st.header("⚙️ 시스템 설정")
    
    # 환경변수 상태 확인
    st.subheader("🔐 환경변수 설정 상태")
    
    # 환경변수 다시 로드 (config.env 파일 변경 시 반영)
    load_dotenv('config.env', override=True)
    
    env_vars = {
        "OpenAI API Key": os.getenv('OPENAI_API_KEY'),
        "Supabase URL": os.getenv('SUPABASE_URL'),
        "Supabase Key": os.getenv('SUPABASE_ANON_KEY'),
        "HuggingFace Token": os.getenv('HUGGINGFACE_HUB_TOKEN')
    }
    
    for name, value in env_vars.items():
        if value and value not in ['your_openai_api_key_here', 'your_supabase_url_here', 'your_supabase_anon_key_here']:
            st.success(f"✅ {name}: 설정됨")
        else:
            st.error(f"❌ {name}: 설정되지 않음")
    
    st.markdown("---")
    
    # API 서버 정보
    st.subheader("🌐 API 서버 정보")
    st.write(f"**Base URL:** {API_BASE_URL}")
    
    api_connected, health_data = check_api_connection()
    if api_connected:
        st.success("✅ API 서버 연결됨")
        if health_data:
            st.json(health_data)
    else:
        st.error("❌ API 서버 연결 실패")
    
    st.markdown("---")
    
    # 데이터베이스 스키마 정보
    st.subheader("🗄️ 데이터베이스 스키마")
    st.markdown("""
    **필요한 Supabase 테이블:**
    - `stt_sessions`: STT 처리 세션 정보
    - `erp_extractions`: ERP 추출 결과
    - `erp_register_logs`: ERP 등록 로그
    
    **스키마 생성 SQL은 `supabase_client.py` 파일을 참조하세요.**
    """) 