import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Stack,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Security as SecurityIcon,
  Storage as StorageIcon,
  Api as ApiIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { apiService } from '../../services/api';

interface EnvironmentStatus {
  name: string;
  value?: string;
  isSet: boolean;
  isValid: boolean;
}

interface SystemInfo {
  envStatus: EnvironmentStatus[];
  apiServerInfo: {
    connected: boolean;
    baseUrl: string;
    healthData?: Record<string, any>;
  };
}

const SettingsPage: React.FC = () => {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSystemInfo();
  }, []);

  const loadSystemInfo = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // API 서버 헬스 체크
      let apiConnected = false;
      let healthData: Record<string, any> | undefined = undefined;
      
      try {
        const healthResponse = await apiService.healthCheck();
        apiConnected = true;
        healthData = healthResponse as Record<string, any>;
      } catch (apiError) {
        console.warn('API 서버 연결 실패:', apiError);
        apiConnected = false;
        healthData = undefined;
      }

      // 환경변수 상태 초기화
      let envStatus: EnvironmentStatus[] = [
        { name: 'OpenAI API Key', isSet: false, isValid: false },
        { name: 'Supabase URL', isSet: false, isValid: false },
        { name: 'Supabase Anon Key', isSet: false, isValid: false },
        { name: 'HuggingFace Token', isSet: false, isValid: false },
      ];

      // API 서버가 연결된 경우 환경변수 상태 확인
      if (apiConnected) {
        try {
          const envResponse = await apiService.getEnvironmentStatus();
          console.log('환경변수 상태 응답:', envResponse);
          
          // 디버깅을 위해 환경변수 응답을 healthData에 추가
          if (healthData) {
            healthData.environment_status = envResponse;
          }
          
          if (envResponse.environment_variables) {
            // API 서버 응답의 키와 화면 표시 이름 매핑
            const keyMapping = {
              'OpenAI API Key': 'OPENAI_API_KEY',
              'Supabase URL': 'SUPABASE_URL', 
              'Supabase Anon Key': 'SUPABASE_ANON_KEY',
              'HuggingFace Token': 'HUGGINGFACE_HUB_TOKEN'
            };
            
            envStatus = envStatus.map(env => {
              const apiKey = keyMapping[env.name as keyof typeof keyMapping];
              const isSet = Boolean(envResponse.environment_variables[apiKey]);
              return {
                ...env,
                isSet,
                isValid: isSet,
              };
            });
          }
        } catch (envError) {
          console.warn('환경변수 상태 확인 실패:', envError);
        }
      }

      setSystemInfo({
        envStatus,
        apiServerInfo: {
          connected: apiConnected,
          baseUrl: 'http://localhost:8000',
          healthData,
        },
      });
    } catch (err) {
      setError('시스템 정보 로드 실패');
      console.error('시스템 정보 로드 오류:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    loadSystemInfo();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2 }}>
          시스템 정보 로딩 중...
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={3}>
        <Typography variant="h4" component="h1">
          ⚙️ 시스템 설정
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading}
        >
          새로고침
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* 환경변수 설정 상태 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
          <SecurityIcon /> 환경변수 설정 상태
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          config.env 파일의 환경변수 설정 상태를 확인합니다.
        </Typography>
        
        <Stack spacing={2}>
          {systemInfo?.envStatus.map((env, index) => (
            <Card key={index} variant="outlined">
              <CardContent sx={{ py: 2 }}>
                <Stack direction="row" alignItems="center" justifyContent="space-between">
                  <Typography variant="body1" fontWeight="medium">
                    {env.name}
                  </Typography>
                  <Chip
                    icon={env.isSet ? <CheckIcon /> : <CancelIcon />}
                    label={env.isSet ? '설정됨' : '설정되지 않음'}
                    color={env.isSet ? 'success' : 'error'}
                    size="small"
                  />
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>

        {systemInfo?.apiServerInfo.connected ? (
          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              환경변수를 수정하려면 프로젝트 루트의 <code>config.env</code> 파일을 편집하고 API 서버를 재시작하세요.
            </Typography>
          </Alert>
        ) : (
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              API 서버에 연결할 수 없어 환경변수 상태를 확인할 수 없습니다. 
              API 서버가 실행 중인지 확인하세요. (<code>run_api_server.bat</code>)
            </Typography>
          </Alert>
        )}
      </Paper>

      {/* API 서버 정보 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
          <ApiIcon /> API 서버 정보
        </Typography>
        
        <Stack spacing={2}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Base URL
            </Typography>
            <Typography variant="body1" fontFamily="monospace">
              {systemInfo?.apiServerInfo.baseUrl}
            </Typography>
          </Box>
          
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              연결 상태
            </Typography>
            <Chip
              icon={systemInfo?.apiServerInfo.connected ? <CheckIcon /> : <CancelIcon />}
              label={systemInfo?.apiServerInfo.connected ? 'API 서버 연결됨' : 'API 서버 연결 실패'}
              color={systemInfo?.apiServerInfo.connected ? 'success' : 'error'}
            />
          </Box>
          
          {systemInfo?.apiServerInfo.connected && systemInfo?.apiServerInfo.healthData && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                헬스 체크 응답
              </Typography>
              <Box
                sx={{
                  backgroundColor: 'grey.100',
                  p: 2,
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  overflow: 'auto',
                  maxHeight: 200,
                }}
              >
                <pre>{JSON.stringify(systemInfo.apiServerInfo.healthData, null, 2)}</pre>
              </Box>
            </Box>
          )}
        </Stack>
      </Paper>

      {/* 데이터베이스 스키마 정보 */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
          <StorageIcon /> 데이터베이스 스키마
        </Typography>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          시스템에서 사용하는 Supabase 테이블 정보입니다.
        </Typography>
        
        <List>
          <ListItem>
            <ListItemIcon>
              <InfoIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="stt_sessions"
              secondary="STT 처리 세션 정보를 저장하는 테이블"
            />
          </ListItem>
          
          <ListItem>
            <ListItemIcon>
              <InfoIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="erp_extractions"
              secondary="ERP 추출 결과를 저장하는 테이블"
            />
          </ListItem>
          
          <ListItem>
            <ListItemIcon>
              <InfoIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="erp_register_logs"
              secondary="ERP 등록 로그를 저장하는 테이블"
            />
          </ListItem>
        </List>

        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            스키마 생성 SQL은 <code>supabase_client.py</code> 파일을 참조하세요.
          </Typography>
        </Alert>
      </Paper>
    </Box>
  );
};

export default SettingsPage;