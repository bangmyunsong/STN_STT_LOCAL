import { create } from 'zustand';
import { AudioFileInfo, FileProcessingStatus, DirectoryProcessingSummary } from '../types/api';
import ApiService from '../services/api';

interface FileState {
  // 상태
  audioFiles: AudioFileInfo[];
  dailyFiles: Record<string, AudioFileInfo[]>;
  selectedFiles: string[];
  processingStatus: FileProcessingStatus[];
  directorySummary: DirectoryProcessingSummary[];
  
  // 필터링
  currentDirectory: string;
  searchQuery: string;
  
  // UI 상태
  isLoading: boolean;
  error: string | null;

  // 액션
  fetchAudioFiles: () => Promise<void>;
  fetchProcessingStatus: (directory?: string) => Promise<void>;
  fetchDirectorySummary: (folder?: string) => Promise<void>;
  checkFileProcessed: (filePath: string) => Promise<boolean>;
  
  // 파일 선택 관리
  selectFile: (filePath: string) => void;
  deselectFile: (filePath: string) => void;
  selectAll: () => void;
  clearSelection: () => void;
  
  // 필터링
  setCurrentDirectory: (directory: string) => void;
  setSearchQuery: (query: string) => void;
  
  // 유틸리티
  getFilteredFiles: () => AudioFileInfo[];
  getSelectedFilePaths: () => string[];
  
  clearError: () => void;
  reset: () => void;
}

export const useFileStore = create<FileState>((set, get) => ({
  // 초기 상태
  audioFiles: [],
  dailyFiles: {},
  selectedFiles: [],
  processingStatus: [],
  directorySummary: [],
  currentDirectory: '',
  searchQuery: '',
  isLoading: false,
  error: null,

  // 음성 파일 목록 조회
  fetchAudioFiles: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await ApiService.getAudioFiles();
      set({ 
        audioFiles: response.files,
        dailyFiles: response.daily_files,
        isLoading: false 
      });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || '파일 목록 조회 실패',
        isLoading: false 
      });
    }
  },

  // 파일 처리 상태 조회
  fetchProcessingStatus: async (directory?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await ApiService.getFileProcessingStatus(directory);
      set({ 
        processingStatus: response.files,
        isLoading: false 
      });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || '처리 상태 조회 실패',
        isLoading: false 
      });
    }
  },

  // 디렉토리별 처리 요약 조회
  fetchDirectorySummary: async (folder?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await ApiService.getDirectorySummary(folder);
      set({ 
        directorySummary: response.summary,
        isLoading: false 
      });
    } catch (error: any) {
      set({ 
        error: error.response?.data?.message || error.message || '디렉토리 요약 조회 실패',
        isLoading: false 
      });
    }
  },

  // 특정 파일 처리 여부 확인
  checkFileProcessed: async (filePath: string) => {
    try {
      const response = await ApiService.checkFileProcessed(filePath);
      return response.is_processed;
    } catch (error: any) {
      console.error('파일 처리 상태 확인 실패:', error);
      return false;
    }
  },

  // 파일 선택
  selectFile: (filePath: string) => {
    const selectedFiles = get().selectedFiles;
    if (!selectedFiles.includes(filePath)) {
      set({ selectedFiles: [...selectedFiles, filePath] });
    }
  },

  // 파일 선택 해제
  deselectFile: (filePath: string) => {
    const selectedFiles = get().selectedFiles;
    set({ selectedFiles: selectedFiles.filter(path => path !== filePath) });
  },

  // 전체 선택
  selectAll: () => {
    const allFiles = get().getFilteredFiles();
    const allPaths = allFiles.map(file => file.path);
    set({ selectedFiles: allPaths });
  },

  // 선택 해제
  clearSelection: () => {
    set({ selectedFiles: [] });
  },

  // 현재 디렉토리 설정
  setCurrentDirectory: (directory: string) => {
    set({ currentDirectory: directory, selectedFiles: [] });
  },

  // 검색 쿼리 설정
  setSearchQuery: (query: string) => {
    set({ searchQuery: query, selectedFiles: [] });
  },

  // 필터링된 파일 목록 반환
  getFilteredFiles: () => {
    const { audioFiles, dailyFiles, currentDirectory, searchQuery } = get();
    
    let allFiles: AudioFileInfo[] = [];
    
    // 현재 디렉토리 필터링
    if (currentDirectory === '' || currentDirectory === 'root') {
      // 루트 파일들
      allFiles = [...audioFiles];
    } else if (dailyFiles[currentDirectory]) {
      // 특정 날짜 폴더 파일들
      allFiles = [...dailyFiles[currentDirectory]];
    } else if (currentDirectory === 'all') {
      // 모든 파일들
      allFiles = [...audioFiles];
      Object.values(dailyFiles).forEach(files => {
        allFiles.push(...files);
      });
    }
    
    // 검색 쿼리 필터링
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      allFiles = allFiles.filter(file => 
        file.filename.toLowerCase().includes(query) ||
        file.path.toLowerCase().includes(query)
      );
    }
    
    return allFiles;
  },

  // 선택된 파일 경로 목록 반환
  getSelectedFilePaths: () => {
    return get().selectedFiles;
  },

  // 에러 클리어
  clearError: () => set({ error: null }),

  // 상태 초기화
  reset: () => set({
    audioFiles: [],
    dailyFiles: {},
    selectedFiles: [],
    processingStatus: [],
    directorySummary: [],
    currentDirectory: '',
    searchQuery: '',
    isLoading: false,
    error: null,
  }),
})); 