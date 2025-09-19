import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Pending as PendingIcon,
  Cancel as CancelIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  Psychology as PsychologyIcon,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material';
import { apiService } from '../../services/api';

interface Session {
  id: number;
  file_name: string;
  file_id: string;
  model_name: string;
  language?: string;
  status: string;
  transcript?: string;
  segments?: any;
  processing_time?: number;
  created_at: string;
  updated_at?: string;
}

const SessionsPage: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [dailyFolders, setDailyFolders] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string>('전체');
  const [selectedDay, setSelectedDay] = useState<string>('전체');
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('전체');
  const [modelFilter, setModelFilter] = useState('전체');
  const [extracting, setExtracting] = useState<number | null>(null);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sessionsResponse, audioFilesData] = await Promise.all([
        apiService.getSessions(100),
        apiService.getAudioFiles(),
      ]);
      setSessions(sessionsResponse.sessions || []);
      
      // dailyFolders 설정
      if (audioFilesData && audioFilesData.daily_files) {
        setDailyFolders(Object.keys(audioFilesData.daily_files));
      }
    } catch (error) {
      console.error('데이터 로드 실패:', error);
      showSnackbar('데이터 로드에 실패했습니다.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleSnackbarClose = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  const handleExtractERP = async (sessionId: number) => {
    try {
      setExtracting(sessionId);
      const response = await apiService.extractERPForSession(sessionId);
      
      if (response.status === 'success') {
        showSnackbar('ERP 재추출이 완료되었습니다.', 'success');
        await loadData();
      } else {
        throw new Error(response.message || 'ERP 재추출 실패');
      }
    } catch (error: any) {
      console.error('ERP 재추출 실패:', error);
      showSnackbar(`ERP 재추출 실패: ${error.message}`, 'error');
    } finally {
      setExtracting(null);
    }
  };

  const handleViewSession = (session: Session) => {
    setSelectedSession(session);
  };

  const handleCloseSession = () => {
    setSelectedSession(null);
  };

  // 월별/일별 필터링된 세션
  const getDateFilteredSessions = () => {
    const currentDate = getCurrentSelectedDate();
    
    if (currentDate === '전체') {
      return sessions;
    }

    // 필터링할 날짜 패턴 생성
    let datePattern: string;
    if (selectedDay === '전체') {
      // 월 단위 필터링
      datePattern = selectedMonth;
    } else {
      // 특정 일자 필터링
      datePattern = `${selectedMonth}-${selectedDay}`;
    }

    // 선택된 날짜/월의 세션들 필터링
    return sessions.filter(session => {
      if (session.file_name.includes('/')) {
        const [folderName] = session.file_name.split('/');
        return folderName.startsWith(datePattern);
      }
      return false;
    });
  };

  // 현재 선택된 날짜 문자열 생성
  const getCurrentSelectedDate = () => {
    if (selectedMonth === '전체') return '전체';
    if (selectedDay === '전체') return selectedMonth; // 월만 선택
    return `${selectedMonth}-${selectedDay}`; // 완전한 날짜
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

  // 필터링 로직 (월별/일별 + 상태/모델)
  const filteredSessions = getDateFilteredSessions().filter(session => {
    if (statusFilter !== '전체' && session.status !== statusFilter) {
      return false;
    }
    if (modelFilter !== '전체' && session.model_name !== modelFilter) {
      return false;
    }
    return true;
  });

  // 모델 목록 생성
  const modelOptions = ['전체', ...Array.from(new Set(sessions.map(s => s.model_name)))];

  // 타이틀 텍스트 생성
  const getTitleText = () => {
    const currentDate = getCurrentSelectedDate();
    if (currentDate === '전체') {
      return '📊 STT 세션 관리 (전체 기간)';
    } else if (selectedDay === '전체') {
      return `📊 STT 세션 관리 (${selectedMonth} 월별)`;
    } else {
      return `📊 STT 세션 관리 (${selectedMonth}-${selectedDay})`;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!sessions.length) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          {getTitleText()}
        </Typography>
        <Alert severity="info">
          아직 처리된 세션이 없습니다.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          {getTitleText()}
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadData}
          disabled={loading}
        >
          새로고침
        </Button>
      </Box>

      {/* 월별/일별 조회 & 필터 옵션 */}
      <Box display="flex" gap={2} mb={3}>
        {/* 월별/일별 조회 (50%) */}
        <Paper sx={{ p: 2, flex: 1 }}>
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

        {/* 필터 옵션 (50%) */}
        <Paper sx={{ p: 2, flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            🔧 필터 옵션
          </Typography>
          <Box display="flex" gap={2} flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>STT 상태</InputLabel>
              <Select
                value={statusFilter}
                label="STT 상태"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="전체">전체</MenuItem>
                <MenuItem value="completed">완료</MenuItem>
                <MenuItem value="processing">처리 중</MenuItem>
                <MenuItem value="failed">실패</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>모델</InputLabel>
              <Select
                value={modelFilter}
                label="모델"
                onChange={(e) => setModelFilter(e.target.value)}
              >
                {modelOptions.map(model => (
                  <MenuItem key={model} value={model}>{model}</MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={loadData}
              disabled={loading}
              size="small"
              sx={{ ml: 2 }}
            >
              새로고침
            </Button>
          </Box>
        </Paper>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6">
          📋 총 {sessions.length}개 세션 (필터링: {filteredSessions.length}개)
        </Typography>
      </Paper>

      {/* 세션 테이블 */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>세션 ID</TableCell>
              <TableCell>파일명</TableCell>
              <TableCell>모델</TableCell>
              <TableCell>상태</TableCell>
              <TableCell>처리시간</TableCell>
              <TableCell>생성일</TableCell>
              <TableCell>작업</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredSessions.map((session) => {
              const isExtracting = extracting === session.id;
              
              return (
                <TableRow key={session.id}>
                  <TableCell>{session.id}</TableCell>
                  <TableCell>{session.file_name}</TableCell>
                  <TableCell>{session.model_name}</TableCell>
                  <TableCell>
                    <Chip 
                      label={session.status} 
                      color={session.status === 'completed' ? 'success' : 'default'} 
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {session.processing_time ? `${session.processing_time.toFixed(2)}초` : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {new Date(session.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={1}>
                      <Tooltip title="세션 상세 보기">
                        <IconButton
                          color="primary"
                          size="small"
                          onClick={() => handleViewSession(session)}
                        >
                          <VisibilityIcon />
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="ERP 재추출">
                        <span>
                          <IconButton
                            color="secondary"
                            size="small"
                            onClick={() => handleExtractERP(session.id)}
                            disabled={isExtracting || session.status !== 'completed'}
                          >
                            {isExtracting ? <CircularProgress size={16} /> : <PsychologyIcon />}
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 세션 상세 정보 다이얼로그 */}
      <Dialog
        open={!!selectedSession}
        onClose={handleCloseSession}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          세션 상세 정보 (ID: {selectedSession?.id})
        </DialogTitle>
        <DialogContent>
          {selectedSession && (
            <Box>
              <Typography variant="h6" gutterBottom>기본 정보</Typography>
              <Box sx={{ mb: 2 }}>
                <Typography><strong>파일명:</strong> {selectedSession.file_name}</Typography>
                <Typography><strong>파일 ID:</strong> {selectedSession.file_id}</Typography>
                <Typography><strong>모델:</strong> {selectedSession.model_name}</Typography>
                <Typography><strong>상태:</strong> {selectedSession.status}</Typography>
                <Typography><strong>처리시간:</strong> {selectedSession.processing_time ? `${selectedSession.processing_time.toFixed(2)}초` : 'N/A'}</Typography>
                <Typography><strong>생성일:</strong> {new Date(selectedSession.created_at).toLocaleString()}</Typography>
              </Box>

              {selectedSession.transcript && (
                <Box>
                  <Typography variant="h6" gutterBottom>전사 결과</Typography>
                  <Paper sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 200, overflow: 'auto' }}>
                    <Typography variant="body2">
                      {selectedSession.transcript}
                    </Typography>
                  </Paper>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseSession}>닫기</Button>
        </DialogActions>
      </Dialog>

      {/* 스낵바 알림 */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SessionsPage; 