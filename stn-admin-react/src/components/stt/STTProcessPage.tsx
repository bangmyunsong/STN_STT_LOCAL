import React, { useState, useEffect, useCallback } from 'react';
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
  FormControlLabel,
  Switch,
  LinearProgress,
  Alert,
  Stack,
  Paper,
  List,
  ListItem,
  ListItemText,
  Tooltip,
  ListItemButton,
  Chip,
  Checkbox,
  Divider,
} from '@mui/material';
import {
  Refresh,
  CalendarToday as CalendarIcon,
  PlayArrow,
  Stop,
  ArrowForward,
  ArrowBack,
  CheckCircle,
  Schedule,
  Folder,
} from '@mui/icons-material';
import { useSTTStore } from '../../store/sttStore';
import { useFileStore } from '../../store/fileStore';
import { STTProcessOptions, AudioFileInfo } from '../../types/api';
import { apiService } from '../../services/api';

// 파일 크기를 읽기 쉬운 형태로 변환
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const STTProcessPage: React.FC = () => {
  // 월별/일별 조회 상태
  const [selectedMonth, setSelectedMonth] = useState<string>('전체');
  const [selectedDay, setSelectedDay] = useState<string>('전체');
  
  // Dual ListBox 상태
  const [availableFiles, setAvailableFiles] = useState<AudioFileInfo[]>([]);
  const [targetFiles, setTargetFiles] = useState<AudioFileInfo[]>([]);
  const [selectedAvailable, setSelectedAvailable] = useState<string[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string[]>([]);
  
  // 처리 완료된 파일 상태
  const [processedFiles, setProcessedFiles] = useState<Set<string>>(new Set());
  const [sttSessions, setSttSessions] = useState<any[]>([]);
  const [erpExtractions, setErpExtractions] = useState<any[]>([]);
  
  const [options, setOptions] = useState<STTProcessOptions>({
    model_name: 'base',
    language: 'auto', // AUTO를 기본값으로 설정
    enable_diarization: true,
    extract_erp: true,
    save_to_db: true,
  });

  const {
    processFile,
    processServerFile,
    isProcessing,
    processingProgress,
    processingStatus,
    error: sttError,
    clearError,
  } = useSTTStore();

  const {
    audioFiles,
    dailyFiles,
    fetchAudioFiles,
    fetchProcessingStatus,
    checkFileProcessed,
    isLoading: fileLoading,
    error: fileError,
  } = useFileStore();
  
  // STT 세션과 ERP 추출 데이터를 가져와서 처리 완료 상태 확인
  const fetchSTTAndERPData = useCallback(async () => {
    try {
      const [sessionsData, extractionsData] = await Promise.all([
        apiService.getSessions(200),
        apiService.getExtractions(200)
      ]);
      
      setSttSessions(sessionsData.sessions || []);
      setErpExtractions(extractionsData.extractions || []);
      
      console.log(`STT 세션 ${sessionsData.sessions?.length || 0}개, ERP 추출 ${extractionsData.extractions?.length || 0}개 로드됨`);
    } catch (error) {
      console.error('STT/ERP 데이터 로드 실패:', error);
    }
  }, []);

  // 처리 완료된 파일 경로 계산 (STT 세션 + ERP 추출 완료 기준)
  const calculateProcessedFiles = useCallback(() => {
    const processed = new Set<string>();
    
    // ERP 추출이 완료된 세션 ID들 찾기
    const sessionsWithERP = new Set(erpExtractions.map(extraction => extraction.session_id));
    
    // 각 STT 세션을 확인하여 ERP 추출도 완료된 경우 처리 완료로 표시
    sttSessions.forEach(session => {
      if (session.status === 'completed' && sessionsWithERP.has(session.id)) {
        // 파일명을 경로 형태로 변환하여 매칭
        const filePath = session.file_name;
        processed.add(filePath);
      }
    });
    
    setProcessedFiles(processed);
    console.log(`처리 완료 파일 ${processed.size}개: STT + ERP 추출 모두 완료`);
  }, [sttSessions, erpExtractions]);

  // 컴포넌트 초기화
  useEffect(() => {
    fetchAudioFiles();
    fetchSTTAndERPData();
  }, [fetchAudioFiles, fetchSTTAndERPData]);

  // 처리 상태 계산
  useEffect(() => {
    calculateProcessedFiles();
  }, [calculateProcessedFiles]);

  // 월별 목록 생성
  const getAvailableMonths = () => {
    const months = new Set<string>();
    Object.keys(dailyFiles).forEach(folder => {
      // YYYY-MM-DD에서 YYYY-MM 추출
      const monthPart = folder.substring(0, 7); // "YYYY-MM"
      months.add(monthPart);
    });
    return Array.from(months).sort().reverse();
  };

  // 선택된 월의 일자 목록 생성
  const getAvailableDays = () => {
    if (selectedMonth === '전체') return [];
    
    const days = Object.keys(dailyFiles)
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

  // 타이틀 텍스트 생성
  const getTitleText = () => {
    const currentDate = getCurrentSelectedDate();
    if (currentDate === '전체') {
      return '🎙️ STT 처리 (전체 기간)';
    } else if (selectedDay === '전체') {
      return `🎙️ STT 처리 (${selectedMonth} 월별)`;
    } else {
      return `🎙️ STT 처리 (${selectedMonth}-${selectedDay})`;
    }
  };

  // 날짜 필터링된 일자별 폴더 목록 생성
  const getFilteredDailyFiles = () => {
    const currentDate = getCurrentSelectedDate();
    
    if (currentDate === '전체') {
      return dailyFiles;
    }
    
    const filtered: { [key: string]: AudioFileInfo[] } = {};
    
    if (selectedDay === '전체') {
      // 월별 필터링
      Object.keys(dailyFiles).forEach(folder => {
        if (folder.startsWith(selectedMonth)) {
          filtered[folder] = dailyFiles[folder];
        }
      });
    } else {
      // 특정 일자 필터링
      const targetDate = `${selectedMonth}-${selectedDay}`;
      if (dailyFiles[targetDate]) {
        filtered[targetDate] = dailyFiles[targetDate];
      }
    }
    
    return filtered;
  };

  // 모든 서버 파일 가져오기 (날짜 필터링 적용)
  const getAllServerFiles = (): AudioFileInfo[] => {
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
    const filteredDailyFiles = getFilteredDailyFiles();
    Object.values(filteredDailyFiles).forEach(files => {
      allFiles.push(...files);
    });
    return allFiles;
  };

  // 날짜 필터링된 파일 가져오기 (모든 파일 포함)
  const getFilteredFiles = (): AudioFileInfo[] => {
    const allFiles = getAllServerFiles();
    // 모든 파일 반환 (처리 완료 여부와 관계없이)
    return allFiles;
  };

  // 파일 목록 새로고침
  const handleRefresh = () => {
    fetchAudioFiles();
    fetchSTTAndERPData();
    // 새로고침 시 처리된 파일 상태도 업데이트
    setTimeout(() => {
      updateProcessedFilesStatus();
    }, 500);
  };

  // 처리된 파일 상태 강제 업데이트 함수 (STT + ERP 완료 기준)
  const updateProcessedFilesStatus = async () => {
    try {
      // 최신 파일 목록과 STT/ERP 데이터 가져오기
      await fetchAudioFiles();
      await fetchSTTAndERPData();
      
      console.log('처리된 파일 상태 업데이트 완료');
    } catch (error) {
      console.error('파일 상태 업데이트 실패:', error);
    }
  };

  // Dual ListBox - 오른쪽으로 이동 (처리 대상에 추가)
  const moveToTarget = () => {
    const filesToMove = availableFiles.filter(file => 
      selectedAvailable.includes(file.path)
    );
    
    setTargetFiles(prev => [...prev, ...filesToMove]);
    setAvailableFiles(prev => prev.filter(file => 
      !selectedAvailable.includes(file.path)
    ));
    setSelectedAvailable([]);
  };

  // Dual ListBox - 왼쪽으로 이동 (처리 대상에서 제거)
  const moveToAvailable = () => {
    const filesToMove = targetFiles.filter(file => 
      selectedTarget.includes(file.path)
    );
    
    setAvailableFiles(prev => [...prev, ...filesToMove]);
    setTargetFiles(prev => prev.filter(file => 
      !selectedTarget.includes(file.path)
    ));
    setSelectedTarget([]);
  };

  // 필터링된 파일 목록이 변경될 때 Available Files 업데이트
  useEffect(() => {
    const filtered = getFilteredFiles();
    // 현재 target에 없는 파일들만 available로
    const targetPaths = new Set(targetFiles.map(f => f.path));
    const newAvailable = filtered.filter(file => !targetPaths.has(file.path));
    setAvailableFiles(newAvailable);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMonth, selectedDay, audioFiles, dailyFiles, targetFiles]); // processedFiles 제거로 무한 루프 방지

  // 일괄 STT 처리
  const handleBulkProcess = async () => {
    if (targetFiles.length === 0) return;

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < targetFiles.length; i++) {
      const file = targetFiles[i];
      
      try {
        await processServerFile(file.path, options);
        successCount++;
      } catch (error) {
        failCount++;
        console.error(`파일 처리 실패: ${file.filename}`, error);
      }
    }

    alert(`일괄 처리 완료!\n성공: ${successCount}개\n실패: ${failCount}개`);
    
    // 처리 완료 후 대상 목록 초기화
    setTargetFiles([]);
    setSelectedTarget([]);
    
    // 파일 목록 새로고침
    handleRefresh();
    
    // 처리 완료 후 상태 업데이트
    setTimeout(() => {
      updateProcessedFilesStatus();
    }, 1500); // 1.5초 후 상태 업데이트
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1">
            {getTitleText()}
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={handleRefresh}
          disabled={fileLoading}
        >
          새로고침
        </Button>
      </Box>

      {/* 에러 알림 */}
      {(sttError || fileError) && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {sttError || fileError}
        </Alert>
      )}

      {/* 통합 설정 영역: 월별/일별 조회 + 처리 옵션 설정 */}
      <Box sx={{ mb: 3 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          {/* 좌측: 월별/일별 조회 (50%) */}
          <Box sx={{ flex: { md: 5 }, width: '100%' }}>
            <Paper sx={{ p: 1.5, height: '100%' }}>
              <Typography variant="subtitle1" gutterBottom display="flex" alignItems="center" gap={1} sx={{ fontSize: '1rem' }}>
                <CalendarIcon fontSize="small" /> 월/일 조회
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="center">
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>월</InputLabel>
                  <Select
                    value={selectedMonth}
                    label="월"
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
                
                <FormControl size="small" sx={{ minWidth: 90 }} disabled={selectedMonth === '전체'}>
                  <InputLabel>일</InputLabel>
                  <Select
                    value={selectedDay}
                    label="일"
                    onChange={(e) => setSelectedDay(e.target.value)}
                  >
                    <MenuItem value="전체">전체</MenuItem>
                    {getAvailableDays().map(day => (
                      <MenuItem key={day} value={day}>{day}일</MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <Button
                  size="small"
                  variant="outlined"
                  sx={{ minWidth: 60 }}
                  onClick={() => {
                    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
                    const todayMonth = today.substring(0, 7); // YYYY-MM
                    const todayDay = today.substring(8); // DD
                    
                    // 오늘 날짜의 폴더가 있는지 확인
                    if (dailyFiles[today]) {
                      setSelectedMonth(todayMonth);
                      setSelectedDay(todayDay);
                    } else {
                      // 오늘 날짜 폴더가 없으면 이번 달로 설정
                      const availableMonths = getAvailableMonths();
                      if (availableMonths.includes(todayMonth)) {
                        setSelectedMonth(todayMonth);
                        setSelectedDay('전체');
                      }
                    }
                  }}
                  disabled={!Object.keys(dailyFiles).some(folder => folder.startsWith(new Date().toISOString().substring(0, 7)))}
                >
                  오늘
                </Button>
              </Stack>
            </Paper>
          </Box>

          {/* 우측: 처리 옵션 설정 (50%) */}
          <Box sx={{ flex: { md: 5 }, width: '100%' }}>
            <Paper sx={{ p: 1.5, height: '100%' }}>
              <Typography variant="subtitle1" gutterBottom sx={{ fontSize: '1rem' }}>
                ⚙️ 처리 옵션 설정
              </Typography>
              
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
                {/* 모델 및 언어 설정 */}
                <Stack direction="row" spacing={1.5}>
                  <FormControl size="small" sx={{ minWidth: 90 }}>
                    <InputLabel>모델</InputLabel>
                    <Select
                      value={options.model_name}
                      label="모델"
                      onChange={(e) => setOptions(prev => ({ ...prev, model_name: e.target.value }))}
                    >
                      <MenuItem value="base">Base</MenuItem>
                      <MenuItem value="small">Small</MenuItem>
                      <MenuItem value="medium">Medium</MenuItem>
                      <MenuItem value="large">Large</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl size="small" sx={{ minWidth: 70 }}>
                    <InputLabel>언어</InputLabel>
                    <Select
                      value={options.language || 'auto'}
                      label="언어"
                      onChange={(e) => setOptions(prev => ({ ...prev, language: e.target.value }))}
                    >
                      <MenuItem value="ko">KO</MenuItem>
                      <MenuItem value="en">EN</MenuItem>
                      <MenuItem value="auto">Auto</MenuItem>
                    </Select>
                  </FormControl>
                </Stack>

                {/* 옵션 스위치들 - 한 줄 배치 */}
                <Stack direction="row" spacing={2} flexWrap="wrap">
                  <FormControlLabel
                    control={
                      <Switch
                        size="small"
                        checked={options.enable_diarization}
                        onChange={(e) => setOptions(prev => ({ ...prev, enable_diarization: e.target.checked }))}
                      />
                    }
                    label="화자분리"
                    sx={{ '& .MuiFormControlLabel-label': { fontSize: '0.875rem' } }}
                  />
                  <Tooltip 
                    title="음성 파일에서 ERP 데이터를 추출합니다"
                    placement="top"
                  >
                    <FormControlLabel
                      control={
                        <Switch
                          size="small"
                          checked={options.extract_erp}
                          onChange={(e) => {
                            const extractErp = e.target.checked;
                            setOptions(prev => ({ 
                              ...prev, 
                              extract_erp: extractErp,
                              // ERP 추출을 비활성화하면 DB 저장도 자동으로 비활성화
                              save_to_db: extractErp ? prev.save_to_db : false
                            }));
                          }}
                        />
                      }
                      label="ERP추출"
                      sx={{ '& .MuiFormControlLabel-label': { fontSize: '0.875rem' } }}
                    />
                  </Tooltip>
                  <FormControlLabel
                    control={
                      <Switch
                        size="small"
                        checked={options.save_to_db}
                        disabled={!options.extract_erp} // ERP 추출이 비활성화되면 DB 저장도 비활성화
                        onChange={(e) => setOptions(prev => ({ ...prev, save_to_db: e.target.checked }))}
                      />
                    }
                    label="ERP연동"
                    sx={{ 
                      '& .MuiFormControlLabel-label': { 
                        fontSize: '0.875rem',
                        color: !options.extract_erp ? 'text.disabled' : 'inherit'
                      } 
                    }}
                  />
                </Stack>
              </Stack>
            </Paper>
          </Box>
        </Stack>
      </Box>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            📂 STT 처리 파일 선택
          </Typography>

          {fileLoading ? (
            <Box sx={{ py: 2 }}>
              <LinearProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                파일 목록을 불러오는 중...
              </Typography>
            </Box>
          ) : fileError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {fileError}
            </Alert>
          ) : (
            <Box>
              {/* 통계 정보 */}
              <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
                <Stack direction="row" spacing={4} flexWrap="wrap">
                  <Chip 
                    icon={<Folder />} 
                    label={`선택된 기간: ${getAllServerFiles().length}개`} 
                    variant="outlined" 
                  />
                  <Chip 
                    icon={<CheckCircle />} 
                    label={`처리 완료: ${[...availableFiles, ...targetFiles].filter(file => processedFiles.has(file.path)).length}개`} 
                    color="success" 
                    variant="outlined" 
                  />
                  <Chip 
                    icon={<Schedule />} 
                    label={`처리 가능: ${getFilteredFiles().length}개`} 
                    color="warning" 
                    variant="outlined" 
                  />
                  {getCurrentSelectedDate() !== '전체' && (
                    <Chip 
                      icon={<CalendarIcon />} 
                      label={`조회 기간: ${getCurrentSelectedDate()}`} 
                      color="primary" 
                      variant="outlined" 
                    />
                  )}
                </Stack>
              </Paper>

              {/* Dual ListBox */}
              <Typography variant="h6" gutterBottom>
                📋 STT 처리 파일 선택
              </Typography>

              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 3 }}>
                {/* 처리할 파일 선택 */}
                <Box sx={{ flex: 1 }}>
                  <Paper sx={{ p: 2, height: 400 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      처리할 파일 선택
                    </Typography>
                    <Typography variant="caption" color="text.secondary" gutterBottom>
                      사용 가능: {availableFiles.length}개 (선택: {selectedAvailable.length}개)
                    </Typography>
                    
                    {/* 전체 선택/해제 버튼 */}
                    <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                      <Button 
                        size="small" 
                        variant="outlined" 
                        onClick={() => {
                          const allPaths = availableFiles.map(file => file.path);
                          setSelectedAvailable(allPaths);
                        }}
                        disabled={availableFiles.length === 0}
                      >
                        전체 선택
                      </Button>
                      <Button 
                        size="small" 
                        variant="outlined" 
                        onClick={() => setSelectedAvailable([])}
                        disabled={selectedAvailable.length === 0}
                      >
                        해제
                      </Button>
                    </Stack>
                    
                    <List sx={{ maxHeight: 250, overflow: 'auto', mt: 1 }}>
                      {availableFiles.map((file) => {
                        const isProcessed = processedFiles.has(file.path);
                        
                        return (
                          <ListItem key={file.path} disablePadding>
                            <ListItemButton
                              selected={selectedAvailable.includes(file.path)}
                              onClick={() => {
                                setSelectedAvailable(prev => 
                                  prev.includes(file.path)
                                    ? prev.filter(p => p !== file.path)
                                    : [...prev, file.path]
                                );
                              }}
                              sx={{
                                backgroundColor: isProcessed ? 'rgba(76, 175, 80, 0.1)' : 'inherit',
                                '&:hover': {
                                  backgroundColor: isProcessed ? 'rgba(76, 175, 80, 0.2)' : 'rgba(0, 0, 0, 0.04)'
                                }
                              }}
                            >
                              <Checkbox
                                checked={selectedAvailable.includes(file.path)}
                                tabIndex={-1}
                                disableRipple
                              />
                              <ListItemText
                                primary={
                                  <Stack direction="row" alignItems="center" spacing={1}>
                                    <Typography 
                                      variant="body2"
                                      sx={{
                                        color: isProcessed ? 'success.main' : 'inherit',
                                        fontWeight: isProcessed ? 500 : 'normal'
                                      }}
                                    >
                                      {file.filename}
                                    </Typography>
                                    {isProcessed && (
                                      <Chip 
                                        label="처리완료" 
                                        size="small" 
                                        color="success"
                                        variant="outlined"
                                        sx={{ fontSize: '0.7rem', height: '20px' }}
                                      />
                                    )}
                                  </Stack>
                                }
                                secondary={
                                  <Stack direction="row" spacing={1} alignItems="center">
                                    <Chip 
                                      label={file.location === 'root' ? '루트' : file.location} 
                                      size="small" 
                                      variant="outlined" 
                                    />
                                    <Typography variant="caption">
                                      {formatFileSize(file.size)}
                                    </Typography>
                                  </Stack>
                                }
                              />
                            </ListItemButton>
                          </ListItem>
                        );
                      })}
                    </List>
                  </Paper>
                </Box>

                {/* 이동 버튼 */}
                <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minWidth: 120 }}>
                  <Stack spacing={2} alignItems="center">
                    <Button
                      variant="contained"
                      onClick={moveToTarget}
                      disabled={selectedAvailable.length === 0}
                      startIcon={<ArrowForward />}
                    >
                      추가
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={moveToAvailable}
                      disabled={selectedTarget.length === 0}
                      startIcon={<ArrowBack />}
                    >
                      제거
                    </Button>
                  </Stack>
                </Box>

                {/* STT 처리 대상 */}
                <Box sx={{ flex: 1 }}>
                  <Paper sx={{ p: 2, height: 400 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      STT 처리 대상
                    </Typography>
                    <Typography variant="caption" color="text.secondary" gutterBottom>
                      처리 대상: {targetFiles.length}개 (선택: {selectedTarget.length}개)
                    </Typography>
                    
                    {/* 전체 선택/해제 버튼 */}
                    <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                      <Button 
                        size="small" 
                        variant="outlined" 
                        onClick={() => {
                          const allPaths = targetFiles.map(file => file.path);
                          setSelectedTarget(allPaths);
                        }}
                        disabled={targetFiles.length === 0}
                      >
                        전체 선택
                      </Button>
                      <Button 
                        size="small" 
                        variant="outlined" 
                        onClick={() => setSelectedTarget([])}
                        disabled={selectedTarget.length === 0}
                      >
                        해제
                      </Button>
                    </Stack>
                    
                    <List sx={{ maxHeight: 250, overflow: 'auto', mt: 1 }}>
                      {targetFiles.map((file) => {
                        const isProcessed = processedFiles.has(file.path);
                        
                        return (
                          <ListItem key={file.path} disablePadding>
                            <ListItemButton
                              selected={selectedTarget.includes(file.path)}
                              onClick={() => {
                                setSelectedTarget(prev => 
                                  prev.includes(file.path)
                                    ? prev.filter(p => p !== file.path)
                                    : [...prev, file.path]
                                );
                              }}
                              sx={{
                                backgroundColor: isProcessed ? 'rgba(76, 175, 80, 0.1)' : 'inherit',
                                '&:hover': {
                                  backgroundColor: isProcessed ? 'rgba(76, 175, 80, 0.2)' : 'rgba(0, 0, 0, 0.04)'
                                }
                              }}
                            >
                              <Checkbox
                                checked={selectedTarget.includes(file.path)}
                                tabIndex={-1}
                                disableRipple
                              />
                              <ListItemText
                                primary={
                                  <Stack direction="row" alignItems="center" spacing={1}>
                                    <Typography 
                                      variant="body2"
                                      sx={{
                                        color: isProcessed ? 'success.main' : 'inherit',
                                        fontWeight: isProcessed ? 500 : 'normal'
                                      }}
                                    >
                                      {file.filename}
                                    </Typography>
                                    {isProcessed && (
                                      <Chip 
                                        label="처리완료" 
                                        size="small" 
                                        color="success"
                                        variant="outlined"
                                        sx={{ fontSize: '0.7rem', height: '20px' }}
                                      />
                                    )}
                                  </Stack>
                                }
                                secondary={
                                  <Stack direction="row" spacing={1} alignItems="center">
                                    <Chip 
                                      label={file.location === 'root' ? '루트' : file.location} 
                                      size="small" 
                                      variant="outlined" 
                                    />
                                    <Typography variant="caption">
                                      {formatFileSize(file.size)}
                                    </Typography>
                                  </Stack>
                                }
                              />
                            </ListItemButton>
                          </ListItem>
                        );
                      })}
                    </List>
                  </Paper>
                </Box>
              </Stack>

              {/* 일괄 처리 시작 */}
              {targetFiles.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Divider sx={{ mb: 2 }} />
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="body1">
                      📋 <strong>처리 예정:</strong> {targetFiles.length}개 파일이 순차적으로 처리됩니다.
                    </Typography>
                    <Button
                      variant="contained"
                      size="large"
                      onClick={handleBulkProcess}
                      disabled={isProcessing}
                      startIcon={isProcessing ? <Stop /> : <PlayArrow />}
                    >
                      {isProcessing ? '처리 중...' : '🚀 STT 처리 시작'}
                    </Button>
                  </Stack>
                </Box>
              )}

              {targetFiles.length === 0 && (
                <Alert severity="info" sx={{ mt: 3 }}>
                  📝 STT 처리할 파일을 선택해주세요. 좌측에서 파일을 선택하고 "추가" 버튼을 클릭하세요.
                </Alert>
              )}

              {getCurrentSelectedDate() !== '전체' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  📅 현재 {getCurrentSelectedDate() === selectedMonth ? '월별' : '일별'} 파일을 조회하고 있습니다. 
                  전체 파일은 "전체"를 선택해주세요.
                </Alert>
              )}
            </Box>
          )}

          {/* 처리 진행 상황 */}
          {isProcessing && (
            <Box sx={{ mt: 3 }}>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                처리 진행 상황
              </Typography>
              <LinearProgress variant="determinate" value={processingProgress} sx={{ mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                {processingStatus} ({processingProgress}%)
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default STTProcessPage; 