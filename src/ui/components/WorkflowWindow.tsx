import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  LinearProgress,
  Typography,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Paper,
  Divider,
  Alert,
  IconButton
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Close as CloseIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon
} from '@mui/icons-material';

interface WorkflowStep {
  timestamp: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
}

interface WorkflowData {
  id: string;
  type: string;
  status: 'initializing' | 'running' | 'completed' | 'failed';
  progress: number;
  current_step: string | null;
  started_at: string;
  completed_at?: string;
  parameters: Record<string, any>;
  logs: WorkflowStep[];
  error?: string;
}

interface WorkflowWindowProps {
  open: boolean;
  onClose: () => void;
  workflowData: {
    workflow_id: string;
    title: string;
    description: string;
    parameters: Record<string, any>;
  };
}

const WorkflowWindow: React.FC<WorkflowWindowProps> = ({
  open,
  onClose,
  workflowData
}) => {
  const [workflow, setWorkflow] = useState<WorkflowData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'primary';
      default:
        return 'default';
    }
  };

  const getStepIcon = (level: string) => {
    switch (level) {
      case 'success':
        return <CheckIcon color="success" fontSize="small" />;
      case 'error':
        return <ErrorIcon color="error" fontSize="small" />;
      case 'warning':
        return <WarningIcon color="warning" fontSize="small" />;
      default:
        return <InfoIcon color="info" fontSize="small" />;
    }
  };

  const executeWorkflow = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/workflows/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
          workflow_id: workflowData.workflow_id,
          parameters: workflowData.parameters
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start workflow');
      }

      const result = await response.json();
      setWorkflow({
        id: result.workflow_id,
        type: workflowData.workflow_id,
        status: 'initializing',
        progress: 0,
        current_step: null,
        started_at: new Date().toISOString(),
        parameters: workflowData.parameters,
        logs: []
      });

      // Start polling for status
      pollWorkflowStatus(result.workflow_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute workflow');
    } finally {
      setLoading(false);
    }
  };

  const pollWorkflowStatus = async (workflowId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/v1/workflows/status/${workflowId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined
        });

        if (!response.ok) {
          throw new Error('Failed to get workflow status');
        }

        const result = await response.json();
        setWorkflow(result.workflow);

        // Stop polling if workflow is completed or failed
        if (result.workflow.status === 'completed' || result.workflow.status === 'failed') {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Error polling workflow status:', err);
        clearInterval(pollInterval);
      }
    }, 1000); // Poll every second
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatDuration = (startedAt: string, completedAt?: string) => {
    const start = new Date(startedAt);
    const end = completedAt ? new Date(completedAt) : new Date();
    const duration = Math.round((end.getTime() - start.getTime()) / 1000);
    return `${duration}s`;
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          minHeight: '600px',
          maxHeight: '80vh'
        }
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            {workflowData.title}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box mb={2}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {workflowData.description}
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!workflow && !loading && (
          <Box textAlign="center" py={4}>
            <Typography variant="h6" gutterBottom>
              Ready to Execute
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Click the button below to start the workflow
            </Typography>
            <Button
              variant="contained"
              startIcon={<PlayIcon />}
              onClick={executeWorkflow}
              sx={{ mt: 2 }}
            >
              Start Workflow
            </Button>
          </Box>
        )}

        {loading && (
          <Box textAlign="center" py={4}>
            <Typography variant="h6" gutterBottom>
              Starting Workflow...
            </Typography>
            <LinearProgress sx={{ mt: 2 }} />
          </Box>
        )}

        {workflow && (
          <Box>
            {/* Workflow Status */}
            <Paper sx={{ p: 2, mb: 2 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="subtitle1" fontWeight="bold">
                  Workflow Status
                </Typography>
                <Chip
                  label={workflow.status.toUpperCase()}
                  color={getStatusColor(workflow.status) as any}
                  size="small"
                />
              </Box>
              
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Started: {formatTimestamp(workflow.started_at)}
                </Typography>
                {workflow.completed_at && (
                  <Typography variant="body2" color="text.secondary">
                    Duration: {formatDuration(workflow.started_at, workflow.completed_at)}
                  </Typography>
                )}
              </Box>

              <LinearProgress
                variant="determinate"
                value={workflow.progress}
                sx={{ height: 8, borderRadius: 4 }}
              />
              
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Progress: {workflow.progress}%
              </Typography>
            </Paper>

            {/* Current Step */}
            {workflow.current_step && (
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  Current Step
                </Typography>
                <Typography variant="body2">
                  {workflow.current_step}
                </Typography>
              </Paper>
            )}

            {/* Workflow Logs */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                Execution Logs
              </Typography>
              
              <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
                {workflow.logs.map((step, index) => (
                  <ListItem key={index} sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      {getStepIcon(step.level)}
                    </ListItemIcon>
                    <ListItemText
                      primary={step.message}
                      secondary={formatTimestamp(step.timestamp)}
                      primaryTypographyProps={{ variant: 'body2' }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItem>
                ))}
                
                {workflow.logs.length === 0 && (
                  <ListItem>
                    <ListItemText
                      primary="No logs available yet"
                      primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
                    />
                  </ListItem>
                )}
              </List>
            </Paper>

            {/* Error Display */}
            {workflow.error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>Error:</strong> {workflow.error}
                </Typography>
              </Alert>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Close
        </Button>
        {workflow && workflow.status === 'running' && (
          <Button
            variant="outlined"
            color="warning"
            startIcon={<StopIcon />}
            disabled
          >
            Stop Workflow
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default WorkflowWindow;
