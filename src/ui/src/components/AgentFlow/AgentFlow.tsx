import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  IconButton,
  Button,
  Alert,
  CircularProgress,
  Grid,
  Collapse,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  LinearProgress
} from '@mui/material';
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
} from '@mui/lab';
import {
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Schedule as ScheduleIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

interface FlowEntry {
  id: string;
  action_type: string;
  action_description?: string;
  action_data?: any;
  entity_type?: string;
  entity_id?: string;
  processing_time_ms?: number;
  ai_model_used?: string;
  ai_confidence_score?: number;
  ai_reasoning?: any;
  severity: string;
  is_successful: boolean;
  error_message?: string;
  created_at: string;
}

interface AgentFlow {
  session_id: string;
  flow_entries: FlowEntry[];
  total_steps: number;
  successful_steps: number;
  failed_steps: number;
  start_time?: string;
  end_time?: string;
  total_processing_time_ms: number;
}

interface AgentStatus {
  status: 'active' | 'idle' | 'inactive';
  last_activity?: string;
  last_action?: string;
  success_rate: 'high' | 'low' | 'unknown';
}

interface AgentFlowProps {
  sessionId?: string;
}

const AgentFlow: React.FC<AgentFlowProps> = ({ sessionId }) => {
  const [expandedFlow, setExpandedFlow] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch agent flow data
  const { data: flowData, isLoading, error, refetch } = useQuery({
    queryKey: ['agent-flow', sessionId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (sessionId) {
        params.append('session_id', sessionId);
      }
      params.append('limit', '10');

      const response = await fetch(`/api/v1/logs/agents/flow?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch agent flow');
      }
      return response.json();
    },
    refetchInterval: autoRefresh ? 10000 : false, // Refetch every 10 seconds if auto-refresh is enabled
  });

  // Fetch agent status
  const { data: statusData } = useQuery({
    queryKey: ['agent-status'],
    queryFn: async () => {
      const response = await fetch('/api/v1/logs/agents/status');
      if (!response.ok) {
        throw new Error('Failed to fetch agent status');
      }
      return response.json();
    },
    refetchInterval: autoRefresh ? 5000 : false, // Refetch every 5 seconds if auto-refresh is enabled
  });

  const handleFlowExpansion = (sessionId: string) => {
    setExpandedFlow(expandedFlow === sessionId ? null : sessionId);
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'data_ingested':
      case 'data_normalized':
      case 'data_validated':
        return <InfoIcon />;
      case 'match_created':
      case 'match_approved':
        return <SuccessIcon />;
      case 'match_rejected':
      case 'match_attempted':
        return <WarningIcon />;
      case 'exception_detected':
      case 'exception_classified':
        return <ErrorIcon />;
      case 'exception_resolved':
        return <SuccessIcon />;
      case 'ai_analysis_completed':
      case 'ai_suggestion_generated':
        return <InfoIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const getActionColor = (actionType: string, isSuccessful: boolean) => {
    if (!isSuccessful) return 'error';
    
    switch (actionType) {
      case 'data_ingested':
      case 'data_normalized':
      case 'data_validated':
        return 'primary';
      case 'match_created':
      case 'match_approved':
      case 'exception_resolved':
        return 'success';
      case 'match_rejected':
      case 'match_attempted':
        return 'warning';
      case 'exception_detected':
      case 'exception_classified':
        return 'error';
      case 'ai_analysis_completed':
      case 'ai_suggestion_generated':
        return 'info';
      default:
        return 'default';
    }
  };

  const getTimelineDotColor = (actionType: string, isSuccessful: boolean) => {
    if (!isSuccessful) return 'error';
    
    switch (actionType) {
      case 'data_ingested':
      case 'data_normalized':
      case 'data_validated':
        return 'primary';
      case 'match_created':
      case 'match_approved':
      case 'exception_resolved':
        return 'success';
      case 'match_rejected':
      case 'match_attempted':
        return 'warning';
      case 'exception_detected':
      case 'exception_classified':
        return 'error';
      case 'ai_analysis_completed':
      case 'ai_suggestion_generated':
        return 'info';
      default:
        return 'grey';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const renderAgentStatus = () => {
    if (!statusData?.agents) return null;

    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Agent Status
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {Object.entries(statusData.agents).map(([agentName, status]) => {
              const agentStatus = status as AgentStatus;
              return (
              <Box key={agentName} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={agentName.replace('_', ' ').toUpperCase()}
                  size="small"
                  color={agentStatus.status === 'active' ? 'success' : agentStatus.status === 'idle' ? 'warning' : 'default'}
                  variant={agentStatus.status === 'active' ? 'filled' : 'outlined'}
                />
                <Chip
                  label={agentStatus.status}
                  size="small"
                  color={agentStatus.status === 'active' ? 'success' : agentStatus.status === 'idle' ? 'warning' : 'default'}
                />
                {agentStatus.success_rate !== 'unknown' && (
                  <Chip
                    label={agentStatus.success_rate}
                    size="small"
                    color={agentStatus.success_rate === 'high' ? 'success' : 'error'}
                  />
                )}
              </Box>
            );
            })}
          </Box>
        </CardContent>
      </Card>
    );
  };

  const renderFlowTimeline = (flow: AgentFlow) => {
    return (
      <Timeline position="alternate">
        {flow.flow_entries.map((entry, index) => (
          <TimelineItem key={entry.id}>
            <TimelineOppositeContent sx={{ m: 'auto 0' }} variant="body2" color="text.secondary">
              {formatTimestamp(entry.created_at)}
            </TimelineOppositeContent>
            <TimelineSeparator>
              <TimelineDot color={getTimelineDotColor(entry.action_type, entry.is_successful)}>
                {getActionIcon(entry.action_type)}
              </TimelineDot>
              {index < flow.flow_entries.length - 1 && <TimelineConnector />}
            </TimelineSeparator>
            <TimelineContent sx={{ py: '12px', px: 2 }}>
              <Card variant="outlined">
                <CardContent sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Chip
                      label={entry.action_type.replace('_', ' ').toUpperCase()}
                      size="small"
                      color={getActionColor(entry.action_type, entry.is_successful)}
                    />
                    <Chip
                      icon={entry.is_successful ? <SuccessIcon /> : <ErrorIcon />}
                      label={entry.is_successful ? 'Success' : 'Failed'}
                      size="small"
                      color={entry.is_successful ? 'success' : 'error'}
                    />
                  </Box>
                  {entry.action_description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {entry.action_description}
                    </Typography>
                  )}
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {entry.processing_time_ms && (
                      <Chip
                        icon={<SpeedIcon />}
                        label={formatDuration(entry.processing_time_ms)}
                        size="small"
                        variant="outlined"
                      />
                    )}
                    {entry.ai_model_used && (
                      <Chip
                        label={entry.ai_model_used}
                        size="small"
                        variant="outlined"
                      />
                    )}
                    {entry.ai_confidence_score && (
                      <Chip
                        label={`${(entry.ai_confidence_score * 100).toFixed(1)}%`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                  {entry.error_message && (
                    <Alert severity="error" sx={{ mt: 1 }}>
                      <Typography variant="body2">
                        {entry.error_message}
                      </Typography>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </TimelineContent>
          </TimelineItem>
        ))}
      </Timeline>
    );
  };

  const renderFlowSummary = (flow: AgentFlow) => {
    const successRate = (flow.successful_steps / flow.total_steps) * 100;
    const avgProcessingTime = flow.total_processing_time_ms / flow.total_steps;

    return (
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ flex: '1 1 200px' }}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" color="primary">
                  {flow.total_steps}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Steps
                </Typography>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: '1 1 200px' }}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" color="success.main">
                  {flow.successful_steps}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Successful
                </Typography>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: '1 1 200px' }}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" color="error.main">
                  {flow.failed_steps}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Failed
                </Typography>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: '1 1 200px' }}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h6" color="info.main">
                  {formatDuration(avgProcessingTime)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Time
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </Box>
        
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Success Rate
          </Typography>
          <LinearProgress
            variant="determinate"
            value={successRate}
            color={successRate >= 80 ? 'success' : successRate >= 60 ? 'warning' : 'error'}
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Typography variant="caption" color="text.secondary">
            {successRate.toFixed(1)}% ({flow.successful_steps}/{flow.total_steps})
          </Typography>
        </Box>
      </Box>
    );
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Agent Flow Control
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={autoRefresh ? <PauseIcon /> : <PlayIcon />}
            onClick={() => setAutoRefresh(!autoRefresh)}
            size="small"
          >
            {autoRefresh ? 'Pause' : 'Auto-refresh'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => refetch()}
            size="small"
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Agent Status */}
      {renderAgentStatus()}

      {/* Content */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error">
          Failed to load agent flow data. Please try again.
        </Alert>
      ) : flowData?.agent_flows?.length === 0 ? (
        <Alert severity="info">
          No agent flows found. Upload some data to see the agent flow in action.
        </Alert>
      ) : (
        <Box>
          {flowData?.agent_flows?.map((flow: AgentFlow) => (
            <Accordion
              key={flow.session_id}
              expanded={expandedFlow === flow.session_id}
              onChange={() => handleFlowExpansion(flow.session_id)}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    Session: {flow.session_id}
                  </Typography>
                  <Chip
                    label={`${flow.successful_steps}/${flow.total_steps}`}
                    color={flow.successful_steps === flow.total_steps ? 'success' : 'warning'}
                    size="small"
                  />
                  <Chip
                    icon={<ScheduleIcon />}
                    label={flow.start_time ? formatTimestamp(flow.start_time) : 'N/A'}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    icon={<SpeedIcon />}
                    label={formatDuration(flow.total_processing_time_ms)}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {renderFlowSummary(flow)}
                <Divider sx={{ my: 2 }} />
                {renderFlowTimeline(flow)}
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default AgentFlow;
