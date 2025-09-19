import { create } from 'zustand';
import { HealthCheckResponse, SystemStatistics } from '../types/api';
import { apiService } from '../services/api';

interface SystemState {
  // 상태
  health: HealthCheckResponse | null;
  statistics: SystemStatistics | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;

  // 액션
  fetchHealth: () => Promise<void>;
  fetchStatistics: (options?: { dateFilter?: string; monthFilter?: string }) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useSystemStore = create<SystemState>((set, get) => ({
  // 초기 상태
  health: null,
  statistics: null,
  isLoading: false,
  error: null,
  lastUpdated: null,

  // 헬스 체크
  fetchHealth: async () => {
    set({ isLoading: true, error: null });
    try {
      console.log('🔍 API 헬스 체크 시작...');
      const health = await apiService.healthCheck();
      console.log('✅ API 헬스 체크 성공:', health);
      set({ 
        health, 
        isLoading: false, 
        lastUpdated: new Date() 
      });
    } catch (error: any) {
      console.error('❌ API 헬스 체크 실패:', error);
      console.error('❌ 오류 상세:', {
        message: error.message,
        response: error.response,
        status: error.response?.status,
        data: error.response?.data
      });
      
      let errorMessage = '헬스 체크 실패';
      if (error.code === 'ECONNREFUSED') {
        errorMessage = 'API 서버에 연결할 수 없습니다 (포트 8000 확인)';
      } else if (error.response?.status) {
        errorMessage = `API 서버 오류 (${error.response.status}): ${error.response.data?.detail || error.message}`;
      } else {
        errorMessage = error.message || '알 수 없는 오류';
      }
      
      set({ 
        error: errorMessage,
        isLoading: false 
      });
    }
  },

  // 시스템 통계 조회
  fetchStatistics: async (options?: { dateFilter?: string; monthFilter?: string }) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiService.getStatistics(options);
      set({ 
        statistics: response.statistics, 
        isLoading: false,
        lastUpdated: new Date()
      });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || '통계 조회 실패',
        isLoading: false 
      });
    }
  },

  // 에러 클리어
  clearError: () => set({ error: null }),

  // 상태 초기화
  reset: () => set({
    health: null,
    statistics: null,
    isLoading: false,
    error: null,
    lastUpdated: null,
  }),
})); 