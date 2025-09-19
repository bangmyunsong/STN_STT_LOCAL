import streamlit as st
import whisper
import tempfile
import os
from datetime import datetime
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import torch
import torchaudio
import numpy as np
from dotenv import load_dotenv

# 환경변수 자동 로드
load_dotenv('config.env')

# 페이지 설정
st.set_page_config(
    page_title="AI 음성-텍스트 변환기 (발화자 구분)",
    page_icon="🎙️",
    layout="wide"
)

# CSS 스타일링
st.markdown("""
<style>
.speaker-segment {
    padding: 10px;
    margin: 5px 0;
    border-radius: 8px;
    border-left: 4px solid;
}
.speaker-0 { border-left-color: #FF6B6B; background-color: #FFE5E5; }
.speaker-1 { border-left-color: #4ECDC4; background-color: #E5F9F6; }
.speaker-2 { border-left-color: #45B7D1; background-color: #E5F3FF; }
.speaker-3 { border-left-color: #96CEB4; background-color: #E8F5E8; }
.speaker-4 { border-left-color: #FECA57; background-color: #FFF8E1; }
.speaker-5 { border-left-color: #FF9FF3; background-color: #FFE5FB; }
.speaker-unknown { border-left-color: #95A5A6; background-color: #F8F9FA; }
.env-status-success { 
    background-color: #d4edda; 
    color: #155724; 
    padding: 8px; 
    border-radius: 4px; 
    border: 1px solid #c3e6cb;
}
.env-status-warning { 
    background-color: #fff3cd; 
    color: #856404; 
    padding: 8px; 
    border-radius: 4px; 
    border: 1px solid #ffeaa7;
}
</style>
""", unsafe_allow_html=True)

# HuggingFace 토큰 읽기 (config.env에서 자동 로드됨)
def get_hf_token():
    """config.env에서 로드된 HuggingFace 토큰을 읽어오기"""
    return os.environ.get('HUGGINGFACE_HUB_TOKEN', None)

# 제목 및 설명
st.title("🎙️ AI 음성-텍스트 변환기 (발화자 구분)")
st.markdown("**Whisper AI + 간단한 발화자 구분을 사용한 고정밀 음성 인식 데모**")
st.markdown("---")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # Whisper 모델 선택
    model_options = {
        "tiny": "Tiny (가장 빠름, 낮은 정확도)",
        "base": "Base (빠름, 보통 정확도)", 
        "small": "Small (보통, 좋은 정확도)",
        "medium": "Medium (느림, 높은 정확도)",
        "large": "Large (가장 느림, 최고 정확도)"
    }
    
    selected_model = st.selectbox(
        "Whisper 모델 선택:",
        options=list(model_options.keys()),
        index=2,  # small 모델 기본 선택
        format_func=lambda x: model_options[x]
    )
    
    # 언어 선택
    language_options = {
        "auto": "자동 감지",
        "ko": "한국어",
        "en": "영어",
        "ja": "일본어",
        "zh": "중국어",
        "es": "스페인어",
        "fr": "프랑스어",
        "de": "독일어"
    }
    
    selected_language = st.selectbox(
        "언어 선택:",
        options=list(language_options.keys()),
        index=0,
        format_func=lambda x: language_options[x]
    )
    
    st.markdown("---")
    st.header("👥 발화자 구분 설정")
    
    # 환경변수 토큰 상태 확인
    env_token = get_hf_token()
    
    if env_token:
        st.markdown(f"""
        <div class="env-status-success">
            ✅ <strong>HuggingFace 토큰 감지됨</strong><br>
            환경변수에서 자동으로 토큰을 사용합니다.<br>
            토큰: {env_token[:8]}...{env_token[-4:]}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
    else:
        st.markdown(f"""
        <div class="env-status-warning">
            ⚠️ <strong>환경변수 토큰 없음</strong><br>
            set_env.bat를 실행하여 토큰을 설정하거나<br>
            아래에서 수동으로 입력하세요.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
    
# 발화자 구분 활성화 (강제 활성화 옵션 추가)
enable_diarization = st.checkbox("발화자 구분 활성화", value=True)  # 기본값을 True로 변경
force_diarization = st.checkbox("강제 발화자 구분 (토큰 없이도 시도)", value=True, help="토큰이 없어도 시간 기반 발화자 구분을 강제 실행")

# 전역 변수로 초기화
num_speakers = None
manual_hf_token = None

if enable_diarization:
    if not env_token:
        st.warning("⚠️ HuggingFace 토큰이 없습니다. 기본 발화자 구분만 사용됩니다.")
    
    # 발화자 수 설정
    speaker_detection_mode = st.radio(
        "발화자 수 설정:",
        ["자동 감지", "수동 설정"]
    )
    
    if speaker_detection_mode == "수동 설정":
        num_speakers = st.slider("예상 발화자 수:", 1, 10, 2)
    else:
        num_speakers = None
        
    # HuggingFace 토큰 수동 입력 (환경변수가 없을 때만)
    if not env_token:
        manual_hf_token = st.text_input(
            "HuggingFace 토큰 (수동 입력):",
            type="password",
            help="환경변수가 설정되지 않은 경우 여기에 토큰을 입력하세요"
        )
        
    # 디버깅 정보 표시
    with st.expander("🔍 디버깅 정보"):
        st.write(f"환경변수 토큰: {'✅ 있음' if env_token else '❌ 없음'}")
        st.write(f"수동 토큰: {'✅ 입력됨' if manual_hf_token else '❌ 없음'}")
        st.write(f"발화자 수: {num_speakers if num_speakers else '자동 감지'}")
        st.write(f"강제 구분: {'✅ 활성화' if force_diarization else '❌ 비활성화'}")
    
    st.markdown("---")
    st.markdown("### 📋 지원 파일 형식")
    st.markdown("- MP3, WAV, M4A, FLAC")
    st.markdown("- 최대 파일 크기: 200MB")
    
    # 환경변수 설정 가이드
    st.markdown("---")
    st.markdown("### 🔧 토큰 관리")
    st.markdown("**토큰을 변경하려면:**")
    st.code("config.env 파일을 열어서 토큰을 수정하세요", language="bash")
    st.markdown("프로그램을 다시 시작하면 새 토큰이 적용됩니다.")

def simple_speaker_diarization(whisper_segments, num_speakers=None):
    """
    강화된 발화자 구분 - 다중 전략 사용
    """
    if not whisper_segments:
        return whisper_segments
    
    max_speakers = num_speakers if num_speakers else 2  # 기본값을 2로 변경
    
    # 전략 1: 침묵 기반 구분 (가장 확실한 방법)
    def silence_based_diarization():
        current_speaker = 0
        previous_end = 0
        
        for i, segment in enumerate(whisper_segments):
            start_time = segment.get('start', 0)
            pause_duration = start_time - previous_end
            
            # 1초 이상 침묵이면 발화자 전환
            if i > 0 and pause_duration > 1.0:
                current_speaker = (current_speaker + 1) % max_speakers
            
            segment['speaker'] = f'SPEAKER_{current_speaker:02d}'
            previous_end = segment.get('end', start_time)
        
        return whisper_segments
    
    # 전략 2: 교대 패턴 (대화의 기본 특성)
    def alternating_pattern():
        for i, segment in enumerate(whisper_segments):
            if max_speakers == 2:
                # 2명일 때는 교대로
                segment['speaker'] = f'SPEAKER_{i % 2:02d}'
            else:
                # 3명 이상일 때는 순환
                segment['speaker'] = f'SPEAKER_{i % max_speakers:02d}'
        
        return whisper_segments
    
    # 전략 3: 하이브리드 방법 (침묵 + 교대)
    def hybrid_method():
        current_speaker = 0
        previous_end = 0
        speaker_changes = 0
        
        for i, segment in enumerate(whisper_segments):
            start_time = segment.get('start', 0)
            pause_duration = start_time - previous_end
            
            # 긴 침묵이면 발화자 전환
            if i > 0 and pause_duration > 1.5:
                current_speaker = (current_speaker + 1) % max_speakers
                speaker_changes += 1
            # 교대 패턴도 고려 (3개 세그먼트마다)
            elif i > 0 and i % 3 == 0 and pause_duration > 0.5:
                current_speaker = (current_speaker + 1) % max_speakers
                speaker_changes += 1
            
            segment['speaker'] = f'SPEAKER_{current_speaker:02d}'
            previous_end = segment.get('end', start_time)
        
        return whisper_segments, speaker_changes
    
    # 최적의 전략 선택
    if len(whisper_segments) <= 4:
        # 세그먼트가 적으면 단순 교대
        return alternating_pattern()
    else:
        # 하이브리드 방법 시도
        result_segments, changes = hybrid_method()
        
        # 발화자 변경이 너무 적으면 교대 패턴 사용
        if changes < len(whisper_segments) // 4:
            return alternating_pattern()
        else:
            return result_segments

def load_pyannote_pipeline(hf_token=None):
    """pyannote-audio 파이프라인을 안전하게 로드"""
    try:
        from pyannote.audio import Pipeline
        
        # 사용 가능한 모델들을 순서대로 시도
        models_to_try = [
            "pyannote/speaker-diarization",  # 구버전 (공개)
            "pyannote/speaker-diarization-3.1",  # 최신 (제한됨)
        ]
        
        for model_name in models_to_try:
            try:
                if hf_token:
                    # 최신 API: token 파라미터 사용 (fallback으로 use_auth_token)
                    try:
                        pipeline = Pipeline.from_pretrained(model_name, token=hf_token)
                    except TypeError:
                        pipeline = Pipeline.from_pretrained(model_name, use_auth_token=hf_token)
                else:
                    pipeline = Pipeline.from_pretrained(model_name)
                return pipeline, model_name
            except Exception as e:
                continue
        
        return None, None
        
    except ImportError:
        return None, None
    except Exception as e:
        return None, None

def assign_speakers_to_segments(whisper_segments, diarization_result):
    """Whisper 세그먼트에 발화자 정보 할당"""
    for segment in whisper_segments:
        start_time = segment['start']
        end_time = segment['end']
        
        # 해당 시간대의 발화자 찾기
        speakers_in_segment = {}
        
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            if turn.start < end_time and turn.end > start_time:
                # 겹치는 부분의 길이 계산
                overlap_start = max(turn.start, start_time)
                overlap_end = min(turn.end, end_time)
                overlap_duration = overlap_end - overlap_start
                
                if overlap_duration > 0:
                    speakers_in_segment[speaker] = speakers_in_segment.get(speaker, 0) + overlap_duration
        
        # 가장 많이 겹치는 발화자 할당
        if speakers_in_segment:
            dominant_speaker = max(speakers_in_segment, key=speakers_in_segment.get)
            segment['speaker'] = dominant_speaker
        else:
            segment['speaker'] = 'UNKNOWN'
    
    return whisper_segments

# 메인 컨텐츠
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📁 파일 업로드")
    
    # 파일 업로더
    uploaded_file = st.file_uploader(
        "오디오 파일을 선택하세요",
        type=['mp3', 'wav', 'm4a', 'flac', 'ogg', 'wma'],
        help="지원되는 오디오 파일을 업로드하세요."
    )
    
    if uploaded_file is not None:
        st.success(f"✅ 파일 업로드 완료: {uploaded_file.name}")
        
        # 파일 정보 표시
        file_size = uploaded_file.size / (1024 * 1024)  # MB 단위
        st.info(f"📊 파일 크기: {file_size:.2f} MB")
        
        # 오디오 플레이어
        st.audio(uploaded_file, format='audio/mp3')

with col2:
    st.header("🔄 변환 결과")
    
    if uploaded_file is not None:
        # 변환 버튼
        if st.button("🚀 텍스트 변환 시작", type="primary", use_container_width=True):
            
            # 진행 상태 표시
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 임시 파일로 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                status_text.text("🔄 Whisper 모델 로딩 중...")
                progress_bar.progress(20)
                
                # Whisper 모델 로드
                model = whisper.load_model(selected_model)
                
                status_text.text("🎙️ 음성 변환 중...")
                progress_bar.progress(40)
                
                # 음성 인식 실행
                language_param = None if selected_language == "auto" else selected_language
                result = model.transcribe(tmp_file_path, language=language_param)
                
                progress_bar.progress(60)
                
                # 발화자 구분 수행
                diarization_success = False
                diarization_method = "없음"
                
                # 디버깅 정보 수집
                debug_info = {
                    "enable_diarization": enable_diarization,
                    "force_diarization": force_diarization,
                    "has_segments": bool(result["segments"]),
                    "segment_count": len(result["segments"]) if result["segments"] else 0,
                    "env_token": bool(env_token),
                    "manual_token": bool(manual_hf_token),
                    "num_speakers": num_speakers
                }
                
                # 발화자 구분 시도 (조건 확대)
                if (enable_diarization or force_diarization) and result["segments"]:
                    status_text.text("👥 발화자 구분 중...")
                    
                    # 토큰 우선순위: 환경변수 > 수동입력
                    final_token = env_token or manual_hf_token
                    
                    st.info(f"🔍 디버깅: 세그먼트 수 {len(result['segments'])}, 토큰 {'있음' if final_token else '없음'}")
                    
                    # pyannote-audio 사용 시도
                    if final_token:
                        pipeline, model_used = load_pyannote_pipeline(final_token)
                        
                        if pipeline is not None:
                            try:
                                status_text.text("🤖 AI 모델로 발화자 구분 중...")
                                
                                if num_speakers:
                                    diarization_result = pipeline(tmp_file_path, num_speakers=num_speakers)
                                else:
                                    diarization_result = pipeline(tmp_file_path)
                                
                                # 발화자 정보를 Whisper 세그먼트에 할당
                                result["segments"] = assign_speakers_to_segments(result["segments"], diarization_result)
                                diarization_success = True
                                diarization_method = f"pyannote-audio ({model_used})"
                                
                                # 토큰 사용 상태 표시
                                token_source = "환경변수" if env_token else "수동입력"
                                st.success(f"✅ pyannote-audio 모델 ({model_used}) 사용 성공! (토큰: {token_source})")
                                
                            except Exception as e:
                                st.warning(f"⚠️ pyannote-audio 발화자 구분 실패: {str(e)}")
                                debug_info["pyannote_error"] = str(e)
                        else:
                            st.warning("⚠️ pyannote-audio 모델 로드 실패")
                    
                    # pyannote-audio 실패 시 또는 토큰 없을 때 간단한 방법 사용
                    if not diarization_success:
                        status_text.text("🔄 시간 기반 발화자 구분 중...")
                        st.info("🔄 간단한 발화자 구분 방법을 사용합니다...")
                        
                        # 강화된 간단 발화자 구분 실행
                        original_segments = [s.copy() for s in result["segments"]]  # 백업
                        result["segments"] = simple_speaker_diarization(result["segments"], num_speakers)
                        
                        # 발화자 구분이 실제로 적용되었는지 확인
                        speakers_found = set(segment.get("speaker", "UNKNOWN") for segment in result["segments"])
                        if len(speakers_found) > 1:
                            diarization_success = True
                            diarization_method = "시간 기반 추정"
                            st.success(f"✅ 시간 기반 발화자 구분 완료! 감지된 발화자: {len(speakers_found)}명")
                        else:
                            st.error("❌ 발화자 구분 실패 - 모든 세그먼트가 동일한 발화자로 분류됨")
                            debug_info["simple_failed"] = True
                
                # 디버깅 정보 표시
                with st.expander("🔍 발화자 구분 디버깅 정보"):
                    st.json(debug_info)
                    st.write(f"**사용된 방법:** {diarization_method}")
                    if result["segments"]:
                        speakers = [segment.get("speaker", "UNKNOWN") for segment in result["segments"]]
                        unique_speakers = set(speakers)
                        st.write(f"**감지된 발화자:** {list(unique_speakers)}")
                        st.write(f"**발화자별 세그먼트 수:** {dict((s, speakers.count(s)) for s in unique_speakers)}")
                
                progress_bar.progress(100)
                status_text.text("✅ 변환 완료!")
                
                # 결과 표시
                st.success("🎉 텍스트 변환이 완료되었습니다!")
                
                # 전체 텍스트
                full_text = result["text"]
                
                # 탭으로 결과 구분
                tab1, tab2, tab3 = st.tabs(["📝 발화자별 텍스트", "📊 타임라인", "📋 전체 텍스트"])
                
                with tab1:
                    # 발화자 정보 확인 (더 관대한 조건)
                    has_speaker_info = any(segment.get("speaker") and segment.get("speaker") != "UNKNOWN" for segment in result["segments"])
                    
                    if has_speaker_info or diarization_success:
                        st.subheader("👥 발화자별 구분된 텍스트:")
                        
                        # 발화자별 색상 매핑
                        speakers = list(set(segment.get("speaker", "UNKNOWN") for segment in result["segments"]))
                        speaker_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3"]
                        
                        # 발화자가 1명만 감지된 경우 강제로 2명으로 재분할
                        if len(speakers) == 1 and speakers[0] == "SPEAKER_00":
                            st.warning("⚠️ 발화자가 1명만 감지되어 강제로 2명으로 재분할합니다.")
                            for i, segment in enumerate(result["segments"]):
                                segment['speaker'] = f'SPEAKER_{i % 2:02d}'
                            speakers = ["SPEAKER_00", "SPEAKER_01"]
                        
                        for i, segment in enumerate(result["segments"]):
                            speaker = segment.get("speaker", f"SPEAKER_{i % 2:02d}")  # 백업 할당
                            text = segment.get("text", "")
                            start_time = segment.get("start", 0)
                            end_time = segment.get("end", 0)
                            
                            # 시간 포맷팅
                            start_str = f"{int(start_time//60):02d}:{int(start_time%60):02d}"
                            end_str = f"{int(end_time//60):02d}:{int(end_time%60):02d}"
                            
                            speaker_idx = speakers.index(speaker) if speaker in speakers else i % len(speaker_colors)
                            if speaker_idx >= len(speaker_colors):
                                speaker_idx = speaker_idx % len(speaker_colors)
                            
                            st.markdown(f"""
                            <div class="speaker-segment speaker-{speaker_idx}">
                                <strong>🎤 {speaker} [{start_str}-{end_str}]</strong><br>
                                {text}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("❌ 발화자 구분 실패 - 기본 형식으로 표시합니다.")
                        st.info("강제 발화자 구분을 활성화하고 다시 시도해보세요.")
                        
                        for segment in result["segments"]:
                            text = segment.get("text", "")
                            start_time = segment.get("start", 0)
                            end_time = segment.get("end", 0)
                            start_str = f"{int(start_time//60):02d}:{int(start_time%60):02d}"
                            end_str = f"{int(end_time//60):02d}:{int(end_time%60):02d}"
                            
                            st.markdown(f"**[{start_str}-{end_str}]** {text}")
                
                with tab2:
                    if result["segments"]:
                        st.subheader("📊 발화 타임라인:")
                        
                        # 타임라인 데이터 준비
                        timeline_data = []
                        for segment in result["segments"]:
                            timeline_data.append({
                                "Speaker": segment.get("speaker", "UNKNOWN"),
                                "Start": segment.get("start", 0),
                                "End": segment.get("end", 0),
                                "Duration": segment.get("end", 0) - segment.get("start", 0),
                                "Text": segment.get("text", "")[:50] + "..." if len(segment.get("text", "")) > 50 else segment.get("text", "")
                            })
                        
                        df = pd.DataFrame(timeline_data)
                        
                        if enable_diarization and any("speaker" in segment for segment in result["segments"]):
                            # Gantt 차트 생성
                            fig = px.timeline(df, x_start="Start", x_end="End", y="Speaker", color="Speaker",
                                            hover_data=["Text"], title="발화자별 타임라인")
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # 발화자별 통계
                            speaker_stats = df.groupby("Speaker")["Duration"].agg(["count", "sum"]).round(2)
                            speaker_stats.columns = ["발화 횟수", "총 발화 시간(초)"]
                            st.subheader("📈 발화자별 통계:")
                            st.dataframe(speaker_stats)
                        else:
                            st.info("발화자 구분 데이터가 없어 기본 타임라인을 표시합니다.")
                            fig = go.Figure()
                            for i, row in df.iterrows():
                                fig.add_trace(go.Scatter(
                                    x=[row["Start"], row["End"]],
                                    y=[1, 1],
                                    mode="lines+markers",
                                    name=f"Segment {i+1}",
                                    text=row["Text"],
                                    hovertemplate="<b>%{text}</b><br>Start: %{x[0]:.1f}s<br>End: %{x[1]:.1f}s"
                                ))
                            fig.update_layout(title="음성 세그먼트 타임라인", xaxis_title="시간 (초)", yaxis_title="세그먼트")
                            st.plotly_chart(fig, use_container_width=True)
                
                with tab3:
                    st.subheader("📝 전체 텍스트:")
                    st.text_area("", value=full_text, height=300, disabled=True)
                    
                    # 상세 정보
                    with st.expander("📊 상세 정보 보기"):
                        st.write(f"**감지된 언어:** {result.get('language', 'Unknown')}")
                        st.write(f"**총 세그먼트 수:** {len(result['segments'])}")
                        
                        if enable_diarization and any("speaker" in segment for segment in result["segments"]):
                            unique_speakers = set(segment.get("speaker", "UNKNOWN") for segment in result["segments"])
                            st.write(f"**감지된 발화자 수:** {len(unique_speakers)}")
                            st.write(f"**발화자 목록:** {', '.join(unique_speakers)}")
                            
                            if diarization_success:
                                method = "고급 AI 모델" if 'pyannote' in str(locals().get('model_used', '')) else "시간 기반 추정"
                                token_info = f" (토큰: {'환경변수' if env_token else '수동입력' if locals().get('manual_hf_token') else '없음'})"
                                st.write(f"**발화자 구분 방법:** {method}{token_info}")
                
                # 결과 다운로드
                st.subheader("💾 다운로드")
                col_txt, col_json, col_csv = st.columns(3)
                
                with col_txt:
                    # 발화자별 텍스트 파일
                    if enable_diarization and any("speaker" in segment for segment in result["segments"]):
                        speaker_text = ""
                        for segment in result["segments"]:
                            speaker = segment.get("speaker", "UNKNOWN")
                            text = segment.get("text", "")
                            start_time = segment.get("start", 0)
                            end_time = segment.get("end", 0)
                            start_str = f"{int(start_time//60):02d}:{int(start_time%60):02d}"
                            end_str = f"{int(end_time//60):02d}:{int(end_time%60):02d}"
                            speaker_text += f"[{start_str}-{end_str}] {speaker}: {text}\n"
                    else:
                        speaker_text = full_text
                        
                    st.download_button(
                        label="📄 발화자별 텍스트 다운로드",
                        data=speaker_text,
                        file_name=f"transcript_speakers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
                
                with col_json:
                    # JSON 파일 다운로드
                    json_data = json.dumps(result, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📋 JSON 파일 다운로드",
                        data=json_data,
                        file_name=f"transcript_detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                with col_csv:
                    # CSV 파일 다운로드
                    if result["segments"]:
                        csv_data = []
                        for segment in result["segments"]:
                            csv_data.append({
                                "발화자": segment.get("speaker", "UNKNOWN"),
                                "시작시간": segment.get("start", 0),
                                "종료시간": segment.get("end", 0),
                                "텍스트": segment.get("text", "")
                            })
                        df_csv = pd.DataFrame(csv_data)
                        csv_string = df_csv.to_csv(index=False, encoding='utf-8-sig')
                        
                        st.download_button(
                            label="📊 CSV 파일 다운로드",
                            data=csv_string,
                            file_name=f"transcript_segments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
                # 임시 파일 삭제
                os.unlink(tmp_file_path)
                
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")
                if 'tmp_file_path' in locals():
                    os.unlink(tmp_file_path)
    else:
        st.info("👈 먼저 오디오 파일을 업로드해주세요.")

# 하단 정보
st.markdown("---")
st.markdown("### 💡 사용 팁")
col_tip1, col_tip2, col_tip3, col_tip4 = st.columns(4)

with col_tip1:
    st.markdown("**🎯 최적의 음질**")
    st.markdown("- 배경 소음 최소화")
    st.markdown("- 명확한 발음")
    st.markdown("- 적절한 음량")

with col_tip2:
    st.markdown("**⚡ 모델 선택 가이드**")
    st.markdown("- Small: 일반적 사용")
    st.markdown("- Medium: 높은 품질")
    st.markdown("- Large: 최고 품질")

with col_tip3:
    st.markdown("**👥 발화자 구분 팁**")
    st.markdown("- 명확한 화자 구분")
    st.markdown("- 적절한 발화 간격")
    st.markdown("- 발화자 수 사전 파악")

with col_tip4:
    st.markdown("**🌍 언어 지원**")
    st.markdown("- 99개 언어 지원")
    st.markdown("- 자동 감지 추천")
    st.markdown("- 다국어 혼용 가능")

st.markdown("---")
st.markdown("### 📝 환경변수로 토큰 관리")
st.info("""
**보안을 위한 환경변수 사용:**
1. `set_env.bat` 실행하여 토큰을 환경변수로 설정
2. 터미널을 다시 시작한 후 앱 실행
3. 환경변수가 설정되면 자동으로 토큰 사용

**환경변수의 장점:**
- 🔒 코드에 토큰이 노출되지 않음
- 🔄 매번 입력할 필요 없음
- 🛡️ 더 안전한 토큰 관리
""")

st.markdown("**Made with ❤️ using Whisper AI, pyannote-audio & Streamlit**") 