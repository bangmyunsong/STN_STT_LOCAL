# 🎙️ STN 고객센터 STT 시스템

**Whisper STT + GPT 기반 ERP 항목 추출 및 연동 시스템 (v1.2)**

OpenAI의 Whisper 모델과 GPT-3.5-turbo/GPT-4o를 활용하여 고객센터 통화 음성을 텍스트로 변환하고, 문맥 기반으로 ERP 등록 항목을 자동 추출하는 고급 시스템입니다.

## ✨ 주요 기능

### 🎯 핵심 기능 (v1.2)
- 🔊 **Whisper STT 배치 처리**: WAV, MP3 등 음성파일을 고정밀 텍스트로 변환
- 👥 **화자 분리**: 상담원과 고객의 대화를 자동으로 구분
- 🤖 **GPT 기반 ERP 항목 추출**: GPT-3.5-turbo/GPT-4o로 ERP 등록용 JSON 데이터 자동 생성
- 📊 **지능형 요약 시스템**: 패턴 매칭 + GPT-4o 하이브리드 요약 (v1.2 신규)
- 🔌 **ERP 연동 API**: REST API를 통한 ERP 시스템 연동 샘플
- 🗄️ **Supabase 연동**: PostgreSQL 기반 데이터 저장 및 관리
- 🎛️ **React 관리자 UI**: STT 결과 확인 및 ERP 추출 관리를 위한 현대적인 웹 대시보드
- 📅 **월별/일별 조회**: 모든 메뉴에서 날짜별 데이터 필터링 및 조회
- 📤 **파일 업로드**: 드래그 앤 드롭 기반 음성 파일 업로드 (v1.1 신규)
- 🔄 **ERP 재추출**: 기존 세션에 대한 ERP 데이터 재추출 (v1.1 신규)
- 🔧 **환경변수 관리**: 실시간 환경변수 상태 모니터링 (v1.1 신규)
- ⚙️ **모델 선택**: GPT-3.5-turbo/GPT-4o 모델 선택 가능 (v1.2 신규)

### 🚀 최신 개선사항 (v1.2)
- **GPT-4o 지원**: GPT-4o 모델을 통한 향상된 요약 및 분석 정확도
- **하이브리드 요약**: 패턴 매칭 + GPT-4o 선택적 사용으로 비용 최적화
- **환경변수 제어**: GPT 모델 및 요약 방식 선택 가능
- **폴백 시스템**: GPT-4o 실패 시 자동으로 패턴 매칭으로 전환
- **성능 최적화**: 패턴 매칭 기반 요약으로 GPT API 호출 횟수 감소
- **UX 개선**: ERP추출/ERP연동 옵션 연동 및 툴팁 추가
- **파일 관리**: 월별/일별 폴더 자동 생성 및 파일 업로드 기능
- **모니터링**: 환경변수 상태 실시간 확인 및 시스템 헬스 체크
- **API 확장**: 파일 업로드, ERP 재추출 등 새로운 엔드포인트 추가

### 📊 ERP 추출 항목

**📋 기본 정보**
- **AS 및 지원**: 지원 방식 (방문기술지원, 원격기술지원, 전화지원 등)
- **요청기관**: 고객사 또는 기관명 (수자원공사 FA망, KT, LG U+ 등)
- **작업국소**: 지역 또는 위치 (서울, 부산, 대전, 대구 등)

**⏰ 일정 정보**
- **요청일**: 고객이 요청한 날짜 (YYYY-MM-DD 형식)
- **요청시간**: 고객이 요청한 시간 (24시간 형식)

**👤 담당자 정보**
- **요청자**: 고객 담당자 이름
- **지원인원수**: 필요한 지원 인원 수 (1명, 2명 등)
- **지원요원**: 투입 예정 기술자 이름

**🔧 장비 정보**
- **장비명**: 장비 종류 (MSPP, 공유기, 모뎀, 스위치 등)
- **기종명**: 구체적인 장비 모델명 (1646SMC, DGS-1100-24 등)
- **A/S기간만료여부**: A/S 기간 상태 (무상, 유상)

**📝 요청 내용**
- **시스템명(고객사명)**: 고객사 시스템명
- **요청 사항**: 고객 요청 내용 요약 (패턴 매칭 기반 자동 생성)

## 🚀 빠른 시작

### 1. 시스템 요구사항
- **Python**: 3.8 이상 (API 서버용)
- **Node.js**: 16.0 이상 (React UI용)
- **메모리**: 최소 8GB RAM (Whisper 및 GPT 처리용)
- **저장공간**: 모델 다운로드를 위한 4GB 여유공간

### 2. 패키지 설치

**API 서버 (Python)**
```bash
# 업데이트된 패키지 설치
pip install -r requirements.txt
```

**React 관리자 UI**
```bash
cd stn-admin-react
npm install
```

### 3. 환경변수 설정

`config.env` 파일을 열어 필요한 API 키와 설정을 입력하세요:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# HuggingFace Hub Token (화자 분리용)
HUGGINGFACE_HUB_TOKEN=hf_your_token_here

# GPT 모델 설정 (v1.2 신규)
# GPT_MODEL=gpt-4o  # GPT-4o 사용 (비용 높음, 정확도 높음)
# GPT_MODEL=gpt-3.5-turbo  # GPT-3.5-turbo 사용 (기본값, 비용 낮음)

# GPT-4o 요약 기능 설정 (v1.2 신규)
# USE_GPT4O_SUMMARY=true   # GPT-4o 요약 기능 활성화
# USE_GPT4O_SUMMARY=false  # 패턴 매칭 요약 사용 (기본값)
```

### 4. Supabase 데이터베이스 설정

1. [Supabase](https://supabase.com) 프로젝트 생성
2. SQL 에디터에서 `supabase_client.py`의 DATABASE_SCHEMA를 실행
3. `config.env`에 Supabase URL과 Key 설정

### 5. 시스템 실행

**전체 시스템 실행 (권장)**
```bash
run_full_system.bat
```

**개별 실행**
```bash
# API 서버 실행
run_api_server.bat

# React 관리자 UI 실행 (새 터미널)
cd stn-admin-react
npm start
```

## 🎛️ 시스템 구성

### 🌐 API 서버 (FastAPI)
- **주소**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스 체크**: http://localhost:8000/health

#### 주요 엔드포인트 (v1.1)
- `POST /api/stt-process`: 음성 파일 업로드를 통한 STT 처리 및 ERP 추출
- `POST /api/stt-process-file`: src_record 디렉토리 파일을 통한 STT 처리 및 ERP 추출
- `GET /api/audio-files`: src_record 디렉토리의 음성 파일 목록 조회
- `POST /api/upload-file`: 음성 파일 업로드 (v1.1 신규)
- `POST /api/sessions/{session_id}/extract-erp`: ERP 재추출 (v1.1 신규)
- `GET /api/environment-status`: 환경변수 상태 확인 (v1.1 신규)
- `POST /api/erp-sample-register`: ERP 시스템 연동 샘플
- `GET /api/sessions`: STT 세션 목록 조회
- `GET /api/statistics`: 시스템 통계 조회

### 🎛️ React 관리자 UI
- **주소**: http://localhost:3000
- **기술 스택**: React 18 + TypeScript + Material-UI + Zustand
- **반응형 디자인**: 데스크톱 및 모바일 최적화

#### 📋 메뉴 구성 (v1.1)

**📊 대시보드**
- 실시간 시스템 현황 및 통계
- 월별/일별 조회를 통한 기간별 데이터 분석
- 주요 메트릭 카드 및 차트 표시
- 시스템 헬스 체크 및 모델 상태 모니터링

**📂 STT 처리**
- 월별/일별 조회를 통한 파일 필터링
- Dual ListBox를 통한 직관적 파일 선택
- 실시간 일괄 처리 및 진행 상황 모니터링
- 처리 옵션 설정 (모델, 화자분리, ERP추출, ERP연동)
- UX 개선: 옵션 연동 및 툴팁 추가

**📈 STT 모니터링**
- 날짜별 파일 처리 상태 모니터링
- 실시간 Supabase 데이터 기반 통계
- 디렉토리별 상세 현황 및 성공률 분석

**👥 세션 관리**
- 월별/일별 조회를 통한 세션 필터링
- 상태별, 모델별 필터링 기능
- 세션별 상세 정보 (전체 텍스트, 세그먼트, ERP 추출 결과)
- ERP 재추출 기능 (v1.1 신규)

**🔍 결과 조회**
- 날짜별 ERP 추출 결과 조회
- 패턴 매칭 요약 결과 확인 (v1.1 신규)
- ERP 시스템 연동 테스트 및 등록 상태 관리
- 추출 결과 검토 및 수정 기능

**📁 파일 관리**
- 월별/일별 조회를 통한 파일 관리
- 파일 업로드 기능 (MP3, WAV, M4A, FLAC, AAC, OGG) (v1.1 신규)
- 파일 통계 및 상태 정보
- 드래그 앤 드롭 기반 업로드 인터페이스

**⚙️ 설정**
- 환경변수 상태 실시간 모니터링 (v1.1 신규)
- API 서버 연결 상태 및 헬스 체크
- 데이터베이스 스키마 정보
- 시스템 모델 상태 확인

## 📖 사용 방법

### 1. API를 통한 STT 처리

#### 📂 디렉토리 파일 처리 (기본 방식)
```bash
# src_record 디렉토리의 파일로 STT 처리
curl -X POST "http://localhost:8000/api/stt-process-file?filename=sample.wav&model_name=base&extract_erp=true&save_to_db=true"

# 디렉토리 내 음성 파일 목록 조회
curl -X GET "http://localhost:8000/api/audio-files"
```

#### 📤 파일 업로드 처리 (v1.1 신규)
```bash
# 음성 파일 업로드 및 처리
curl -X POST "http://localhost:8000/api/upload-file" \
  -F "file=@음성파일.wav" \
  -F "target_date=2025-01-19"

# 업로드된 파일로 STT 처리
curl -X POST "http://localhost:8000/api/stt-process" \
  -F "file=@음성파일.wav" \
  -F "model_name=base" \
  -F "extract_erp=true" \
  -F "save_to_db=true"
```

### 2. React 관리자 UI 사용법

#### 📊 대시보드
- 총 STT 세션 수, ERP 추출 수, 등록 수 등 주요 메트릭 확인
- 월별/일별 조회로 특정 기간 데이터 분석
- API 서버 연결 상태 및 모델 상태 실시간 모니터링
- 환경변수 설정 상태 확인

#### 🎙️ STT 처리
1. **날짜 선택**: 월별/일별 조회에서 처리할 파일의 날짜 선택
2. **파일 선택**: Dual ListBox에서 처리할 파일을 우측으로 이동
3. **옵션 설정**: 모델, 언어, 화자분리, ERP추출 옵션 설정
4. **처리 실행**: "🚀 STT 처리 시작" 버튼으로 일괄 처리 시작
5. **결과 확인**: 실시간 진행 상황 및 완료된 파일 상태 확인

#### 📈 STT 모니터링
- **실시간 데이터**: Supabase에서 실시간으로 처리 상태 조회
- **날짜별 필터링**: 월별/일별 조회로 특정 기간 모니터링
- **상세 분석**: 디렉토리별 성공률, 평균 처리 시간 등 분석

#### 📁 파일 관리 (v1.1 신규)
1. **파일 업로드**: 상단의 파일 업로드 섹션에서 음성 파일 업로드
2. **날짜별 조회**: 월별/일별 필터로 특정 기간 파일 조회
3. **통계 확인**: 전체, 루트, 일자별 파일 수 및 상태 확인
4. **드래그 앤 드롭**: 파일을 드래그하여 간편 업로드

#### ⚙️ 설정 (v1.1 신규)
1. **환경변수 상태**: 실시간 환경변수 설정 상태 모니터링
2. **API 서버 정보**: 연결 상태 및 헬스 체크 정보 확인
3. **데이터베이스 스키마**: Supabase 테이블 정보 조회

### 3. ERP 연동 테스트

추출된 ERP 데이터를 실제 ERP 시스템에 등록하는 과정을 시뮬레이션:

```json
{
  "접수일자": "2025-04-21 10:03",
  "접수자": "배성경",
  "AS 및 지원": "원격기술지원",
  "요청기관": "수자원공사 FA망",
  "작업국소": "대전",
  "요청일": "2025-04-18",
  "요청시간": "15",
  "요청자": "이정순",
  "지원인원수": "1명",
  "지원요원": "임선묵",
  "장비명": "MSPP",
  "기종명": "1646SMC",
  "A/S기간만료여부": "유상",
  "시스템명(고객사명)": "수자원공사 FA망",
  "요청 사항": "[요약] 수자원공사 원격기술지원 요청\n[유형] 장애신고 | 장애신고\n[위치] 대전 | 오늘 오후\n[문제] MSPP 장애 | 장비 문제\n[핵심] 링크 장애 복구 원인 파악 요청"
}
```

**주요 필드 설명:**
- **접수일자, 접수자**: 시스템 자동 입력
- **AS 및 지원, A/S기간만료여부**: 셀렉트박스 항목
- **요청기관, 요청자, 지원요원, 기종명**: 검색 입력
- **장비명, 시스템명**: 자동 설정
- **작업국소, 요청일, 요청시간, 지원인원수**: **STT 기반 추출**
- **요청 사항**: **패턴 매칭 기반 자동 요약 생성** (v1.1 신규)

## 🔧 고급 설정

### Whisper 모델 선택

| 모델 | 크기 | 속도 | 정확도 | 추천 용도 |
|------|------|------|--------|-----------|
| **tiny** | ~39MB | ⚡⚡⚡⚡⚡ | ⭐⭐ | 빠른 테스트 |
| **base** | ~74MB | ⚡⚡⚡⚡ | ⭐⭐⭐ | **기본 권장** |
| **small** | ~244MB | ⚡⚡⚡ | ⭐⭐⭐⭐ | 정확도 중시 |
| **medium** | ~769MB | ⚡⚡ | ⭐⭐⭐⭐⭐ | 높은 정확도 |
| **large** | ~1550MB | ⚡ | ⭐⭐⭐⭐⭐ | 최고 품질 |

### GPT 프롬프트 최적화

`gpt_extractor.py`의 프롬프트를 수정하여 추출 정확도를 향상시킬 수 있습니다:

- 업계별 전문 용어 추가
- 추출 규칙 세분화
- 예시 데이터 확장

### 지능형 요약 시스템 (v1.2 신규)

패턴 매칭과 GPT-4o를 결합한 하이브리드 요약 시스템:

#### 🔄 **하이브리드 요약 방식**
- **GPT-4o 요약**: 향상된 정확도와 맥락 이해 (비용 높음)
- **패턴 매칭 요약**: 고성능, 저비용 요약 (기본값)
- **자동 폴백**: GPT-4o 실패 시 패턴 매칭으로 자동 전환

#### 📊 **패턴 매칭 요약 (v1.1)**
GPT API 호출 없이 고성능 요약을 생성하는 패턴 매칭 시스템:

**구현된 패턴들:**
- **핵심 문장 추출**: 문제, 장애, 요청, 긴급 관련 키워드
- **요청 유형 분석**: 장애신고, 기술지원, 문의사항, 긴급요청
- **문제 상황 추출**: 장비-문제 조합 패턴 매칭
- **시간/장소 정보**: 시간대, 지역, 건물 정보 추출

#### 🤖 **GPT-4o 요약 (v1.2 신규)**
- **향상된 정확도**: 복잡한 요청사항도 정확히 분석
- **맥락 이해**: 기술적 용어와 업무 상황을 정확히 파악
- **구조화된 출력**: 일관된 형식의 요약 생성

**요약 형식:**
```
[요약] [요청기관] [AS 및 지원] 요청
[유형] [요청유형] | [분석된 요청유형]
[위치] [작업국소] | [추출된 시간/장소]
[문제] [추출된 문제 정보]
[핵심] [핵심 문장들]
```

#### ⚙️ **설정 방법**
```env
# config.env에서 설정
USE_GPT4O_SUMMARY=true   # GPT-4o 요약 활성화
USE_GPT4O_SUMMARY=false  # 패턴 매칭 요약 사용 (기본값)
GPT_MODEL=gpt-4o         # GPT-4o 모델 사용
```

## 📁 프로젝트 구조

```
STN_STT_POC/
├── 🎯 핵심 모듈
│   ├── api_server.py           # FastAPI 기반 REST API 서버
│   ├── gpt_extractor.py        # GPT 기반 ERP 항목 추출 모듈
│   ├── gpt_summarizer.py       # GPT-4o 기반 요약 및 분석 클래스 (v1.2 신규)
│   ├── stt_handlers.py         # STT 처리 핸들러 (하이브리드 요약 포함)
│   ├── erp_handlers.py         # ERP 재추출 핸들러
│   ├── admin_handlers.py       # 관리자 API 핸들러 (파일 업로드 포함)
│   ├── supabase_client.py      # Supabase 데이터베이스 연동
│   ├── postprocessor.py        # STT 텍스트 후처리 (음성 매핑, 정규화)
│   ├── models.py               # Pydantic 데이터 모델
│   ├── payload_schema.py       # API 페이로드 스키마
│   ├── domain_loader.py        # 도메인 데이터 로더
│   ├── domain_manager.py       # 도메인 데이터 관리자
│   └── admin_ui.py             # Streamlit 관리자 대시보드 (레거시)
│
├── 🎛️ React 관리자 UI
│   └── stn-admin-react/        # React + TypeScript 기반 현대적 관리자 UI
│       ├── src/
│       │   ├── components/     # React 컴포넌트
│       │   │   ├── dashboard/  # 📊 대시보드
│       │   │   ├── stt/        # 📂 STT 처리
│       │   │   ├── files/      # 📈 STT 모니터링
│       │   │   ├── sessions/   # 👥 세션 관리
│       │   │   ├── results/    # 🔍 결과 조회
│       │   │   ├── status/     # 📁 파일 관리
│       │   │   ├── settings/   # ⚙️ 설정
│       │   │   └── layout/     # 공통 레이아웃
│       │   ├── services/       # API 서비스
│       │   ├── store/          # 상태 관리 (Zustand)
│       │   └── types/          # TypeScript 타입 정의
│       ├── package.json        # React 의존성
│       └── README.md           # React 앱 가이드 (백엔드 API 문서 포함)
│
├── 🎙️ STT 기능
│   ├── stt_app.py              # Streamlit STT 웹앱
│   └── stt_cli.py              # CLI 버전
│
├── 🧪 테스트 파일
│   ├── test_api_health.py      # API 헬스 체크 테스트
│   ├── test_config.py          # 설정 테스트
│   ├── test_erp_extract.py     # ERP 추출 테스트
│   ├── test_integrated_api.py  # 통합 API 테스트
│   ├── test_react_admin_apis.py # React Admin API 테스트
│   ├── test_statistics_api.py  # 통계 API 테스트
│   ├── test_stt_with_db.py     # STT + DB 테스트
│   ├── test_system_health.py   # 시스템 헬스 테스트
│   └── test_whisper.py         # Whisper 테스트
│
├── 🎨 UI 컴포넌트 (Streamlit)
│   └── ui_components/          # Streamlit UI 컴포넌트
│       ├── dashboard.py        # 대시보드 컴포넌트
│       ├── stt_processing.py   # STT 처리 컴포넌트
│       ├── stt_sessions.py     # STT 세션 컴포넌트
│       ├── other_pages.py      # 기타 페이지 컴포넌트
│       ├── api_helpers.py      # API 헬퍼 함수
│       └── utils.py            # 유틸리티 함수
│
├── 📊 도메인 데이터
│   └── domain_data/            # ERP 도메인 데이터
│       ├── equipment_list_minimal.xlsx      # 장비 목록
│       ├── error_types_minimal.xlsx         # 오류 유형
│       └── request_type_mapping_minimal.xlsx # 요청 유형 매핑
│
├── 🔊 음성 파일
│   └── src_record/             # STT 대상 음성파일 디렉토리
│       └── YYYY-MM-DD/         # 일자별 폴더 구조
│
├── ⚙️ 설정 및 실행
│   ├── config.env              # 환경변수 설정
│   ├── requirements.txt        # Python 패키지 의존성
│   ├── run_full_system.bat     # 전체 시스템 실행
│   ├── run_api_server.bat      # API 서버 실행
│   ├── run_admin_ui.bat        # 관리자 UI 실행 (Streamlit)
│   ├── run_frontend.bat        # React 프론트엔드 실행
│   ├── setup_venv.bat          # 가상환경 설정
│   ├── setup_whisperx.bat      # WhisperX 설정
│   ├── install_apscheduler.bat # APScheduler 설치
│   ├── install_ffmpeg.bat      # FFmpeg 설치
│   ├── fix_environment.bat     # 환경 설정 수정
│   └── diagnose_system.bat     # 시스템 진단
│
└── 📚 문서
    └── README.md               # 프로젝트 문서
```

## 🗄️ 데이터베이스 스키마 (v1.2 업데이트)

### 📊 STT 세션 테이블 (stt_sessions)
음성 파일 처리 세션 정보 및 STT 결과 저장:

**기본 정보:**
- `id`: 세션 고유 ID (SERIAL PRIMARY KEY)
- `file_id`: 파일 고유 식별자 (VARCHAR(100) UNIQUE)
- `file_name`: 파일명 (VARCHAR(255))
- `model_name`: Whisper 모델명 (VARCHAR(50), 기본값: 'base')
- `language`: 언어 설정 (VARCHAR(10))

**STT 결과:**
- `transcript`: 후처리된 전사 결과 (TEXT)
- `segments`: 세그먼트 정보 (JSONB)
- `original_transcript`: 원본 전사 결과 (TEXT) - v1.2 신규
- `original_segments`: 원본 세그먼트 정보 (JSONB) - v1.2 신규

**처리 정보:**
- `processing_time`: 처리 시간 (FLOAT)
- `status`: 처리 상태 (VARCHAR(20), 기본값: 'processing')
- `created_at`: 생성 시간 (TIMESTAMP WITH TIME ZONE)
- `updated_at`: 수정 시간 (TIMESTAMP WITH TIME ZONE)

### 📋 ERP 추출 테이블 (erp_extractions)
GPT로 추출된 ERP 항목 데이터 저장:

**기본 정보:**
- `id`: 추출 결과 고유 ID (SERIAL PRIMARY KEY)
- `session_id`: STT 세션 ID (INTEGER, 외래키)
- `as_지원`: 지원 방식 (VARCHAR(50))
- `요청기관`: 고객사 또는 기관명 (VARCHAR(200))
- `작업국소`: 지역 또는 위치 (VARCHAR(100))

**일정 정보:**
- `요청일`: 요청 날짜 (VARCHAR(20), YYYY-MM-DD 형식) - v1.2 수정
- `요청시간`: 요청 시간 (TEXT)

**담당자 정보:**
- `요청자`: 고객 담당자 이름 (VARCHAR(100))
- `지원인원수`: 필요한 지원 인원 수 (VARCHAR(20))
- `지원요원`: 투입 예정 기술자 이름 (VARCHAR(100))

**장비 정보:**
- `장비명`: 장비 종류 (VARCHAR(100))
- `기종명`: 구체적인 장비 모델명 (VARCHAR(100))
- `as_기간만료여부`: A/S 기간 상태 (VARCHAR(20))

**요청 내용:**
- `시스템명`: 고객사 시스템명 (VARCHAR(200))
- `요청사항`: 고객 요청 내용 요약 (TEXT)

**추가 정보:**
- `confidence_score`: 추출 신뢰도 (FLOAT)
- `raw_extraction`: 원본 추출 데이터 (JSONB)
- `created_at`: 생성 시간 (TIMESTAMP WITH TIME ZONE)

### 📝 ERP 등록 로그 (erp_register_logs)
ERP 시스템 연동 시도 기록:

**기본 정보:**
- `id`: 로그 고유 ID (SERIAL PRIMARY KEY)
- `extraction_id`: ERP 추출 결과 ID (INTEGER, 외래키)
- `erp_id`: ERP 시스템 ID (VARCHAR(50))
- `status`: 등록 상태 (VARCHAR(20), 'success' 또는 'failed')
- `response_data`: ERP 시스템 응답 데이터 (JSONB)
- `registered_at`: 등록 시도 시간 (TIMESTAMP WITH TIME ZONE)

### 🔍 인덱스 및 뷰 (v1.2 신규)

#### **성능 최적화 인덱스:**
- `idx_stt_sessions_file_id`: 파일 ID 조회 최적화
- `idx_stt_sessions_created_at`: 생성일시 조회 최적화
- `idx_stt_sessions_file_name`: 파일명 조회 최적화
- `idx_stt_sessions_status`: 처리 상태 조회 최적화
- `idx_erp_extractions_요청기관`: 요청기관별 조회 최적화
- `idx_erp_extractions_작업국소`: 작업국소별 조회 최적화

#### **처리 상태 뷰 (audio_file_processing_status):**
- **파일 정보**: 전체파일경로, 디렉토리, 파일명
- **STT 정보**: 세션 ID, 모델, 상태, 처리시간, 전사결과
- **ERP 정보**: 추출여부, 신뢰도, 모든 ERP 필드
- **등록 정보**: 등록여부, ERP ID, 등록상태
- **진행률**: 전체 처리 진행률 (0-100%)

#### **디렉토리별 요약 뷰 (directory_processing_summary):**
- **통계 정보**: 총 파일수, STT 완료수, ERP 추출수, ERP 등록수
- **성공률**: 완료율, STT 완료율, ERP 추출율
- **시간 정보**: 최초/최근 처리일시, 평균 처리시간
- **디렉토리 지원**: `src_record/YYYY-MM-DD/` 구조 지원

## 🔧 STT 텍스트 후처리

### 📝 음성 매핑 및 정규화
STT 결과의 정확도를 높이기 위한 후처리 시스템이 구현되어 있습니다:

#### 🎯 음성 매핑 (Voice Mapping)
- **STN 관련 용어**: "스테인" → "STN" 자동 변환
- **기술 용어**: 업계 표준 용어로 정규화
- **고객사명**: 약칭을 정식 명칭으로 변환

#### 🔄 텍스트 정규화
- **숫자 변환**: "일곱" → "7", "십오" → "15" 등
- **시간 형식**: "오후 세시" → "15:00" 등
- **날짜 형식**: "이월 십오일" → "2월 15일" 등

#### 📊 후처리 결과
- **원본 텍스트**: Whisper의 원시 출력
- **처리된 텍스트**: 후처리 적용된 최종 텍스트
- **세그먼트 정보**: 화자별 시간 정보와 함께 저장

## 💡 사용 팁

### 🎯 최적의 STT 정확도를 위한 팁
- **명확한 음성**: 배경 소음이 적은 환경에서 녹음
- **적절한 음량**: 너무 크거나 작지 않게 조절
- **화자 구분**: 발화자 전환시 충분한 간격 두기
- **파일 형식**: WAV 또는 FLAC 형식 권장 (무손실 압축)

### 📂 효율적인 파일 관리
- **일자별 폴더**: src_record/YYYY-MM-DD/ 구조로 파일 정리
- **파일명 규칙**: 날짜_시간_고객사 형식 권장 (예: 20250121_1430_수자원공사.wav)
- **배치 처리**: React UI의 Dual ListBox로 여러 파일을 선택하여 일괄 처리
- **월별/일별 조회**: 모든 메뉴에서 날짜별 필터링으로 효율적 관리
- **파일 업로드**: 드래그 앤 드롭으로 간편한 파일 업로드 (v1.1 신규)

### 🤖 GPT 추출 정확도 향상
- **상세한 대화**: 구체적인 문제 설명일수록 정확도 향상
- **전문 용어**: 업계 표준 용어 사용 권장
- **구조화된 대화**: 문제 → 위치 → 요청 순서로 대화 진행

### 🚀 GPT-4o 활용 팁 (v1.2 신규)
- **고정확도 요약**: 복잡한 요청사항이 많은 경우 GPT-4o 요약 활성화
- **비용 최적화**: 일반적인 요청은 패턴 매칭, 복잡한 요청은 GPT-4o 사용
- **환경변수 제어**: `USE_GPT4O_SUMMARY=true`로 GPT-4o 요약 활성화
- **폴백 시스템**: GPT-4o 실패 시 자동으로 패턴 매칭으로 전환되어 안정성 보장

### 🎛️ React UI 활용 팁
- **월별/일별 조회**: 모든 메뉴에서 특정 기간 데이터만 필터링하여 빠른 분석
- **실시간 모니터링**: STT 모니터링에서 처리 상태 실시간 확인
- **일괄 처리**: STT 처리 메뉴에서 여러 파일을 한 번에 처리
- **파일 업로드**: 파일 관리 메뉴에서 드래그 앤 드롭으로 간편 업로드
- **환경변수 확인**: 설정 메뉴에서 시스템 상태 실시간 모니터링 (v1.1 신규)
- **ERP 재추출**: 세션 관리에서 기존 세션의 ERP 데이터 재추출 (v1.1 신규)

### 📊 요약 시스템 활용
#### 패턴 매칭 요약 (v1.1)
- **고성능**: GPT API 호출 없이 빠른 요약 생성
- **정확도**: 고객센터 통화 특화 패턴으로 높은 정확도
- **비용 절약**: GPT API 사용량 감소로 비용 절약
- **실시간**: STT 처리와 동시에 요약 생성

#### GPT-4o 요약 (v1.2 신규)
- **고정확도**: 복잡한 요청사항도 정확히 분석
- **맥락 이해**: 기술적 용어와 업무 상황을 정확히 파악
- **구조화된 출력**: 일관된 형식의 요약 생성
- **폴백 시스템**: 실패 시 자동으로 패턴 매칭으로 전환

## 🛠️ 문제 해결

### 자주 발생하는 문제

#### OpenAI API 관련
```bash
# API 키 오류
Error: OpenAI API 키가 설정되지 않았습니다.
해결: config.env에서 OPENAI_API_KEY 확인

# GPT-4o 모델 오류 (v1.2 신규)
Error: GPT-4o 모델에 접근할 수 없습니다.
해결: OpenAI 계정에 GPT-4o 접근 권한이 있는지 확인
해결: GPT_MODEL=gpt-3.5-turbo로 변경하여 폴백 사용

# GPT-4o 요약 초기화 실패
Error: GPT-4o 요약기 초기화 실패
해결: USE_GPT4O_SUMMARY=false로 설정하여 패턴 매칭 사용
```

#### Supabase 연결 오류
```bash
# Supabase 연결 실패
Error: Supabase URL이 설정되지 않았습니다.
해결: config.env에서 SUPABASE_URL과 SUPABASE_ANON_KEY 확인
```

#### React UI 관련
```bash
# React 앱 실행 오류
Error: npm start 실행 실패
해결: cd stn-admin-react && npm install 먼저 실행

# API 서버 연결 오류
Error: API 서버에 연결할 수 없습니다.
해결: http://localhost:8000이 실행 중인지 확인
```

#### 모델 로딩 오류
```bash
# Whisper 모델 다운로드 실패
해결: 인터넷 연결 확인 및 충분한 저장 공간 확보
```

#### 음성 파일 처리 오류
```bash
# src_record 디렉토리 없음
Error: 음성 파일 디렉토리(src_record)가 존재하지 않습니다.
해결: 프로젝트 루트에 src_record 디렉토리 생성

# 지원하지 않는 파일 형식
Error: 지원하지 않는 파일 형식입니다.
해결: .mp3, .wav, .m4a, .flac, .aac, .ogg 형식 사용
```

#### 파일 업로드 오류 (v1.1 신규)
```bash
# 파일 업로드 실패
Error: 파일 업로드에 실패했습니다
해결: API 서버의 파일 업로드 엔드포인트 확인

# 환경변수 상태 오류
Error: 환경변수 상태를 확인할 수 없습니다
해결: API 서버의 환경변수 로딩 확인
```

## 📞 지원 및 문의

- **이슈 리포트**: GitHub Issues
- **기능 요청**: PRD 문서 참조
- **기술 지원**: 개발팀 문의

---

**STN 고객센터 STT 시스템 v1.2** - 2025.01.19  
*Whisper STT + GPT 기반 ERP 항목 추출 및 연동 시스템*  
*React + TypeScript 현대적 관리자 UI*

### 📝 변경 이력
- **v1.2 (2025.01.19)**: 
  - GPT-4o 지원 및 하이브리드 요약 시스템
  - 환경변수 제어 및 폴백 시스템
  - 데이터베이스 스키마 최적화 (인덱스, 뷰 개선)
  - 원본 전사 결과 보존 기능 (original_transcript, original_segments)
  - 디렉토리별 처리 현황 뷰 확장
- **v1.1 (2025.01.19)**: 패턴 매칭 요약, 파일 업로드, ERP 재추출, 환경변수 관리, UX 개선
- **v1.0 (2025.01.11)**: 초기 버전, 기본 기능 구현