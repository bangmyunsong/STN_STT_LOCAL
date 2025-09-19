import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  CircularProgress,
  Alert,
  Stack,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
} from '@mui/material';
import {
  CheckCircle,
  Warning,
  Computer,
  Assignment,
  TrendingUp,
  CalendarToday as CalendarIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useSystemStore } from '../../store/systemStore';
import { apiService } from '../../services/api';

// 시스템 상태 컴포넌트
const SystemHealthCard: React.FC = () => {
  const { health, fetchHealth, isLoading, error } = useSystemStore();

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const getHealthStatus = () => {
    if (isLoading) return { color: 'info' as const, text: '확인 중...' };
    if (error) return { color: 'error' as const, text: `연결 실패: ${error}` };
    if (!health) return { color: 'warning' as const, text: '상태 불명' };
    
    const { models } = health;
    const allHealthy = models.whisper && models.erp_extractor && models.supabase;
    
    if (allHealthy) return { color: 'success' as const, text: '정상' };
    if (models.whisper && models.erp_extractor) return { color: 'warning' as const, text: '부분 정상' };
    return { color: 'error' as const, text: '오류' };
  };

  const healthStatus = getHealthStatus();

  return (
    <Card sx={{ height: '100%', mb: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6" component="div">
            시스템 상태
          </Typography>
          <Chip 
            label={healthStatus.text}
            color={healthStatus.color}
            icon={healthStatus.color === 'success' ? <CheckCircle /> : <Warning />}
          />
        </Box>
        
        {isLoading ? (
          <Box display="flex" justifyContent="center" py={2}>
            <CircularProgress size={40} />
          </Box>
        ) : error ? (
          <Alert severity="error" variant="outlined">
            {error}
          </Alert>
        ) : health ? (
          <Stack direction="row" spacing={2} justifyContent="space-around">
            <Box textAlign="center">
              <Computer color={health.models.whisper ? 'success' : 'error'} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                STT 엔진
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {health.models.whisper ? '정상' : '오류'}
              </Typography>
            </Box>
            <Box textAlign="center">
              <Assignment color={health.models.erp_extractor ? 'success' : 'error'} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                ERP 추출
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {health.models.erp_extractor ? '정상' : '오류'}
              </Typography>
            </Box>
            <Box textAlign="center">
              <TrendingUp color={health.models.supabase ? 'success' : 'error'} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                데이터베이스
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {health.models.supabase ? '정상' : '오류'}
              </Typography>
            </Box>
          </Stack>
        ) : null}
      </CardContent>
    </Card>
  );
};

// 통계 카드 컴포넌트
const StatCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
}> = ({ title, value, subtitle }) => (
  <Card sx={{ mb: 2 }}>
    <CardContent>
      <Typography variant="h4" component="div" color="primary.main" fontWeight="bold" gutterBottom>
        {value}
      </Typography>
      <Typography variant="h6" component="div" gutterBottom>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </CardContent>
  </Card>
);

// 메인 대시보드 컴포넌트
const Dashboard: React.FC = () => {
  const { 
    statistics, 
    fetchStatistics, 
    isLoading: systemLoading, 
    error: systemError 
  } = useSystemStore();

  // 월별/일별 조회 상태
  const [dailyFolders, setDailyFolders] = useState<string[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string>('전체');
  const [selectedDay, setSelectedDay] = useState<string>('전체');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 선택된 월/일이 변경될 때마다 데이터 다시 로드
  useEffect(() => {
    const loadFilteredData = async () => {
      try {
        setLoading(true);
        
        const currentDate = getCurrentSelectedDate();
        let filterOptions = {};
        
        if (currentDate !== '전체') {
          if (selectedDay === '전체') {
            // 월별 필터
            filterOptions = { monthFilter: selectedMonth };
          } else {
            // 일별 필터
            filterOptions = { dateFilter: `${selectedMonth}-${selectedDay}` };
          }
        }
        
        await fetchStatistics(filterOptions);
        
      } catch (error) {
        console.error('필터링된 통계 로드 실패:', error);
      } finally {
        setLoading(false);
      }
    };

    // 초기 로드가 아닌 경우에만 실행
    if (dailyFolders.length > 0) {
      loadFilteredData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMonth, selectedDay]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // 선택된 날짜에 따른 통계 로드
      const currentDate = getCurrentSelectedDate();
      let filterOptions = {};
      
      if (currentDate !== '전체') {
        if (selectedDay === '전체') {
          // 월별 필터
          filterOptions = { monthFilter: selectedMonth };
        } else {
          // 일별 필터
          filterOptions = { dateFilter: `${selectedMonth}-${selectedDay}` };
        }
      }
      
      await fetchStatistics(filterOptions);
      
      // 일자별 폴더 목록 로드
      try {
        const audioFilesData = await apiService.getAudioFiles();
        console.log('Audio files data:', audioFilesData); // 디버깅용
        
        const folders = Object.keys(audioFilesData.daily_files || {}).sort().reverse();
        console.log('Available folders:', folders); // 디버깅용
        setDailyFolders(folders);
        
        // 폴더가 없으면 경고 메시지 표시
        if (folders.length === 0) {
          console.warn('일자별 폴더가 없습니다. src_record 디렉토리에 YYYY-MM-DD 형식의 폴더가 있는지 확인하세요.');
        }
      } catch (audioError) {
        console.error('일자별 폴더 로드 실패:', audioError);
        setDailyFolders([]);
      }
      
    } catch (error) {
      console.error('대시보드 데이터 로드 실패:', error);
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
    const monthList = Array.from(months).sort().reverse();
    console.log('Available months:', monthList); // 디버깅용
    return monthList;
  };

  // 선택된 월의 일자 목록 생성
  const getAvailableDays = () => {
    if (selectedMonth === '전체') return [];
    
    const days = dailyFolders
      .filter(folder => folder.startsWith(selectedMonth))
      .map(folder => folder.substring(8)) // "DD" 부분만 추출
      .sort()
      .reverse();
    
    console.log(`Available days for ${selectedMonth}:`, days); // 디버깅용
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
      return '📊 STN 고객센터 STT 시스템 대시보드 (전체 기간)';
    } else if (selectedDay === '전체') {
      return `📊 STN 고객센터 STT 시스템 대시보드 (${selectedMonth} 월별)`;
    } else {
      return `📊 STN 고객센터 STT 시스템 대시보드 (${selectedMonth}-${selectedDay})`;
    }
  };

  // 성공률 계산
  const successRate = statistics ? 
    (statistics.completed_sessions / Math.max(statistics.total_sessions, 1) * 100).toFixed(1) : 
    '0';

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
          startIcon={<RefreshIcon />}
          onClick={loadData}
          disabled={loading || systemLoading}
        >
          새로고침
        </Button>
      </Box>

      {/* 월/일 필터 */}
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
        
        {/* 일자별 폴더가 없을 때 안내 메시지 */}
        {dailyFolders.length === 0 && (
          <Alert severity="info" sx={{ mt: 2 }}>
            📁 일자별 폴더가 없습니다. 
            <br />
            • src_record 디렉토리에 YYYY-MM-DD 형식의 폴더를 생성하세요
            <br />
            • 또는 음성 파일을 업로드하여 STT 처리를 진행하세요
          </Alert>
        )}
      </Paper>
      
      {systemError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          데이터 로딩 중 오류가 발생했습니다: {systemError}
        </Alert>
      ) : null}

      <SystemHealthCard />

      {(systemLoading || loading) ? (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress size={60} />
        </Box>
      ) : (
        <Stack spacing={2}>
          <Typography variant="h5" component="h2" gutterBottom>
            처리 통계
          </Typography>
          
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <StatCard
              title="전체 세션"
              value={statistics?.total_sessions || 0}
              subtitle="총 처리된 음성 파일"
            />
            <StatCard
              title="완료된 세션"
              value={statistics?.completed_sessions || 0}
              subtitle="성공적으로 처리됨"
            />
            <StatCard
              title="성공률"
              value={`${successRate}%`}
              subtitle="전체 대비 성공률"
            />
            <StatCard
              title="평균 처리 시간"
              value={statistics?.avg_processing_time ? `${statistics.avg_processing_time.toFixed(1)}초` : '0초'}
              subtitle="음성 파일당 평균"
            />
          </Stack>

          <Typography variant="h5" component="h2" gutterBottom sx={{ mt: 4 }}>
            ERP 처리 현황
          </Typography>
          
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <StatCard
              title="ERP 추출 완료"
              value={statistics?.total_extractions || 0}
              subtitle="데이터 추출 완료"
            />
            <StatCard
              title="ERP 등록 성공"
              value={statistics?.success_registers || 0}
              subtitle="시스템 등록 완료"
            />
            <StatCard
              title="등록 성공률"
              value={
                statistics && statistics.total_registers > 0 
                  ? `${((statistics.success_registers / statistics.total_registers) * 100).toFixed(1)}%`
                  : '0%'
              }
              subtitle={`총 ${statistics?.total_registers || 0}건 중 ${statistics?.success_registers || 0}건 성공`}
            />
          </Stack>

          {getCurrentSelectedDate() !== '전체' && (
            <Alert severity="info" sx={{ mt: 2 }}>
              📅 현재 {getCurrentSelectedDate() === selectedMonth ? '월별' : '일별'} 데이터를 조회하고 있습니다. 
              전체 통계는 "전체"를 선택해주세요.
            </Alert>
          )}
        </Stack>
      )}
    </Box>
  );
};

export default Dashboard; 