import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Stack,
  Chip,
  LinearProgress,
  Alert,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Collapse,
} from '@mui/material';
import {
  Refresh,
  ExpandMore,
  Folder,
  Search,
  Close,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material';
import { useFileStore } from '../../store/fileStore';
import { useSystemStore } from '../../store/systemStore';
import { DirectoryProcessingSummary, FileProcessingStatus } from '../../types/api';
import { apiService } from '../../services/api';

// 상태별 이모지 및 색상 매핑
const getStatusInfo = (status: string) => {
  const statusMap: Record<string, { emoji: string; color: 'success' | 'warning' | 'info' | 'error' | 'default'; label: string }> = {
    'completed': { emoji: '🟢', color: 'success', label: '완료' },
    'extracted': { emoji: '🟡', color: 'warning', label: '추출완료' },
    'stt_completed': { emoji: '🔵', color: 'info', label: 'STT완료' },
    'processing': { emoji: '🟠', color: 'warning', label: '처리중' },
    'pending': { emoji: '🔴', color: 'error', label: '미처리' },
    'failed': { emoji: '⚫', color: 'default', label: '실패' },
  };
  return statusMap[status] || { emoji: '⚫', color: 'default', label: status };
};

// 처리된 파일 상태 매핑
const getProcessedStatus = (fileStatus: FileProcessingStatus) => {
  if (!fileStatus) {
    return 'pending';
  }
  if (fileStatus.is_processed) {
    return fileStatus.status || 'completed';
  }
  return 'pending';
};

const FileManagementPage: React.FC = () => {
  // 상태 관리
  const [selectedDirectory, setSelectedDirectory] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('전체');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // 월별/일별 조회 상태
  const [selectedMonth, setSelectedMonth] = useState<string>('전체');
  const [selectedDay, setSelectedDay] = useState<string>('전체');
  const [dailyFolders, setDailyFolders] = useState<string[]>([]);
  
  // 데이터 상태
  const [directorySummary, setDirectorySummary] = useState<DirectoryProcessingSummary[]>([]);
  const [fileDetails, setFileDetails] = useState<FileProcessingStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 실제 Supabase 연동 데이터
  const [sttSessions, setSttSessions] = useState<any[]>([]);
  const [erpExtractions, setErpExtractions] = useState<any[]>([]);

  const {
    audioFiles,
    dailyFiles,
    fetchAudioFiles,
  } = useFileStore();

  const { fetchHealth } = useSystemStore();

  // 초기 데이터 로드
  useEffect(() => {
    loadInitialData();
  }, [fetchAudioFiles, fetchHealth]);

  // dailyFiles 변경 시 dailyFolders 업데이트
  useEffect(() => {
    const folders = Object.keys(dailyFiles || {}).sort().reverse();
    setDailyFolders(folders);
  }, [dailyFiles]);

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        fetchAudioFiles(),
        fetchHealth(),
        loadDirectorySummary(),
        loadSupabaseData(),
      ]);
    } catch (error) {
      setError('데이터 로드 실패');
      console.error('데이터 로드 오류:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // 월별 목록 생성
  const getAvailableMonths = () => {
    const months = new Set<string>();
    dailyFolders.forEach(folder => {
      // YYYY-MM-DD에서 YYYY-MM 추출
      const monthPart = folder.substring(0, 7); // "YYYY-MM"
      months.add(monthPart);
    });
    return Array.from(months).sort().reverse();
  };

  // 선택된 월의 일자 목록 생성
  const getAvailableDays = () => {
    if (selectedMonth === '전체') return [];
    
    const days = dailyFolders
      .filter(folder => folder.startsWith(selectedMonth))
      .map(folder => folder.substring(8)) // "DD" 부분만 추출
      .sort()
      .reverse();
    
    return days;
  };

  // 현재 선택된 날짜 문자열 생성
  const getCurrentSelectedDate = () => {
    if (selectedMonth === '전체') return '전체';
    if (selectedDay === '전체') return selectedMonth; // 월만 선택
    return `${selectedMonth}-${selectedDay}`; // 완전한 날짜
  };

  // 디렉토리별 처리 요약 로드
  const loadDirectorySummary = async () => {
    try {
      const response = await apiService.getDirectorySummary();
      setDirectorySummary(response.summary || []);
      setError(null); // 성공 시 에러 클리어
    } catch (error) {
      console.error('디렉토리 요약 로드 실패:', error);
      setError('API 서버와 연결할 수 없습니다. API 서버가 실행 중인지 확인해주세요.');
      setDirectorySummary([]); // 에러 시 빈 배열로 설정
    }
  };

  // 특정 디렉토리(날짜)의 파일 상세 정보 로드 (Supabase 데이터 기반)
  const loadFileDetails = async (directory: string) => {
    setIsLoading(true);
    try {
      // 선택된 디렉토리(날짜)에 해당하는 STT 세션들 필터링
      const directorySessions = sttSessions.filter(session => {
        const sessionDate = session.created_at ? session.created_at.split('T')[0] : '';
        return sessionDate === directory;
      });

      // FileProcessingStatus 형식으로 변환
      const fileDetails: FileProcessingStatus[] = directorySessions.map(session => {
        // 해당 세션의 ERP 추출 완료 여부 확인
        const hasErpExtraction = erpExtractions.some(ext => ext.session_id === session.id);
        const isProcessed = session.status === 'completed' && hasErpExtraction;

        return {
          file_path: session.file_name || session.file_path || `세션-${session.id}`,
          is_processed: isProcessed,
          session_id: session.id,
          processing_time: session.processing_time || 0,
          status: session.status || 'unknown',
          last_processed: session.updated_at || session.created_at || new Date().toISOString()
        };
      });

      // 최신 처리 순으로 정렬
      const sortedFiles = fileDetails.sort((a, b) => 
        new Date(b.last_processed || '').getTime() - new Date(a.last_processed || '').getTime()
      );

      setFileDetails(sortedFiles);
      setError(null);
    } catch (error) {
      setError('파일 상세 정보 로드 실패');
      console.error('파일 상세 정보 로드 오류:', error);
      setFileDetails([]); // 에러 시 빈 배열로 설정
    } finally {
      setIsLoading(false);
    }
  };



  // Supabase 데이터 로드
  const loadSupabaseData = async () => {
    try {
      const [sessionsData, extractionsData] = await Promise.all([
        apiService.getSessions(500),
        apiService.getExtractions(500)
      ]);
      
      setSttSessions(sessionsData.sessions || []);
      setErpExtractions(extractionsData.extractions || []);
      
      console.log(`STT 세션 ${sessionsData.sessions?.length || 0}개, ERP 추출 ${extractionsData.extractions?.length || 0}개 로드됨`);
    } catch (error) {
      console.error('Supabase 데이터 로드 실패:', error);
    }
  };

  // 데이터 새로고침
  const handleRefresh = async () => {
    await loadInitialData();
    await loadSupabaseData();
  };

  // 디렉토리 클릭 시 파일 목록 표시
  const handleDirectoryClick = (directory: string) => {
    if (selectedDirectory === directory) {
      setSelectedDirectory('');
      setFileDetails([]);
    } else {
      setSelectedDirectory(directory);
      loadFileDetails(directory);
    }
  };

  // 필터링된 파일 목록
  const getFilteredFiles = (): FileProcessingStatus[] => {
    let filtered = [...fileDetails];

    // 상태 필터
    if (statusFilter !== '전체') {
      filtered = filtered.filter(file => {
        const status = getProcessedStatus(file);
        return status === statusFilter;
      });
    }

    // 검색 필터
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(file => 
        file.file_path && file.file_path.toLowerCase().includes(query)
      );
    }

    return filtered;
  };

  // 실제 Supabase 데이터 기반 디렉토리별 요약 생성
  const getFilteredDirectorySummary = (): DirectoryProcessingSummary[] => {
    const currentDate = getCurrentSelectedDate();
    
    // 월별/일별 필터에 따른 데이터 필터링
    let filteredSessions = sttSessions;
    let filteredExtractions = erpExtractions;
    
    if (currentDate !== '전체') {
      let datePattern: string;
      if (selectedDay === '전체') {
        // 월 단위 필터링 (YYYY-MM)
        datePattern = selectedMonth;
      } else {
        // 특정 일자 필터링 (YYYY-MM-DD)
        datePattern = `${selectedMonth}-${selectedDay}`;
      }
      
      filteredSessions = sttSessions.filter(session => 
        session.created_at && session.created_at.startsWith(datePattern)
      );
      
      filteredExtractions = erpExtractions.filter(extraction => 
        extraction.created_at && extraction.created_at.startsWith(datePattern)
      );
    }

    // 날짜별로 그룹화하여 디렉토리 요약 생성
    const directoryMap = new Map<string, {
      totalFiles: number;
      processedFiles: number;
      sessions: any[];
      extractions: any[];
    }>();

    // STT 세션을 날짜별로 그룹화
    filteredSessions.forEach(session => {
      const date = session.created_at ? session.created_at.split('T')[0] : '알 수 없음';
      const directory = date;
      
      if (!directoryMap.has(directory)) {
        directoryMap.set(directory, {
          totalFiles: 0,
          processedFiles: 0,
          sessions: [],
          extractions: []
        });
      }
      
      const dirData = directoryMap.get(directory)!;
      dirData.totalFiles++;
      dirData.sessions.push(session);
      
      // ERP 추출도 완료된 경우 처리완료로 카운트
      const hasErpExtraction = filteredExtractions.some(ext => ext.session_id === session.id);
      if (session.status === 'completed' && hasErpExtraction) {
        dirData.processedFiles++;
      }
    });

    // DirectoryProcessingSummary 형식으로 변환
    const summaries: DirectoryProcessingSummary[] = Array.from(directoryMap.entries())
      .sort(([a], [b]) => b.localeCompare(a)) // 최신 순으로 정렬
      .map(([directory, data]) => {
        // 마지막 처리 시간 계산
        const lastProcessedSession = data.sessions
          .filter(s => s.status === 'completed')
          .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())[0];
        
        const lastProcessed = lastProcessedSession 
          ? new Date(lastProcessedSession.updated_at || lastProcessedSession.created_at).toISOString()
          : new Date().toISOString();

        // 평균 처리 시간 계산 (완료된 세션들의 처리 시간 평균)
        const completedSessions = data.sessions.filter(s => s.status === 'completed' && s.processing_time);
        const avgProcessingTime = completedSessions.length > 0 
          ? completedSessions.reduce((sum, s) => sum + (s.processing_time || 0), 0) / completedSessions.length
          : 0;

        return {
          directory,
          total_files: data.totalFiles,
          processed_files: data.processedFiles,
          unprocessed_files: data.totalFiles - data.processedFiles,
          success_rate: data.totalFiles > 0 ? (data.processedFiles / data.totalFiles) * 100 : 0,
          avg_processing_time: avgProcessingTime,
          last_processed: lastProcessed
        };
      });

    return summaries;
  };

  // 전체 통계 계산 (실제 Supabase 데이터 기준)
  const calculateOverallStats = () => {
    const currentDate = getCurrentSelectedDate();
    
    // 월별/일별 필터에 따른 데이터 필터링
    let filteredSessions = sttSessions;
    let filteredExtractions = erpExtractions;
    
    if (currentDate !== '전체') {
      let datePattern: string;
      if (selectedDay === '전체') {
        // 월 단위 필터링 (YYYY-MM)
        datePattern = selectedMonth;
      } else {
        // 특정 일자 필터링 (YYYY-MM-DD)
        datePattern = `${selectedMonth}-${selectedDay}`;
      }
      
      filteredSessions = sttSessions.filter(session => 
        session.created_at && session.created_at.startsWith(datePattern)
      );
      
      filteredExtractions = erpExtractions.filter(extraction => 
        extraction.created_at && extraction.created_at.startsWith(datePattern)
      );
    }
    
    // 전체 파일 수 (STT 세션 기준)
    const totalFiles = filteredSessions.length;
    
    // 처리 완료된 파일 수 (STT 완료 + ERP 추출 완료)
    const processedFiles = filteredSessions.filter(session => {
      const hasErpExtraction = filteredExtractions.some(ext => ext.session_id === session.id);
      return session.status === 'completed' && hasErpExtraction;
    }).length;
    
    // 완료율 계산
    const avgCompletion = totalFiles > 0 ? (processedFiles / totalFiles) * 100 : 0;
    
    // 고유 날짜 수 (디렉토리 수 대신)
    const uniqueDates = new Set(filteredSessions.map(session => 
      session.created_at ? session.created_at.split('T')[0] : ''
    ).filter(date => date));
    const totalDirectories = uniqueDates.size;

    return { totalFiles, processedFiles, avgCompletion, totalDirectories };
  };

  const overallStats = calculateOverallStats();

  return (
    <Box>
      {/* 타이틀과 버튼들 */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={3}>
        <Typography variant="h4" component="h1">
          {getCurrentSelectedDate() === '전체' 
            ? '📈 STT 모니터링 (전체 기간)' 
            : getCurrentSelectedDate().includes('-') && getCurrentSelectedDate() !== selectedMonth
            ? `📈 STT 모니터링 (${getCurrentSelectedDate()})`
            : `📈 STT 모니터링 (${getCurrentSelectedDate()} 월별)`
          }
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={isLoading}
          >
            새로고침
          </Button>
        </Stack>
      </Stack>

      {/* 월별/일별 조회 필터 */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
          <CalendarIcon /> 월별/일별 조회
        </Typography>
        <Box display="flex" gap={2} flexWrap="wrap">
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>조회 월</InputLabel>
            <Select
              value={selectedMonth}
              label="조회 월"
              onChange={(e) => {
                setSelectedMonth(e.target.value);
                setSelectedDay('전체'); // 월 변경시 일자 초기화
              }}
            >
              <MenuItem value="전체">전체</MenuItem>
              {getAvailableMonths().map(month => (
                <MenuItem key={month} value={month}>{month}</MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 120 }} disabled={selectedMonth === '전체'}>
            <InputLabel>조회 일</InputLabel>
            <Select
              value={selectedDay}
              label="조회 일"
              onChange={(e) => setSelectedDay(e.target.value)}
            >
              <MenuItem value="전체">전체</MenuItem>
              {getAvailableDays().map(day => (
                <MenuItem key={day} value={day}>{day}일</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}



      {/* 전체 요약 메트릭 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          📊 전체 처리 현황
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          STT 세션과 ERP 추출 완료 데이터를 기반으로 한 실시간 통계
        </Typography>
        
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} justifyContent="space-around">
          <Box textAlign="center">
            <Typography variant="h4" color="primary.main" fontWeight="bold">
              {overallStats.totalFiles}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              총 파일 수
            </Typography>
          </Box>
          
          <Box textAlign="center">
            <Typography variant="h4" color="success.main" fontWeight="bold">
              {overallStats.processedFiles}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              완전 처리된 파일 (STT+ERP)
            </Typography>
          </Box>
          
          <Box textAlign="center">
            <Typography variant="h4" color="info.main" fontWeight="bold">
              {overallStats.avgCompletion.toFixed(1)}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              전체 완료율
            </Typography>
          </Box>
          
          <Box textAlign="center">
            <Typography variant="h4" color="warning.main" fontWeight="bold">
              {overallStats.totalDirectories}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              처리 날짜 수
            </Typography>
          </Box>
        </Stack>
      </Paper>

      {/* 디렉토리별 상세 현황 */}
      <Typography variant="h5" gutterBottom>
        📂 디렉토리별 상세 현황
      </Typography>

      {isLoading ? (
        <Box sx={{ py: 4 }}>
          <LinearProgress />
          <Typography variant="body2" textAlign="center" sx={{ mt: 2 }}>
            데이터 로딩 중...
          </Typography>
        </Box>
      ) : getFilteredDirectorySummary().length > 0 ? (
        <Stack spacing={2}>
          {getFilteredDirectorySummary().map((summary, index) => (
            <Accordion 
              key={index}
              expanded={selectedDirectory === summary.directory}
              onChange={() => handleDirectoryClick(summary.directory)}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Stack direction="row" alignItems="center" spacing={2} sx={{ width: '100%' }}>
                  <Folder />
                  <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    {summary.directory}
                  </Typography>
                  <Chip 
                    label={`${(summary.success_rate || 0).toFixed(1)}%`}
                    color={(summary.success_rate || 0) >= 80 ? 'success' : 
                           (summary.success_rate || 0) >= 50 ? 'warning' : 'error'}
                    size="small"
                  />
                  <Typography variant="body2" color="text.secondary">
                    ({summary.processed_files || 0}/{summary.total_files || 0})
                  </Typography>
                </Stack>
              </AccordionSummary>
              
              <AccordionDetails>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} sx={{ mb: 3 }} justifyContent="space-around">
                  <Box textAlign="center">
                    <Typography variant="h5" color="primary.main">
                      {summary.total_files || 0}
                    </Typography>
                    <Typography variant="body2">총 파일</Typography>
                  </Box>
                  
                  <Box textAlign="center">
                    <Typography variant="h5" color="success.main">
                      {summary.processed_files || 0}
                    </Typography>
                    <Typography variant="body2">처리 완료</Typography>
                  </Box>
                  
                  <Box textAlign="center">
                    <Typography variant="h5" color="error.main">
                      {summary.unprocessed_files || 0}
                    </Typography>
                    <Typography variant="body2">미처리</Typography>
                  </Box>
                  
                  <Box textAlign="center">
                    <Typography variant="h5" color="info.main">
                      {summary.avg_processing_time ? `${summary.avg_processing_time.toFixed(1)}s` : 'N/A'}
                    </Typography>
                    <Typography variant="body2">평균 처리시간</Typography>
                  </Box>
                </Stack>

                {/* 진행률 바 */}
                <Box sx={{ mb: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                    <Typography variant="body2">처리율</Typography>
                    <Typography variant="body2">{(summary.success_rate || 0).toFixed(1)}%</Typography>
                  </Stack>
                  <LinearProgress 
                    variant="determinate" 
                    value={summary.success_rate || 0} 
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>

                {/* 최근 처리 정보 */}
                {summary.last_processed && (
                  <Typography variant="caption" color="text.secondary">
                    최근 처리: {summary.last_processed.slice(0, 19).replace('T', ' ')}
                  </Typography>
                )}

                {/* 파일 목록 */}
                <Collapse in={selectedDirectory === summary.directory}>
                  <Box sx={{ mt: 3 }}>
                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                      <Typography variant="h6">
                        📋 {summary.directory} 파일 목록
                      </Typography>
                      
                      <Button
                        size="small"
                        startIcon={<Close />}
                        onClick={() => setSelectedDirectory('')}
                      >
                        닫기
                      </Button>
                    </Stack>

                    {/* 필터링 옵션 */}
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
                      <FormControl sx={{ minWidth: 150 }}>
                        <InputLabel>처리 상태 필터</InputLabel>
                        <Select
                          value={statusFilter}
                          label="처리 상태 필터"
                          onChange={(e) => setStatusFilter(e.target.value)}
                        >
                          <MenuItem value="전체">전체</MenuItem>
                          <MenuItem value="completed">완료</MenuItem>
                          <MenuItem value="processing">처리중</MenuItem>
                          <MenuItem value="pending">미처리</MenuItem>
                        </Select>
                      </FormControl>

                      <TextField
                        label="파일명 검색"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        InputProps={{
                          startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
                        }}
                        sx={{ flexGrow: 1 }}
                      />

                      <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        onClick={() => loadFileDetails(summary.directory)}
                      >
                        새로고침
                      </Button>
                    </Stack>

                    {/* 파일 목록 테이블 */}
                    <TableContainer component={Paper}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>파일명</TableCell>
                            <TableCell align="center">상태</TableCell>
                            <TableCell align="center">처리시간</TableCell>
                            <TableCell align="center">최종 처리일</TableCell>
                            <TableCell align="center">세션 ID</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {getFilteredFiles().map((file, fileIndex) => {
                            const status = getProcessedStatus(file);
                            const statusInfo = getStatusInfo(status);
                            const fileName = file.file_path ? 
                              (file.file_path.split('/').pop() || file.file_path.split('\\').pop() || file.file_path) : 
                              'Unknown';
                            
                            return (
                              <TableRow key={fileIndex}>
                                <TableCell>
                                  <Typography variant="body2">
                                    {fileName}
                                  </Typography>
                                </TableCell>
                                <TableCell align="center">
                                  <Chip
                                    label={`${statusInfo.emoji} ${statusInfo.label}`}
                                    color={statusInfo.color}
                                    size="small"
                                  />
                                </TableCell>
                                <TableCell align="center">
                                  <Typography variant="body2">
                                    {file && file.processing_time && typeof file.processing_time === 'number' ? 
                                      `${file.processing_time.toFixed(2)}초` : 
                                      'N/A'
                                    }
                                  </Typography>
                                </TableCell>
                                <TableCell align="center">
                                  <Typography variant="caption">
                                    {file && file.last_processed ? 
                                      file.last_processed.slice(0, 19).replace('T', ' ') : 
                                      'N/A'
                                    }
                                  </Typography>
                                </TableCell>
                                <TableCell align="center">
                                  <Typography variant="body2">
                                    {file && file.session_id ? file.session_id : 'N/A'}
                                  </Typography>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    {getFilteredFiles().length === 0 && (
                      <Alert severity="info" sx={{ mt: 2 }}>
                        필터 조건에 맞는 파일이 없습니다.
                      </Alert>
                    )}
                  </Box>
                </Collapse>
              </AccordionDetails>
            </Accordion>
          ))}
        </Stack>
      ) : (
        <Alert severity="info">
          {getCurrentSelectedDate() === '전체' 
            ? '아직 처리된 파일이 없습니다.' 
            : `${getCurrentSelectedDate()}에 해당하는 처리된 파일이 없습니다.`
          }
        </Alert>
      )}
    </Box>
  );
};

export default FileManagementPage; 