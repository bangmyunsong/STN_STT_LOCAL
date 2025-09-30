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
  Card,
  CardContent,
  Snackbar,
  Stack,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  AudioFile as AudioFileIcon,
  CloudUpload,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material';
import { apiService } from '../../services/api';

interface AudioFile {
  filename: string;
  path: string;
  size: number;
  modified: string;
  extension: string;
  location: string;
}

// 파일 크기를 읽기 쉬운 형태로 변환
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const FileStatusPage: React.FC = () => {
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [dailyFiles, setDailyFiles] = useState<Record<string, AudioFile[]>>({});
  const [dailyFolders, setDailyFolders] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string>('전체');
  const [selectedDay, setSelectedDay] = useState<string>('전체');
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
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
      
      // 오디오 파일 목록 조회
      const audioResponse = await apiService.getAudioFiles();
      setAudioFiles(audioResponse.files || []);
      setDailyFiles(audioResponse.daily_files || {});
      
      // 일자별 폴더 목록 추출
      const folders = Object.keys(audioResponse.daily_files || {}).sort().reverse();
      setDailyFolders(folders);
      
    } catch (error) {
      console.error('데이터 로드 실패:', error);
      showSnackbar('데이터 로드에 실패했습니다.', 'error');
    } finally {
      setLoading(false);
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
    if (selectedDay === '전체') {
      // 월만 선택된 경우 오늘 날짜 사용
      const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
      return today;
    }
    return `${selectedMonth}-${selectedDay}`; // 완전한 날짜
  };
  
  // 타이틀 텍스트 생성
  const getTitleText = () => {
    const currentDate = getCurrentSelectedDate();
    if (currentDate === '전체') {
      return '📁 파일 관리 (전체 기간)';
    } else if (selectedDay === '전체') {
      return `📁 파일 관리 (${selectedMonth} 월별)`;
    } else {
      return `📁 파일 관리 (${selectedMonth}-${selectedDay})`;
    }
  };

  // 날짜 필터링된 파일 목록 생성
  const getFilteredFilesByDate = () => {
    const currentDate = getCurrentSelectedDate();
    
    if (currentDate === '전체') {
      // 전체 기간: 모든 파일
      const allFiles = [...audioFiles];
      Object.values(dailyFiles).forEach(files => {
        allFiles.push(...files);
      });
      return allFiles;
    }
    
    // 날짜 필터링 적용
    const allFiles = [...audioFiles]; // 루트 파일들은 항상 포함
    
    if (selectedDay === '전체') {
      // 월별 필터링
      Object.keys(dailyFiles).forEach(folder => {
        if (folder.startsWith(selectedMonth)) {
          allFiles.push(...dailyFiles[folder]);
        }
      });
    } else {
      // 특정 일자 필터링
      const targetDate = `${selectedMonth}-${selectedDay}`;
      if (dailyFiles[targetDate]) {
        allFiles.push(...dailyFiles[targetDate]);
      }
    }
    
    return allFiles;
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleSnackbarClose = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleFileSubmit = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      
      // 파일 업로드 API 호출
      const result = await apiService.uploadFile(selectedFile, getCurrentSelectedDate() !== '전체' ? getCurrentSelectedDate() : undefined);
      
      showSnackbar(`파일 업로드 완료: ${selectedFile.name}`, 'success');
      setSelectedFile(null);
      
      // 파일 목록 새로고침
      await loadData();
      
    } catch (error) {
      console.error('파일 업로드 실패:', error);
      showSnackbar('파일 업로드에 실패했습니다.', 'error');
    } finally {
      setUploading(false);
    }
  };

  const getFilteredFiles = () => {
    // 날짜 필터링만 적용
    return getFilteredFilesByDate();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const totalFiles = getFilteredFilesByDate().length;
  const filteredFiles = getFilteredFiles();

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

      {/* 파일 업로드 섹션 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
          <CloudUpload /> 파일 업로드
        </Typography>
        
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <input
            accept="audio/*,.mp3,.wav,.m4a,.flac,.aac,.ogg"
            style={{ display: 'none' }}
            id="audio-file-upload"
            type="file"
            onChange={handleFileUpload}
          />
          <label htmlFor="audio-file-upload">
            <Button
              variant="outlined"
              component="span"
              startIcon={<CloudUpload />}
              disabled={uploading}
            >
              음성 파일 선택
            </Button>
          </label>
          
          {selectedFile && (
            <Box>
              <Typography variant="body1" component="span" sx={{ mr: 2 }}>
                선택된 파일: <strong>{selectedFile.name}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary" component="span">
                ({formatFileSize(selectedFile.size)})
              </Typography>
            </Box>
          )}

          {selectedFile && (
            <Button
              variant="contained"
              onClick={handleFileSubmit}
              disabled={uploading}
              startIcon={uploading ? <CircularProgress size={16} /> : <CloudUpload />}
            >
              {uploading ? '업로드 중...' : '업로드'}
            </Button>
          )}
        </Stack>
        
        <Alert severity="info" sx={{ mt: 2 }}>
          지원 형식: MP3, WAV, M4A, FLAC, AAC, OGG
        </Alert>
      </Paper>

      {/* 전체 요약 */}
      <Box display="flex" gap={2} mb={3} flexWrap="wrap">
        <Card sx={{ minWidth: 200 }}>
          <CardContent>
            <Typography variant="h6" color="primary">전체 파일</Typography>
            <Typography variant="h4">{totalFiles}</Typography>
            <Typography variant="body2" color="text.secondary">
              모든 오디오 파일 수
            </Typography>
          </CardContent>
        </Card>
        
        <Card sx={{ minWidth: 200 }}>
          <CardContent>
            <Typography variant="h6" color="secondary">루트 파일</Typography>
            <Typography variant="h4">{audioFiles.length}</Typography>
            <Typography variant="body2" color="text.secondary">
              src_record 직접 하위 파일
            </Typography>
          </CardContent>
        </Card>
        
        <Card sx={{ minWidth: 200 }}>
          <CardContent>
            <Typography variant="h6" color="success">일자별 폴더</Typography>
            <Typography variant="h4">{Object.keys(dailyFiles).length}</Typography>
            <Typography variant="body2" color="text.secondary">
              YYYY-MM-DD 형식 폴더 수
            </Typography>
          </CardContent>
        </Card>
        
        <Card sx={{ minWidth: 200 }}>
          <CardContent>
            <Typography variant="h6" color="warning">일자별 파일</Typography>
            <Typography variant="h4">
              {Object.values(dailyFiles).reduce((total, files) => total + files.length, 0)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              일자별 폴더 내 파일 수
            </Typography>
          </CardContent>
        </Card>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6">
          📋 파일 목록 ({filteredFiles.length}개)
        </Typography>
      </Paper>

      {/* 파일 목록 테이블 */}
      {filteredFiles.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>파일명</TableCell>
                <TableCell>경로</TableCell>
                <TableCell>위치</TableCell>
                <TableCell align="right">크기</TableCell>
                <TableCell>수정일</TableCell>
                <TableCell>확장자</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredFiles.map((file, index) => (
                <TableRow key={`${file.location}-${file.filename}-${index}`}>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <AudioFileIcon fontSize="small" color="action" />
                      {file.filename}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {file.path}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={file.location === 'root' ? '루트' : file.location}
                      size="small"
                      color={file.location === 'root' ? 'default' : 'primary'}
                    />
                  </TableCell>
                  <TableCell align="right">
                    {formatFileSize(file.size)}
                  </TableCell>
                  <TableCell>
                    {new Date(file.modified).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={file.extension}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Alert severity="info">
          {getCurrentSelectedDate() === '전체' ? 
            '파일이 없습니다.' : 
            `${getCurrentSelectedDate()}에 해당하는 파일이 없습니다.`
          }
        </Alert>
      )}

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

export default FileStatusPage; 