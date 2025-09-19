# 🎛️ STN STT 관리자 UI (React)

**React + TypeScript + Material-UI 기반 현대적 웹 관리자 대시보드**

STN 고객센터 STT 시스템의 관리자 인터페이스입니다. Whisper STT 처리, ERP 추출, 데이터 관리를 위한 직관적이고 반응형 웹 UI를 제공합니다.

## ✨ 주요 기능

### 🎯 핵심 UI 기능
- 📊 **실시간 대시보드**: 시스템 현황 및 통계 모니터링
- 📂 **STT 처리**: Dual ListBox 기반 직관적 파일 선택 및 일괄 처리
- 📈 **STT 모니터링**: 실시간 Supabase 데이터 기반 상태 모니터링
- 👥 **세션 관리**: 필터링 및 상세 정보 조회
- 🔍 **결과 조회**: ERP 추출 결과 관리 및 등록
- 📁 **파일 관리**: 파일 업로드 및 통계 관리
- 📅 **월별/일별 조회**: 모든 메뉴에서 날짜별 데이터 필터링
- ⚙️ **시스템 설정**: 환경변수 상태 및 시스템 정보 관리

### 🚀 최신 기능 (v1.1)
- 📤 **파일 업로드**: 드래그 앤 드롭 기반 음성 파일 업로드
- 🔄 **ERP 재추출**: 기존 세션에 대한 ERP 데이터 재추출
- 📊 **패턴 매칭 요약**: GPT API 없이 고성능 요약 생성
- 🎯 **UX 개선**: ERP추출/ERP연동 옵션 연동 및 툴팁 추가
- 🔧 **환경변수 관리**: 실시간 환경변수 상태 모니터링

### 🛠 기술 스택
- **Frontend**: React 18 + TypeScript
- **UI Framework**: Material-UI (MUI) v5
- **상태 관리**: Zustand
- **HTTP Client**: Axios
- **빌드 도구**: Create React App (Webpack)
- **스타일링**: Emotion (CSS-in-JS)

## 🚀 빠른 시작

### 1. 시스템 요구사항
- **Node.js**: 16.0 이상
- **npm**: 8.0 이상 (또는 yarn 1.22 이상)
- **브라우저**: Chrome 90+, Firefox 88+, Safari 14+

### 2. 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm start

# 프로덕션 빌드
npm run build

# 테스트 실행
npm test
```

### 3. 환경 설정

React 앱은 API 서버(`http://localhost:8000`)와 통신합니다.
API 서버가 실행 중인지 확인하세요:

```bash
# API 서버 상태 확인
curl http://localhost:8000/health
```

## 📋 메뉴 구성

### 📊 대시보드 (`/dashboard`)
- **실시간 메트릭**: STT 세션, ERP 추출, 등록 현황
- **월별/일별 조회**: 기간별 데이터 분석
- **시스템 상태**: API 서버 연결 및 모델 상태
- **최근 활동**: 처리된 세션 및 추출 결과

### 📂 STT 처리 (`/stt`)
- **월별/일별 조회**: 날짜별 파일 필터링
- **Dual ListBox**: 직관적 파일 선택 인터페이스
- **처리 옵션**: 모델, 언어, 화자분리, ERP추출 설정
- **UX 개선**: ERP추출/ERP연동 옵션 연동 및 툴팁
- **일괄 처리**: 선택된 파일들의 순차적 STT 처리
- **실시간 진행**: 처리 상황 및 결과 모니터링

### 📈 STT 모니터링 (`/files`) - 구 파일 관리
- **실시간 통계**: Supabase 기반 처리 상태 데이터
- **월별/일별 조회**: 날짜별 상태 모니터링
- **전체 현황**: 파일 수, 성공률, 평균 처리 시간
- **디렉토리별 분석**: 폴더별 상세 통계

### 👥 세션 관리 (`/sessions`)
- **월별/일별 조회**: 날짜별 세션 필터링
- **필터 옵션**: 상태별, 모델별 세션 분류
- **상세 정보**: 세션별 전체 텍스트, 세그먼트, ERP 추출 결과
- **ERP 재추출**: 기존 세션에 대한 ERP 데이터 재추출
- **검색 기능**: 파일명 및 내용 기반 검색

### 🔍 결과 조회 (`/results`)
- **날짜별 조회**: 월별/일별 ERP 추출 결과
- **ERP 데이터**: 추출된 항목별 상세 정보
- **패턴 매칭 요약**: 고성능 요약 생성 결과 확인
- **등록 관리**: ERP 시스템 연동 테스트 및 상태 관리
- **결과 검토**: 추출 결과 수정 및 승인

### 📁 파일 관리 (`/status`) - 구 파일 상태
- **파일 업로드**: 드래그 앤 드롭 기반 음성 파일 업로드
- **월별/일별 조회**: 날짜별 파일 관리
- **파일 통계**: 전체, 루트, 일자별 파일 수 및 상태
- **지원 형식**: MP3, WAV, M4A, FLAC, AAC, OGG

### ⚙️ 설정 (`/settings`)
- **환경변수 상태**: 실시간 환경변수 설정 상태 모니터링
- **API 서버 정보**: 연결 상태 및 헬스 체크 정보
- **데이터베이스 스키마**: Supabase 테이블 정보
- **시스템 정보**: 모델 상태 및 캐시 정보

## 🏗 프로젝트 구조

```
stn-admin-react/
├── 📁 public/                 # 정적 파일
│   ├── index.html             # HTML 템플릿
│   ├── favicon.ico            # 파비콘
│   └── manifest.json          # PWA 매니페스트
│
├── 📁 src/                    # 소스 코드
│   ├── 📁 components/         # React 컴포넌트
│   │   ├── dashboard/         # 📊 대시보드 컴포넌트
│   │   │   └── Dashboard.tsx
│   │   ├── stt/               # 📂 STT 처리 컴포넌트
│   │   │   └── STTProcessPage.tsx
│   │   ├── files/             # 📈 STT 모니터링 컴포넌트
│   │   │   └── FileManagementPage.tsx
│   │   ├── sessions/          # 👥 세션 관리 컴포넌트
│   │   │   └── SessionsPage.tsx
│   │   ├── results/           # 🔍 결과 조회 컴포넌트
│   │   │   └── ResultsPage.tsx
│   │   ├── status/            # 📁 파일 관리 컴포넌트
│   │   │   └── FileStatusPage.tsx
│   │   ├── settings/          # ⚙️ 설정 컴포넌트
│   │   │   └── SettingsPage.tsx
│   │   └── layout/            # 공통 레이아웃
│   │       └── MainLayout.tsx
│   │
│   ├── 📁 services/           # API 서비스
│   │   └── api.ts             # FastAPI 백엔드 통신
│   │
│   ├── 📁 store/              # 상태 관리 (Zustand)
│   │   ├── fileStore.ts       # 파일 관련 상태
│   │   ├── sttStore.ts        # STT 처리 상태
│   │   └── systemStore.ts     # 시스템 상태
│   │
│   ├── 📁 types/              # TypeScript 타입 정의
│   │   └── api.ts             # API 인터페이스
│   │
│   ├── App.tsx                # 메인 앱 컴포넌트
│   ├── index.tsx              # React 진입점
│   └── index.css              # 전역 스타일
│
├── package.json               # 의존성 및 스크립트
├── tsconfig.json              # TypeScript 설정
└── README.md                  # 프로젝트 문서
```

## 🔧 주요 컴포넌트

### 🎛️ MainLayout.tsx
- **네비게이션**: 사이드바 기반 메뉴 시스템
- **반응형 디자인**: 모바일/데스크톱 최적화
- **Material-UI AppBar**: 상단 헤더 및 브랜딩

### 📂 STTProcessPage.tsx
- **Dual ListBox**: 파일 선택을 위한 좌우 리스트 인터페이스
- **처리 옵션**: FormControl 기반 설정 UI
- **UX 개선**: ERP추출/ERP연동 옵션 연동 및 툴팁
- **Progress Tracking**: LinearProgress로 처리 상황 표시
- **Batch Processing**: 선택된 파일들의 순차적 처리

### 📈 FileManagementPage.tsx
- **Real-time Stats**: Supabase 데이터 기반 실시간 통계
- **Card Layout**: Material-UI Card로 정보 구성
- **Date Filtering**: 월별/일별 조회 필터링

### 🔍 ResultsPage.tsx
- **Table View**: TableContainer로 ERP 추출 결과 표시
- **Accordion Details**: 상세 정보 확장/축소
- **Action Buttons**: ERP 등록 및 상태 관리
- **패턴 매칭 요약**: 고성능 요약 결과 표시

### 📁 FileStatusPage.tsx
- **파일 업로드**: 드래그 앤 드롭 기반 업로드
- **월별/일별 조회**: 날짜별 파일 관리
- **파일 통계**: 전체 현황 및 상태 모니터링

### ⚙️ SettingsPage.tsx
- **환경변수 상태**: 실시간 환경변수 모니터링
- **API 서버 정보**: 연결 상태 및 헬스 체크
- **데이터베이스 스키마**: Supabase 테이블 정보

## 🚀 최신 기능 상세

### 📤 파일 업로드 기능
```typescript
// 파일 업로드 API 호출
const result = await apiService.uploadFile(selectedFile, targetDate);
```

**특징:**
- 드래그 앤 드롭 지원
- 월별/일별 폴더 자동 생성
- 파일 형식 검증 (MP3, WAV, M4A, FLAC)
- 업로드 진행률 표시

### 🔄 ERP 재추출 기능
```typescript
// 기존 세션에 대한 ERP 재추출
const result = await apiService.extractERPForSession(sessionId);
```

**특징:**
- 기존 STT 세션 데이터 활용
- 패턴 매칭 기반 요약 자동 생성
- 실시간 진행률 표시
- 결과 즉시 반영

### 📊 패턴 매칭 요약
**구현된 패턴들:**
- **핵심 문장 추출**: 문제, 장애, 요청, 긴급 관련 키워드
- **요청 유형 분석**: 장애신고, 기술지원, 문의사항, 긴급요청
- **문제 상황 추출**: 장비-문제 조합 패턴 매칭
- **시간/장소 정보**: 시간대, 지역, 건물 정보 추출

**요약 형식:**
```
[요약] [요청기관] [AS 및 지원] 요청
[유형] [요청유형] | [분석된 요청유형]
[위치] [작업국소] | [추출된 시간/장소]
[문제] [추출된 문제 정보]
[핵심] [핵심 문장들]
```

### 🎯 UX 개선사항
- **옵션 연동**: ERP추출 비활성화 시 ERP연동 자동 비활성화
- **툴팁 추가**: 각 옵션에 대한 설명 툴팁
- **상태 표시**: 옵션 상태에 따른 시각적 피드백

## 🔌 백엔드 API 문서

### 🌐 API 서버 정보
- **Base URL**: `http://localhost:8000`
- **API 문서**: http://localhost:8000/docs (Swagger UI)
- **ReDoc 문서**: http://localhost:8000/redoc
- **헬스 체크**: http://localhost:8000/health

### 🎯 주요 API 엔드포인트

#### 🎙️ STT 처리 API
```typescript
// 파일 업로드를 통한 STT 처리
POST /api/stt-process
Content-Type: multipart/form-data
Parameters:
  - file: UploadFile (음성 파일)
  - model_name: string (base, small, medium, large)
  - language: string (ko, en, auto)
  - enable_diarization: boolean
  - extract_erp: boolean
  - save_to_db: boolean

// 디렉토리 파일을 통한 STT 처리
POST /api/stt-process-file
Parameters:
  - filename: string (src_record 내 파일명)
  - model_name: string
  - language: string
  - enable_diarization: boolean
  - extract_erp: boolean
  - save_to_db: boolean
```

#### 📁 파일 관리 API
```typescript
// 음성 파일 목록 조회
GET /api/audio-files
Response: {
  files: AudioFileInfo[],
  daily_files: Record<string, AudioFileInfo[]>
}

// 파일 업로드
POST /api/upload-file
Content-Type: multipart/form-data
Parameters:
  - file: UploadFile
  - target_date?: string (YYYY-MM-DD)
```

#### 👥 세션 관리 API
```typescript
// STT 세션 목록 조회
GET /api/sessions?limit=50&offset=0
Response: {
  sessions: STTSession[],
  total: number
}

// 특정 세션 상세 조회
GET /api/sessions/{session_id}
Response: {
  session: STTSession,
  extraction?: ERPExtraction
}

// ERP 재추출
POST /api/sessions/{session_id}/extract-erp
Response: {
  status: string,
  session_id: number,
  extraction_id: number,
  erp_data: ERPData
}
```

#### 🔍 ERP 추출 API
```typescript
// ERP 추출 결과 목록 조회
GET /api/extractions?limit=50&offset=0
Response: {
  extractions: ERPExtraction[],
  total: number
}

// ERP 등록 로그 조회
GET /api/register-logs?limit=50&offset=0
Response: {
  register_logs: RegisterLog[],
  total: number
}

// ERP 시스템 연동 테스트
POST /api/erp-sample-register
Body: ERPData
Response: {
  status: string,
  erp_id: string,
  response_data: any
}
```

#### 📊 통계 및 모니터링 API
```typescript
// 시스템 통계 조회
GET /api/statistics?date_filter=2025-01-19&month_filter=2025-01
Response: {
  statistics: {
    total_sessions: number,
    completed_sessions: number,
    failed_sessions: number,
    total_extractions: number,
    total_registers: number,
    success_registers: number,
    failed_registers: number,
    avg_processing_time: number,
    model_usage: Record<string, number>
  }
}

// 시스템 헬스 체크
GET /health
Response: {
  status: string,
  timestamp: string,
  models: {
    whisper: boolean,
    erp_extractor: boolean,
    supabase: boolean
  }
}

// 환경변수 상태 확인
GET /api/environment-status
Response: {
  status: string,
  environment_variables: Record<string, boolean>,
  timestamp: string
}
```

### 📝 데이터 타입 정의

#### STTSession
```typescript
interface STTSession {
  id: number;
  file_name: string;
  file_id: string;
  model_name: string;
  language?: string;
  transcript: string;
  original_transcript: string;
  segments: Segment[];
  original_segments: Segment[];
  processing_time: number;
  status: string;
  created_at: string;
  updated_at?: string;
}
```

#### ERPExtraction
```typescript
interface ERPExtraction {
  id: number;
  session_id: number;
  "AS 및 지원": string;
  "요청기관": string;
  "작업국소": string;
  "요청일": string;
  "요청시간": string;
  "요청자": string;
  "지원인원수": string;
  "지원요원": string;
  "장비명": string;
  "기종명": string;
  "A/S기간만료여부": string;
  "시스템명(고객사명)": string;
  "요청 사항": string;
  created_at: string;
  updated_at?: string;
}
```

#### AudioFileInfo
```typescript
interface AudioFileInfo {
  name: string;
  path: string;
  size: number;
  modified: string;
  extension: string;
  date_folder: string;
}
```

### 🔧 API 사용 예시

#### React에서 API 호출
```typescript
import { apiService } from '../services/api';

// STT 세션 목록 조회
const sessions = await apiService.getSessions(50, 0);

// ERP 추출 결과 조회
const extractions = await apiService.getExtractions(50, 0);

// 파일 업로드
const result = await apiService.uploadFile(file, '2025-01-19');

// ERP 재추출
const extraction = await apiService.extractERPForSession(73);
```

#### cURL 예시
```bash
# 헬스 체크
curl http://localhost:8000/health

# STT 세션 목록 조회
curl "http://localhost:8000/api/sessions?limit=10"

# ERP 추출 결과 조회
curl "http://localhost:8000/api/extractions?limit=10"

# 파일 업로드
curl -X POST "http://localhost:8000/api/upload-file" \
  -F "file=@audio.wav" \
  -F "target_date=2025-01-19"
```

### ⚠️ API 주의사항

1. **CORS 설정**: API 서버에서 React 앱 도메인 허용 필요
2. **파일 크기 제한**: 업로드 파일 크기 제한 확인
3. **타임아웃**: STT 처리 시간이 길 수 있으므로 적절한 타임아웃 설정
4. **에러 처리**: API 응답의 status 필드로 성공/실패 확인
5. **인증**: 현재는 인증 없이 사용, 향후 JWT 토큰 기반 인증 예정

## 🛠 개발 가이드

### 새 컴포넌트 추가

```typescript
// src/components/example/ExamplePage.tsx
import React from 'react';
import { Box, Typography } from '@mui/material';

const ExamplePage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4">
        새 페이지
      </Typography>
    </Box>
  );
};

export default ExamplePage;
```

### API 서비스 추가

```typescript
// src/services/api.ts
export const apiService = {
  // 새 API 메서드 추가
  getNewData: async (): Promise<NewDataType> => {
    const response = await axios.get(`${API_BASE_URL}/api/new-endpoint`);
    return response.data;
  },
};
```

### 상태 관리 (Zustand)

```typescript
// src/store/newStore.ts
import { create } from 'zustand';

interface NewStore {
  data: any[];
  loading: boolean;
  setData: (data: any[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useNewStore = create<NewStore>((set) => ({
  data: [],
  loading: false,
  setData: (data) => set({ data }),
  setLoading: (loading) => set({ loading }),
}));
```

## 🎨 스타일링 가이드

### Material-UI 테마 사용

```typescript
// 컴포넌트에서 테마 사용
import { useTheme } from '@mui/material/styles';

const theme = useTheme();
const primaryColor = theme.palette.primary.main;
```

### 반응형 디자인

```typescript
// sx prop을 사용한 반응형 스타일
<Box
  sx={{
    display: { xs: 'block', md: 'flex' },
    gap: { xs: 1, md: 2 },
    p: { xs: 2, md: 3 }
  }}
>
```

## 📊 성능 최적화

### 코드 분할
```typescript
// React.lazy를 사용한 컴포넌트 레이지 로딩
const STTProcessPage = React.lazy(() => import('./components/stt/STTProcessPage'));
```

### 메모이제이션
```typescript
// React.memo로 불필요한 리렌더링 방지
const MemoizedComponent = React.memo(({ data }) => {
  return <div>{data}</div>;
});
```

## 🛠️ 문제 해결

### 자주 발생하는 오류

#### 컴파일 오류
```bash
# TypeScript 타입 오류
Error: Property 'xyz' does not exist on type 'ABC'
해결: types/api.ts에서 인터페이스 정의 확인
```

#### API 연결 오류
```bash
# CORS 오류
Error: Access to fetch at 'http://localhost:8000' blocked by CORS
해결: API 서버의 CORS 설정 확인 (api_server.py)
```

#### 빌드 오류
```bash
# 메모리 부족
Error: JavaScript heap out of memory
해결: NODE_OPTIONS=--max_old_space_size=4096 npm run build
```

#### 파일 업로드 오류
```bash
# 파일 업로드 실패
Error: 파일 업로드에 실패했습니다
해결: API 서버의 파일 업로드 엔드포인트 확인
```

#### 환경변수 상태 오류
```bash
# 환경변수 상태 확인 실패
Error: 환경변수 상태를 확인할 수 없습니다
해결: API 서버의 환경변수 로딩 확인
```

## 📈 개발 로드맵

### ✅ 완료된 기능 (v1.1)
- [x] 기본 React + TypeScript 구조
- [x] Material-UI 통합
- [x] API 서비스 연동
- [x] 7개 메뉴 구현
- [x] 월별/일별 조회 기능
- [x] Dual ListBox STT 처리
- [x] 실시간 데이터 모니터링
- [x] 파일 업로드 기능
- [x] ERP 재추출 기능
- [x] 패턴 매칭 요약
- [x] UX 개선 (옵션 연동, 툴팁)
- [x] 환경변수 상태 모니터링

### 🔄 개발 예정 (v1.2)
- [ ] PWA (Progressive Web App) 지원
- [ ] 다크 모드 테마
- [ ] 국제화 (i18n) 지원
- [ ] 사용자 권한 관리
- [ ] 모바일 앱 (React Native)
- [ ] 오프라인 모드
- [ ] 실시간 알림 시스템
- [ ] 데이터 내보내기/가져오기

## 🔗 관련 링크

- **메인 프로젝트**: [STN_STT_POC](../README.md)
- **API 문서**: http://localhost:8000/docs
- **Material-UI**: https://mui.com/
- **React 공식 문서**: https://reactjs.org/
- **TypeScript 가이드**: https://www.typescriptlang.org/

---

**STN STT 관리자 UI v1.1** - 2025.01.19  
*React + TypeScript + Material-UI 현대적 웹 대시보드*

### 📝 변경 이력
- **v1.1 (2025.01.19)**: 파일 업로드, ERP 재추출, 패턴 매칭 요약, UX 개선, 환경변수 관리, 백엔드 API 문서 추가
- **v1.0 (2025.01.11)**: 초기 버전, 기본 기능 구현