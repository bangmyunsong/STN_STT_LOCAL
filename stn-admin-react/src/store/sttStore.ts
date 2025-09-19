import { create } from 'zustand';
import { STTSession, STTResponse, ERPExtraction, STTProcessOptions } from '../types/api';
import ApiService from '../services/api';

interface STTState {
  // 상태
  sessions: STTSession[];
  currentSession: STTSession | null;
  currentERPExtraction: ERPExtraction | null;
  isProcessing: boolean;
  isLoading: boolean;
  error: string | null;
  
  // 처리 진행률
  processingProgress: number;
  processingStatus: string;

  // 액션
  fetchSessions: (limit?: number, offset?: number) => Promise<void>;
  fetchSession: (sessionId: number) => Promise<void>;
  processFile: (file: File, options?: STTProcessOptions) => Promise<STTResponse>;
  processServerFile: (filename: string, options?: STTProcessOptions) => Promise<STTResponse>;
  extractERPForSession: (sessionId: number) => Promise<void>;
  clearCurrentSession: () => void;
  clearError: () => void;
  reset: () => void;
}

export const useSTTStore = create<STTState>((set, get) => ({
  // 초기 상태
  sessions: [],
  currentSession: null,
  currentERPExtraction: null,
  isProcessing: false,
  isLoading: false,
  error: null,
  processingProgress: 0,
  processingStatus: '',

  // STT 세션 목록 조회
  fetchSessions: async (limit = 50, offset = 0) => {
    set({ isLoading: true, error: null });
    try {
      const response = await ApiService.getSessions(limit, offset);
      set({ 
        sessions: response.sessions, 
        isLoading: false 
      });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || '세션 목록 조회 실패',
        isLoading: false 
      });
    }
  },

  // 특정 STT 세션 조회
  fetchSession: async (sessionId: number) => {
    set({ isLoading: true, error: null });
    try {
      const response = await ApiService.getSession(sessionId);
      set({ 
        currentSession: response.session,
        currentERPExtraction: response.erp_extraction || null,
        isLoading: false 
      });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || '세션 조회 실패',
        isLoading: false 
      });
    }
  },

  // 파일 업로드 및 STT 처리
  processFile: async (file: File, options: STTProcessOptions = {}) => {
    set({ 
      isProcessing: true, 
      error: null, 
      processingProgress: 0,
      processingStatus: '파일 업로드 중...'
    });

    try {
      // 진행률 시뮬레이션
      const progressInterval = setInterval(() => {
        const currentProgress = get().processingProgress;
        if (currentProgress < 90) {
          set({ 
            processingProgress: currentProgress + 10,
            processingStatus: currentProgress < 30 ? '파일 업로드 중...' :
                            currentProgress < 60 ? 'STT 처리 중...' :
                            'ERP 데이터 추출 중...'
          });
        }
      }, 1000);

      const response = await ApiService.processAudioFile(file, options);
      
      clearInterval(progressInterval);
      
      set({ 
        isProcessing: false,
        processingProgress: 100,
        processingStatus: '처리 완료'
      });

      // 세션 목록 새로고침
      get().fetchSessions();

      return response;
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'STT 처리 실패',
        isProcessing: false,
        processingProgress: 0,
        processingStatus: ''
      });
      throw error;
    }
  },

  // 서버 파일 STT 처리
  processServerFile: async (filename: string, options: STTProcessOptions = {}) => {
    set({ 
      isProcessing: true, 
      error: null, 
      processingProgress: 0,
      processingStatus: 'STT 처리 시작...'
    });

    try {
      // 진행률 시뮬레이션
      const progressInterval = setInterval(() => {
        const currentProgress = get().processingProgress;
        if (currentProgress < 90) {
          set({ 
            processingProgress: currentProgress + 15,
            processingStatus: currentProgress < 30 ? 'STT 처리 중...' :
                            currentProgress < 60 ? 'ERP 데이터 추출 중...' :
                            '결과 저장 중...'
          });
        }
      }, 1000);

      const response = await ApiService.processServerFile(filename, options);
      
      clearInterval(progressInterval);
      
      set({ 
        isProcessing: false,
        processingProgress: 100,
        processingStatus: '처리 완료'
      });

      // 세션 목록 새로고침
      get().fetchSessions();

      return response;
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'STT 처리 실패',
        isProcessing: false,
        processingProgress: 0,
        processingStatus: ''
      });
      throw error;
    }
  },

  // ERP 재추출
  extractERPForSession: async (sessionId: number) => {
    set({ isLoading: true, error: null });
    try {
      const response = await ApiService.extractERPForSession(sessionId);
      
      // 현재 세션 새로고침
      if (get().currentSession?.id === sessionId) {
        get().fetchSession(sessionId);
      }
      
      set({ isLoading: false });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || 'ERP 재추출 실패',
        isLoading: false 
      });
    }
  },

  // 현재 세션 클리어
  clearCurrentSession: () => set({ 
    currentSession: null, 
    currentERPExtraction: null 
  }),

  // 에러 클리어
  clearError: () => set({ error: null }),

  // 상태 초기화
  reset: () => set({
    sessions: [],
    currentSession: null,
    currentERPExtraction: null,
    isProcessing: false,
    isLoading: false,
    error: null,
    processingProgress: 0,
    processingStatus: '',
  }),
})); 