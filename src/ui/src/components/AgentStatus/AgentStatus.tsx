import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  IconButton,
  Tooltip,
  LinearProgress,
  Alert,
  Paper
} from '@mui/material';
import {
  PlayArrow as ActiveIcon,
  Pause as IdleIcon,
  Stop as InactiveIcon,
  Refresh as RefreshIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon
} from '@mui/icons-material';

interface AgentStatus {
  status: 'active' | 'idle' | 'inactive';
  last_activity: string | null;
  last_action: string | null;
  success_rate: 'high' | 'low' | 'unknown';
}

interface AgentStatusData {
  agents: {
    data_ingestion: AgentStatus;
    normalization: AgentStatus;
    matching: AgentStatus;
    exception_identification: AgentStatus;
    resolution: AgentStatus;
    reporting: AgentStatus;
    human_in_loop: AgentStatus;
  };
  overall_status: 'operational' | 'idle' | 'error';
}

const AgentStatus: React.FC = () => {
  const [agentStatus, setAgentStatus] = useState<AgentStatusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchAgentStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/v1/logs/agents/status');
      if (!response.ok) {
        throw new Error('Failed to fetch agent status');
      }
      
      const data = await response.json();
      setAgentStatus(data);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgentStatus();
    
    // Refresh every 10 seconds
    const interval = setInterval(fetchAgentStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <ActiveIcon color="success" />;
      case 'idle':
        return <IdleIcon color="warning" />;
      case 'inactive':
        return <InactiveIcon color="error" />;
      default:
        return <InactiveIcon color="error" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'idle':
        return 'warning';
      case 'inactive':
        return 'error';
      default:
        return 'error';
    }
  };

  const getSuccessRateIcon = (rate: string) => {
    switch (rate) {
      case 'high':
        return <SuccessIcon color="success" fontSize="small" />;
      case 'low':
        return <ErrorIcon color="error" fontSize="small" />;
      default:
        return <WarningIcon color="warning" fontSize="small" />;
    }
  };

  const formatLastActivity = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const agentDisplayNames = {
    data_ingestion: 'Data Ingestion',
    normalization: 'Normalization',
    matching: 'Matching',
    exception_identification: 'Exception ID',
    resolution: 'Resolution',
    reporting: 'Reporting',
    human_in_loop: 'Human-in-Loop'
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Error loading agent status: {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h2">
          Agent Status Dashboard
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {loading && <LinearProgress sx={{ width: 100 }} />}
          <Tooltip title="Refresh status">
            <IconButton onClick={fetchAgentStatus} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          {lastUpdate && (
            <Typography variant="caption" color="text.secondary">
              Last update: {lastUpdate.toLocaleTimeString()}
            </Typography>
          )}
        </Box>
      </Box>

      {agentStatus && (
        <>
          {/* Overall Status */}
          <Paper sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6">Overall System Status:</Typography>
              <Chip
                label={agentStatus.overall_status.toUpperCase()}
                color={agentStatus.overall_status === 'operational' ? 'success' : 'warning'}
                icon={agentStatus.overall_status === 'operational' ? <SuccessIcon /> : <WarningIcon />}
              />
            </Box>
          </Paper>

          {/* Agent Grid */}
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 2 }}>
            {Object.entries(agentStatus.agents).map(([agentKey, status]) => (
              <Card 
                key={agentKey}
                sx={{ 
                  height: '100%',
                  border: 1,
                  borderColor: getStatusColor(status.status) + '.main',
                  '&:hover': {
                    boxShadow: 4,
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out'
                  }
                }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="subtitle2" component="h3" sx={{ fontWeight: 'bold' }}>
                      {agentDisplayNames[agentKey as keyof typeof agentDisplayNames]}
                    </Typography>
                    {getStatusIcon(status.status)}
                  </Box>

                  <Box sx={{ mb: 2 }}>
                    <Chip
                      label={status.status.toUpperCase()}
                      color={getStatusColor(status.status) as any}
                      size="small"
                      sx={{ mb: 1 }}
                    />
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {getSuccessRateIcon(status.success_rate)}
                      <Typography variant="caption" color="text.secondary">
                        {status.success_rate} success rate
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ space: 1 }}>
                    <Typography variant="caption" display="block" color="text.secondary">
                      Last Activity: {formatLastActivity(status.last_activity)}
                    </Typography>
                    {status.last_action && (
                      <Typography variant="caption" display="block" color="text.secondary">
                        Last Action: {status.last_action.replace(/_/g, ' ')}
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>

          {/* Status Legend */}
          <Paper sx={{ p: 2, mt: 3, bgcolor: 'background.default' }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Status Legend:
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <ActiveIcon color="success" fontSize="small" />
                <Typography variant="caption">Active - Currently processing</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <IdleIcon color="warning" fontSize="small" />
                <Typography variant="caption">Idle - Recently active</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <InactiveIcon color="error" fontSize="small" />
                <Typography variant="caption">Inactive - No recent activity</Typography>
              </Box>
            </Box>
          </Paper>
        </>
      )}
    </Box>
  );
};

export default AgentStatus;
