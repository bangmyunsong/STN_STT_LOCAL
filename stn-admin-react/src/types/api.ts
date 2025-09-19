// API 응답 타입 정의

// ERP 데이터 모델
export interface ERPData {
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
}

// STT 세그먼트 데이터
export interface STTSegment {
  id: number;
  text: string;
  start: number;
  end: number;
  speaker: string;
}

// STT 처리 응답
export interface STTResponse {
  status: string;
  transcript: string;
  segments: STTSegment[];
  erp_data?: ERPData;
  processing_time: number;
  file_id: string;
  session_id?: number;
  extraction_id?: number;
}

// ERP 등록 응답
export interface ERPRegisterResponse {
  status: string;
  erp_id: string;
  message?: string;
}

// STT 세션 데이터
export interface STTSession {
  id: number;
  file_name: string;
  file_id: string;
  model_name: string;
  language?: string;
  transcript?: string;
  segments?: STTSegment[] | string;
  processing_time?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

// ERP 추출 결과
export interface ERPExtraction {
  id: number;
  session_id: number;
  erp_data: ERPData;
  created_at: string;
  updated_at: string;
}

// 음성 파일 정보
export interface AudioFileInfo {
  filename: string;
  path: string;
  size: number;
  modified: string;
  extension: string;
  location: string;
}

// 음성 파일 목록 응답
export interface AudioFilesResponse {
  status: string;
  message: string;
  files: AudioFileInfo[];
  daily_files: Record<string, AudioFileInfo[]>;
  directory: string;
  today_folder: string;
}

// 시스템 통계
export interface SystemStatistics {
  total_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  total_extractions: number;
  total_registers: number;
  success_registers: number;
  failed_registers: number;
  avg_processing_time: number;
}

// ERP 등록 로그
export interface ERPRegisterLog {
  id: number;
  extraction_id: number;
  erp_id: string;
  status: string;
  response_data: any;
  created_at: string;
}

// 디렉토리 처리 요약
export interface DirectoryProcessingSummary {
  directory: string;
  total_files: number;
  processed_files: number;
  unprocessed_files: number;
  success_rate: number;
  avg_processing_time: number;
  last_processed: string;
}

// 파일 처리 상태
export interface FileProcessingStatus {
  file_path: string;
  is_processed: boolean;
  session_id?: number;
  processing_time?: number;
  status?: string;
  last_processed?: string;
}

// API 공통 응답 타입
export interface ApiResponse<T = any> {
  status: string;
  message?: string;
  data?: T;
}

// API 에러 응답
export interface ApiError {
  detail: string | any[];
  message?: string;
  debug_info?: any;
}

// STT 처리 요청 옵션
export interface STTProcessOptions {
  model_name?: string;
  language?: string;
  enable_diarization?: boolean;
  extract_erp?: boolean;
  save_to_db?: boolean;
}

// 헬스 체크 응답
export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  models: {
    whisper: boolean;
    erp_extractor: boolean;
    supabase: boolean;
  };
} 