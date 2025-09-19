import axios, { AxiosResponse } from 'axios';
import {
  STTResponse,
  ERPRegisterResponse,
  STTSession,
  ERPExtraction,
  AudioFilesResponse,
  SystemStatistics,
  ERPRegisterLog,
  DirectoryProcessingSummary,
  FileProcessingStatus,
  HealthCheckResponse,
  STTProcessOptions,
  ERPData,
  ApiResponse
} from '../types/api';

// API 기본 설정
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5분 타임아웃 (STT 처리 시간 고려)
  headers: {
    'Content-Type': 'application/json',
  },
});

// 응답 인터셉터 (에러 처리)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API 에러:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// API 서비스 클래스
export class ApiService {
  // 헬스 체크
  static async healthCheck(): Promise<HealthCheckResponse> {
    const response: AxiosResponse<HealthCheckResponse> = await apiClient.get('/health');
    return response.data;
  }

  // 환경변수 설정 상태 확인
  static async getEnvironmentStatus(): Promise<{
    status: string;
    environment_variables: Record<string, boolean>;
    timestamp: string;
  }> {
    const response = await apiClient.get('/api/environment-status');
    return response.data;
  }

  // STT 처리 (파일 업로드)
  static async processAudioFile(
    file: File,
    options: STTProcessOptions = {}
  ): Promise<STTResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (options.model_name) formData.append('model_name', options.model_name);
    if (options.language) formData.append('language', options.language);
    if (options.enable_diarization !== undefined) 
      formData.append('enable_diarization', options.enable_diarization.toString());
    if (options.extract_erp !== undefined) 
      formData.append('extract_erp', options.extract_erp.toString());
    if (options.save_to_db !== undefined) 
      formData.append('save_to_db', options.save_to_db.toString());

    const response: AxiosResponse<STTResponse> = await apiClient.post(
      '/api/stt-process',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  // STT 처리 (서버 파일)
  static async processServerFile(
    filename: string,
    options: STTProcessOptions = {}
  ): Promise<STTResponse> {
    const params = new URLSearchParams({ filename });
    
    if (options.model_name) params.append('model_name', options.model_name);
    if (options.language) params.append('language', options.language);
    if (options.enable_diarization !== undefined) 
      params.append('enable_diarization', options.enable_diarization.toString());
    if (options.extract_erp !== undefined) 
      params.append('extract_erp', options.extract_erp.toString());
    if (options.save_to_db !== undefined) 
      params.append('save_to_db', options.save_to_db.toString());

    const response: AxiosResponse<STTResponse> = await apiClient.post(
      `/api/stt-process-file?${params.toString()}`
    );
    return response.data;
  }

  // 텍스트에서 ERP 추출
  static async extractERPFromText(conversationText: string): Promise<{
    status: string;
    erp_data: ERPData;
    message: string;
  }> {
    const response = await apiClient.post('/api/extract-erp', {
      conversation_text: conversationText,
    });
    return response.data;
  }

  // ERP 등록
  static async registerERP(
    erpData: ERPData,
    extractionId?: number
  ): Promise<ERPRegisterResponse> {
    const params = extractionId ? `?extraction_id=${extractionId}` : '';
    const response: AxiosResponse<ERPRegisterResponse> = await apiClient.post(
      `/api/erp-sample-register${params}`,
      erpData
    );
    return response.data;
  }

  // STT 세션 목록 조회
  static async getSessions(limit = 50, offset = 0): Promise<{
    status: string;
    sessions: STTSession[];
    total: number;
  }> {
    const response = await apiClient.get('/api/sessions', {
      params: { limit, offset }
    });
    return response.data;
  }

  // 특정 STT 세션 조회
  static async getSession(sessionId: number): Promise<{
    status: string;
    session: STTSession;
    erp_extraction?: ERPExtraction;
  }> {
    const response = await apiClient.get(`/api/sessions/${sessionId}`);
    return response.data;
  }

  // 세션에 대한 ERP 재추출
  static async extractERPForSession(sessionId: number): Promise<{
    status: string;
    message: string;
    session_id: number;
    extraction_id: number;
    erp_data: ERPData;
  }> {
    const response = await apiClient.post(`/api/sessions/${sessionId}/extract-erp`);
    return response.data;
  }

  // ERP 추출 결과 목록 조회
  static async getExtractions(limit = 50, offset = 0): Promise<{
    status: string;
    extractions: ERPExtraction[];
    total: number;
  }> {
    const response = await apiClient.get('/api/extractions', {
      params: { limit, offset }
    });
    return response.data;
  }

  // 시스템 통계 조회
  static async getStatistics(options?: { 
    dateFilter?: string; 
    monthFilter?: string 
  }): Promise<{
    status: string;
    statistics: SystemStatistics;
  }> {
    const params: any = {};
    if (options?.dateFilter) params.date_filter = options.dateFilter;
    if (options?.monthFilter) params.month_filter = options.monthFilter;
    
    const response = await apiClient.get('/api/statistics', { params });
    return response.data;
  }

  // 음성 파일 목록 조회
  static async getAudioFiles(): Promise<AudioFilesResponse> {
    const response: AxiosResponse<AudioFilesResponse> = await apiClient.get('/api/audio-files');
    return response.data;
  }

  // ERP 등록 로그 조회
  static async getRegisterLogs(limit = 50, offset = 0): Promise<{
    status: string;
    register_logs: ERPRegisterLog[];
    total: number;
  }> {
    const response = await apiClient.get('/api/register-logs', {
      params: { limit, offset }
    });
    return response.data;
  }

  // 디렉토리별 처리 요약 조회
  static async getDirectorySummary(folder?: string): Promise<{
    status: string;
    summary: DirectoryProcessingSummary[];
    total_directories: number;
    folder_filter?: string;
  }> {
    const params = folder ? { folder } : {};
    const response = await apiClient.get('/api/directory-summary', { params });
    return response.data;
  }

  // 파일 처리 상태 조회
  static async getFileProcessingStatus(
    directory?: string,
    limit = 200
  ): Promise<{
    status: string;
    files: FileProcessingStatus[];
    total: number;
    directory: string;
  }> {
    const params: any = { limit };
    if (directory) params.directory = directory;
    
    const response = await apiClient.get('/api/file-processing-status', { params });
    return response.data;
  }

  // 특정 파일 처리 여부 확인
  static async checkFileProcessed(filePath: string): Promise<{
    status: string;
    file_path: string;
    is_processed: boolean;
    session_id?: number;
    processing_time?: number;
    status_detail?: string;
    last_processed?: string;
  }> {
    const response = await apiClient.get('/api/check-file-processed', {
      params: { file_path: filePath }
    });
    return response.data;
  }

  // 향상된 처리 요약 조회
  static async getProcessingSummaryEnhanced(): Promise<{
    status: string;
    overall_summary: any;
    directory_summaries: DirectoryProcessingSummary[];
    recent_activity: any[];
  }> {
    const response = await apiClient.get('/api/processing-summary-enhanced');
    return response.data;
  }

  // 디렉토리 뷰 업데이트
  static async updateDirectoryView(): Promise<{
    status: string;
    message: string;
  }> {
    const response = await apiClient.post('/api/update-directory-view');
    return response.data;
  }

  // 파일 업로드
  static async uploadFile(file: File, targetDate?: string): Promise<{
    status: string;
    message: string;
    file_path: string;
    target_date: string;
    file_size: number;
    timestamp: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    if (targetDate) {
      formData.append('target_date', targetDate);
    }

    const response = await apiClient.post('/api/upload-file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
}

// static 메서드만 사용하는 클래스이므로 직접 export
export const apiService = ApiService;
export default ApiService; 