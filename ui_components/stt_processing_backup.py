"""
STT 처리 페이지 컴포넌트
"""

import streamlit as st
import os
from .api_helpers import (
    check_api_connection, get_audio_files, 
    process_audio_file_from_directory, register_erp_sample, get_file_processing_status
)
from .utils import get_file_emoji, display_stt_result, process_bulk_files


def show_stt_processing():
    """STT 처리 페이지"""
    st.header("🎙️ STT 처리")
    
    if not check_api_connection()[0]:
        st.error("API 서버에 연결할 수 없습니다.")
        return
    
    # 탭으로 구분
    tab1, tab2 = st.tabs(["📂 디렉토리에서 선택", "📤 파일 업로드"])
    
    with tab1:
        st.subheader("src_record 디렉토리에서 파일 선택")
        
        # 파일 목록 새로고침 버튼
        if st.button("🔄 파일 목록 새로고침", key="refresh_files"):
            st.rerun()
        
        # 파일 목록 가져오기
        success, audio_data = get_audio_files()
        
        if success and (audio_data.get("files") or audio_data.get("daily_files")):
            root_files = audio_data.get("files", [])
            daily_files = audio_data.get("daily_files", {})
            today_folder = audio_data.get("today_folder", "")
            
            # 전체 파일 수 계산
            total_files = len(root_files) + sum(len(files) for files in daily_files.values())
            
            st.write(f"**📂 디렉토리:** {audio_data.get('directory', 'src_record')}")
            st.write(f"**📊 총 파일 수:** {total_files}개 (루트: {len(root_files)}개, 일자별: {sum(len(files) for files in daily_files.values())}개)")
            
            # 폴더 선택 드롭다운
            folder_options = ["전체 폴더"]
            if root_files:
                folder_options.append("루트 폴더")
            
            # 일자별 폴더 옵션 추가 (최신 날짜 순으로 정렬)
            sorted_date_folders = sorted(daily_files.keys(), reverse=True)
            folder_options.extend(sorted_date_folders)
            
            # Today 버튼과 폴더 선택을 같은 행에 배치
            col1, col2 = st.columns([3, 1])
            
            # Today 버튼 플래그 처리
            if getattr(st.session_state, 'goto_today_stt_folder', False):
                target_folder = st.session_state.get('target_today_stt_folder', '')
                if target_folder in folder_options:
                    current_index = folder_options.index(target_folder)
                else:
                    current_index = 0
                # 플래그 정리
                st.session_state.goto_today_stt_folder = False
                if 'target_today_stt_folder' in st.session_state:
                    del st.session_state.target_today_stt_folder
            else:
                # 기본 인덱스 (현재 선택된 폴더 유지)
                current_selection = getattr(st.session_state, 'stt_folder_selector', '전체 폴더')
                current_index = folder_options.index(current_selection) if current_selection in folder_options else 0
            
            with col1:
                selected_folder = st.selectbox(
                    "📁 처리할 폴더 선택:",
                    folder_options,
                    index=current_index,
                    key="stt_folder_selector"
                )
            
            # 폴더 변경 시 체크박스 상태 초기화
            if 'prev_stt_folder' not in st.session_state:
                st.session_state.prev_stt_folder = selected_folder
            elif st.session_state.prev_stt_folder != selected_folder:
                # 폴더가 변경되었을 때 모든 체크박스 상태 초기화
                keys_to_remove = [key for key in st.session_state.keys() if key.startswith('filtered_file_check_')]
                for key in keys_to_remove:
                    del st.session_state[key]
                st.session_state.prev_stt_folder = selected_folder
            
            with col2:
                # Today 버튼 (오늘 날짜 폴더가 있는 경우만)
                if today_folder and today_folder in daily_files:
                    if st.button("📅 Today", key="stt_today", help=f"{today_folder} 폴더로 이동"):
                        st.session_state.goto_today_stt_folder = True
                        st.session_state.target_today_stt_folder = today_folder
                        st.rerun()
            
            # 선택된 폴더에 따른 파일 목록 필터링 및 처리 완료 파일 제외
            if selected_folder == "전체 폴더":
                # 모든 파일을 하나의 리스트로 통합
                available_files = []
                
                # 루트 파일들 추가
                for file_info in root_files:
                    file_emoji = get_file_emoji(file_info['filename'])
                    file_data = {
                        "display_name": f"{file_emoji} {file_info['filename']} ({file_info['size']} bytes) [루트]",
                        "path": file_info['path'],
                        "filename": file_info['filename'],
                        "size": file_info['size'],
                        "location": file_info['location']
                    }
                    available_files.append(file_data)
                
                # 일자별 폴더 파일들 추가
                for date_folder, files_list in daily_files.items():
                    for file_info in files_list:
                        file_emoji = get_file_emoji(file_info['filename'])
                        file_data = {
                            "display_name": f"{file_emoji} {file_info['filename']} ({file_info['size']} bytes) [{date_folder}]",
                            "path": file_info['path'],
                            "filename": file_info['filename'],
                            "size": file_info['size'],
                            "location": file_info['location']
                        }
                        available_files.append(file_data)
                        
            elif selected_folder == "루트 폴더":
                # 루트 폴더 파일만
                available_files = []
                for file_info in root_files:
                    file_emoji = get_file_emoji(file_info['filename'])
                    file_data = {
                        "display_name": f"{file_emoji} {file_info['filename']} ({file_info['size']} bytes)",
                        "path": file_info['path'],
                        "filename": file_info['filename'],
                        "size": file_info['size'],
                        "location": file_info['location']
                    }
                    available_files.append(file_data)
                        
            else:
                # 특정 날짜 폴더 파일만
                available_files = []
                if selected_folder in daily_files:
                    for file_info in daily_files[selected_folder]:
                        file_emoji = get_file_emoji(file_info['filename'])
                        file_data = {
                            "display_name": f"{file_emoji} {file_info['filename']} ({file_info['size']} bytes)",
                            "path": file_info['path'],
                            "filename": file_info['filename'],
                            "size": file_info['size'],
                            "location": file_info['location']
                        }
                        available_files.append(file_data)
            
            # 처리 완료된 파일들 제외 (성능 최적화)
            with st.spinner("처리 완료된 파일 확인 중..."):
                # 선택된 폴더의 처리된 파일 목록을 한 번에 가져오기
                if selected_folder == "전체 폴더":
                    processed_files_data = get_file_processing_status(directory=None, limit=1000)
                elif selected_folder == "루트 폴더":
                    processed_files_data = get_file_processing_status(directory="루트", limit=1000)
                else:
                    processed_files_data = get_file_processing_status(directory=selected_folder, limit=1000)
                
                # 처리된 파일 경로 세트 생성 (빠른 조회를 위해)
                processed_paths = set()
                if processed_files_data:
                    for item in processed_files_data:
                        full_path = item.get('전체파일경로', '')
                        if full_path:
                            processed_paths.add(full_path)
                
                # 미처리 파일만 필터링
                unprocessed_files = []
                processed_count = 0
                
                for file_data in available_files:
                    if file_data['path'] not in processed_paths:
                        unprocessed_files.append(file_data)
                    else:
                        processed_count += 1
            
            # 파일 상태 정보 표시
            total_files = len(available_files)
            available_count = len(unprocessed_files)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("전체 파일", total_files)
            with col2:
                st.metric("처리 가능", available_count, delta=f"-{processed_count} 처리완료")
            with col3:
                st.metric("처리 완료", processed_count)
            
            # 선택된 폴더 정보 표시
            if selected_folder != "전체 폴더":
                st.info(f"📁 **선택된 폴더:** {selected_folder}")
            else:
                st.info(f"📁 **선택된 폴더:** {selected_folder}")
            
            if not unprocessed_files:
                st.warning("처리 가능한 파일이 없습니다. 모든 파일이 이미 처리 완료되었습니다.")
                return

            # STT 처리 대상 목록 초기화 (session_state)
            if 'stt_target_files' not in st.session_state:
                st.session_state.stt_target_files = []
            
            # 폴더 변경 시 STT 처리 대상 초기화
            if 'prev_stt_folder' not in st.session_state:
                st.session_state.prev_stt_folder = selected_folder
            elif st.session_state.prev_stt_folder != selected_folder:
                st.session_state.stt_target_files = []
                st.session_state.prev_stt_folder = selected_folder
            
            # Dual ListBox UI (개선된 리스트박스 형태)
            st.markdown("---")
            st.subheader("📋 STT 처리 파일 선택")
            
            # 현재 처리 가능한 파일 목록 (STT 처리 대상에 없는 것들)
            target_paths = [item['path'] for item in st.session_state.stt_target_files]
            available_for_selection = [f for f in unprocessed_files if f['path'] not in target_paths]
            
            col1, col2, col3 = st.columns([5, 2, 5])
            
            with col1:
                st.write("**처리할 파일 선택**")
                
                # 리스트박스 형태 (체크박스 사용)
                if available_for_selection:
                    # 전체 선택/해제 버튼
                    sub_col1, sub_col2 = st.columns(2)
                    with sub_col1:
                        if st.button("✅ 전체 선택", key="select_all_available"):
                            for i, file_data in enumerate(available_for_selection):
                                st.session_state[f"available_check_{file_data['path']}"] = True
                            st.rerun()
                    with sub_col2:
                        if st.button("❌ 전체 해제", key="deselect_all_available"):
                            for i, file_data in enumerate(available_for_selection):
                                st.session_state[f"available_check_{file_data['path']}"] = False
                            st.rerun()
                    
                    # 파일 리스트 (체크박스)
                    selected_available_files = []
                    
                    # 컨테이너를 사용해 스크롤 가능한 영역 만들기
                    with st.container():
                        for file_data in available_for_selection:
                            checkbox_key = f"available_check_{file_data['path']}"
                            is_checked = st.checkbox(
                                file_data['display_name'],
                                value=st.session_state.get(checkbox_key, False),
                                key=checkbox_key
                            )
                            if is_checked:
                                selected_available_files.append(file_data)
                    
                    st.caption(f"사용 가능: {len(available_for_selection)}개")
                else:
                    st.info("처리 가능한 파일이 없습니다.")
            
            with col2:
                st.write("**이동**")
                st.write("")  # 간격 조정
                st.write("")  # 간격 조정
                
                # => 버튼 (선택된 파일들을 STT 처리 대상으로 이동)
                move_to_disabled = not any(st.session_state.get(f"available_check_{f['path']}", False) for f in available_for_selection)
                
                if st.button("➡️", key="move_to_target", 
                           help="선택된 파일을 STT 처리 대상으로 이동",
                           disabled=move_to_disabled, type="secondary"):
                    # 선택된 파일들을 STT 처리 대상에 추가
                    for file_data in available_for_selection:
                        checkbox_key = f"available_check_{file_data['path']}"
                        if st.session_state.get(checkbox_key, False):
                            if file_data not in st.session_state.stt_target_files:
                                st.session_state.stt_target_files.append(file_data)
                            # 체크박스 해제
                            st.session_state[checkbox_key] = False
                    st.rerun()
                
                st.write("")  # 간격
                
                # <= 버튼 (STT 처리 대상에서 제거)
                move_from_disabled = not any(st.session_state.get(f"target_check_{f['path']}", False) for f in st.session_state.stt_target_files)
                
                if st.button("⬅️", key="move_from_target",
                           help="선택된 파일을 처리 대상에서 제거",
                           disabled=move_from_disabled, type="secondary"):
                    # 선택된 파일들을 STT 처리 대상에서 제거
                    files_to_remove = []
                    for file_data in st.session_state.stt_target_files:
                        checkbox_key = f"target_check_{file_data['path']}"
                        if st.session_state.get(checkbox_key, False):
                            files_to_remove.append(file_data)
                            # 체크박스 해제
                            st.session_state[checkbox_key] = False
                    
                    for file_data in files_to_remove:
                        st.session_state.stt_target_files.remove(file_data)
                    st.rerun()
            
            with col3:
                st.write("**STT 처리 대상**")
                
                if st.session_state.stt_target_files:
                    # 전체 선택/해제 버튼
                    sub_col1, sub_col2 = st.columns(2)
                    with sub_col1:
                        if st.button("✅ 전체 선택", key="select_all_target"):
                            for file_data in st.session_state.stt_target_files:
                                st.session_state[f"target_check_{file_data['path']}"] = True
                            st.rerun()
                    with sub_col2:
                        if st.button("❌ 전체 해제", key="deselect_all_target"):
                            for file_data in st.session_state.stt_target_files:
                                st.session_state[f"target_check_{file_data['path']}"] = False
                            st.rerun()
                    
                    # 처리 대상 파일 리스트 (체크박스)
                    with st.container():
                        for file_data in st.session_state.stt_target_files:
                            checkbox_key = f"target_check_{file_data['path']}"
                            st.checkbox(
                                file_data['display_name'],
                                value=st.session_state.get(checkbox_key, False),
                                key=checkbox_key
                            )
                    
                    st.caption(f"처리 대상: {len(st.session_state.stt_target_files)}개")
                else:
                    st.info("처리 대상 파일이 없습니다.")

            # 처리 옵션
            if st.session_state.stt_target_files:
                st.markdown("---")
                st.subheader("⚙️ STT 처리 옵션")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    model_name = st.selectbox(
                        "STT 모델 선택:",
                        ["base", "small", "medium", "large"],
                        key="stt_model"
                    )
                with col2:
                    extract_erp = st.checkbox("ERP 추출 포함", value=True, key="stt_erp")
                with col3:
                    auto_register = st.checkbox("ERP 자동 등록", value=True, key="stt_auto_register")
                
                # STT 처리 시작 버튼
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.info(f"📋 **처리 예정:** {len(st.session_state.stt_target_files)}개 파일이 순차적으로 처리됩니다.")
                
                with col2:
                    if st.button("🚀 STT 처리 시작", key="start_stt_processing", type="primary"):
                        # 처리 대상 파일 경로 목록
                        target_file_paths = [f['path'] for f in st.session_state.stt_target_files]
                        
                        # 일괄 처리 실행
                        process_bulk_files(
                            target_file_paths, model_name, extract_erp, auto_register,
                            process_audio_file_from_directory, register_erp_sample
                        )
                        
                        # 처리 완료 후 대상 목록 초기화
                        st.session_state.stt_target_files = []
                        st.rerun()
            else:
                st.info("📝 STT 처리할 파일을 선택해주세요. 좌측에서 파일을 선택하고 ➡️ 버튼을 클릭하세요.")
        else:
            if not success:
                st.error("파일 목록을 가져올 수 없습니다. API 서버 상태를 확인해주세요.")
            else:
                st.info("src_record 디렉토리에 음성 파일이 없습니다.")
                st.markdown("**지원되는 파일 형식:** .mp3, .wav, .m4a, .flac, .aac, .ogg")
    
    with tab2:
        st.subheader("음성 파일 직접 업로드")
        st.info("🚧 파일 업로드 기능은 향후 구현될 예정입니다.")
        st.markdown("현재는 `src_record` 디렉토리에 파일을 직접 복사한 후 '디렉토리에서 선택' 탭을 사용해주세요.") 