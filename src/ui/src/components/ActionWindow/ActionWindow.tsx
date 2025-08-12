import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Paper,
  Chip,
  Alert,
  LinearProgress,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Card,
  CardContent,
  Grid
} from '@mui/material';
import {
  PlayArrow as ExecuteIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Schedule as PendingIcon,
  Security as SecurityIcon,
  Assessment as AssessmentIcon,
  Build as BuildIcon,
  Verified as VerifiedIcon
} from '@mui/icons-material';

interface ActionWindowProps {
  open: boolean;
  onClose: () => void;
  action: string;
  exception: any;
  actionType: 'execute' | 'review';
}

interface WorkflowStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  details?: string;
  timestamp?: string;
  icon: React.ReactNode;
}

const ActionWindow: React.FC<ActionWindowProps> = ({
  open,
  onClose,
  action,
  exception,
  actionType
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      initializeWorkflow();
    }
  }, [open, actionType]);

  const initializeWorkflow = () => {
    // Find the workflow trigger for this action
    const workflowTrigger = exception?.workflowTriggers?.find(
      (trigger: any) => trigger.action === action || trigger.title === action
    );

    if (workflowTrigger) {
      // Use workflow-specific steps if available
      const steps: WorkflowStep[] = [
        {
          id: 'initialization',
          title: 'Workflow Initialization',
          description: 'Initializing workflow execution',
          status: 'pending',
          icon: <AssessmentIcon />
        },
        {
          id: 'validation',
          title: 'Parameter Validation',
          description: 'Validating workflow parameters and permissions',
          status: 'pending',
          icon: <SecurityIcon />
        },
        {
          id: 'execution',
          title: workflowTrigger.title || 'Action Execution',
          description: workflowTrigger.description || 'Executing the recommended action',
          status: 'pending',
          icon: <BuildIcon />
        },
        {
          id: 'verification',
          title: 'Result Verification',
          description: 'Verifying execution results and updating records',
          status: 'pending',
          icon: <VerifiedIcon />
        }
      ];
      
      setWorkflowSteps(steps);
    } else {
      // Fallback to generic steps
      const steps: WorkflowStep[] = actionType === 'execute' 
        ? [
            {
              id: 'validation',
              title: 'Action Validation',
              description: 'Validating action parameters and permissions',
              status: 'pending',
              icon: <AssessmentIcon />
            },
            {
              id: 'security',
              title: 'Security Check',
              description: 'Performing security and compliance checks',
              status: 'pending',
              icon: <SecurityIcon />
            },
            {
              id: 'execution',
              title: 'Action Execution',
              description: 'Executing the recommended action',
              status: 'pending',
              icon: <BuildIcon />
            },
            {
              id: 'verification',
              title: 'Result Verification',
              description: 'Verifying action results and impact',
              status: 'pending',
              icon: <VerifiedIcon />
            }
          ]
        : [
            {
              id: 'analysis',
              title: 'Action Analysis',
              description: 'Analyzing action details and implications',
              status: 'pending',
              icon: <AssessmentIcon />
            },
            {
              id: 'review',
              title: 'Human Review',
              description: 'Manual review and approval process',
              status: 'pending',
              icon: <SecurityIcon />
            },
            {
              id: 'approval',
              title: 'Approval Workflow',
              description: 'Routing for necessary approvals',
              status: 'pending',
              icon: <VerifiedIcon />
            }
          ];
      
      setWorkflowSteps(steps);
    }
    
    setCurrentStep(0);
    setResult(null);
    setError(null);
  };

  const executeAction = async () => {
    setIsExecuting(true);
    setError(null);

    try {
      // Find the workflow trigger for this action
      const workflowTrigger = exception?.workflowTriggers?.find(
        (trigger: any) => trigger.action === action || trigger.title === action
      );

      if (!workflowTrigger) {
        throw new Error('No workflow trigger found for this action');
      }

      // Call the workflow API
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/workflows/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
          workflow_id: workflowTrigger.workflow_id,
          parameters: {
            ...workflowTrigger.parameters,
            action_type: actionType,
            exception_id: exception.id,
            action_description: action
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start workflow');
      }

      const result = await response.json();
      const workflowId = result.workflow_id;

      // Poll for workflow status
      let workflowStatus = null;
      let attempts = 0;
      const maxAttempts = 60; // 5 minutes with 5-second intervals

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 5000)); // 5-second intervals
        
        const statusResponse = await fetch(`/api/v1/workflows/status/${workflowId}`, {
          headers: {
            ...(token && { Authorization: `Bearer ${token}` })
          }
        });

        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          workflowStatus = statusData.workflow;
          
          // Update workflow steps based on status
          if (workflowStatus.steps && workflowStatus.steps.length > 0) {
            setWorkflowSteps(workflowStatus.steps.map((step: any) => ({
              id: step.id || step.title,
              title: step.title,
              description: step.description,
              status: step.status,
              details: step.details,
              timestamp: step.timestamp,
              icon: getStepIcon({ 
                id: step.id || step.title,
                title: step.title,
                description: step.description,
                status: step.status,
                icon: undefined
              })
            })));
          }

          if (workflowStatus.status === 'completed' || workflowStatus.status === 'failed') {
            break;
          }
        }
        
        attempts++;
      }

      if (workflowStatus?.status === 'completed') {
        setResult({
          success: true,
          action_id: workflowId,
          status: 'completed',
          message: `Successfully ${actionType}d: ${action}`,
          execution_time_ms: workflowStatus.execution_time_ms || 0,
          result_data: workflowStatus.result_data || {}
        });
      } else {
        throw new Error('Workflow execution failed or timed out');
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execution failed');
      
      // Mark current step as failed
      setWorkflowSteps(prev => prev.map((step, index) => 
        index === currentStep 
          ? { ...step, status: 'failed', timestamp: new Date().toISOString() }
          : step
      ));
    } finally {
      setIsExecuting(false);
    }
  };

  const getStepDetails = (stepId: string, type: string): string => {
    const details = {
      execute: {
        validation: 'Action parameters validated successfully. All required fields present.',
        security: 'Security checks passed. User has sufficient permissions.',
        execution: 'Action executed successfully. Database updated with changes.',
        verification: 'Results verified. All changes applied correctly.'
      },
      review: {
        analysis: 'Action analyzed. Impact assessment completed.',
        review: 'Manual review completed. Action approved by reviewer.',
        approval: 'Approval workflow completed. Action ready for execution.'
      }
    };

    if (type === 'execute') {
      return (details.execute as any)[stepId] || 'Step completed successfully.';
    } else if (type === 'review') {
      return (details.review as any)[stepId] || 'Step completed successfully.';
    }
    
    return 'Step completed successfully.';
  };

  const getStepIcon = (step: WorkflowStep) => {
    switch (step.status) {
      case 'completed':
        return <SuccessIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'running':
        return <PendingIcon color="primary" />;
      default:
        return step.icon;
    }
  };

  const getStepColor = (step: WorkflowStep) => {
    switch (step.status) {
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

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          {actionType === 'execute' ? <ExecuteIcon color="primary" /> : <InfoIcon color="info" />}
          <Typography variant="h6">
            {actionType === 'execute' ? 'Execute Action' : 'Review Action'}
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* Action Details */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Action Details
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Action Description
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {action}
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Exception Type
              </Typography>
              <Chip 
                label={exception?.breakType || 'Unknown'} 
                color="warning" 
                size="small" 
                sx={{ mb: 1 }}
              />
              <Typography variant="body2" color="text.secondary">
                Severity
              </Typography>
              <Chip 
                label={exception?.severity || 'Medium'} 
                color={exception?.severity === 'high' ? 'error' : 'warning'} 
                size="small"
              />
            </Box>
          </Box>
        </Paper>

        {/* Workflow Steps */}
        <Typography variant="h6" gutterBottom>
          {actionType === 'execute' ? 'Execution Workflow' : 'Review Workflow'}
        </Typography>
        
        <Stepper activeStep={currentStep} orientation="vertical">
          {workflowSteps.map((step, index) => (
            <Step key={step.id}>
              <StepLabel
                icon={getStepIcon(step)}
                color={getStepColor(step)}
              >
                <Typography variant="subtitle1">
                  {step.title}
                </Typography>
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {step.description}
                </Typography>
                
                {step.status === 'running' && (
                  <Box sx={{ width: '100%', mb: 2 }}>
                    <LinearProgress />
                  </Box>
                )}
                
                {step.details && (
                  <Alert severity="info" sx={{ mt: 1 }}>
                    {step.details}
                  </Alert>
                )}
                
                {step.timestamp && (
                  <Typography variant="caption" color="text.secondary">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </Typography>
                )}
              </StepContent>
            </Step>
          ))}
        </Stepper>

        {/* Results */}
        {result && (
          <Paper sx={{ p: 2, mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Execution Results
            </Typography>
            <Alert severity="success" sx={{ mb: 2 }}>
              {result.message}
            </Alert>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Action ID
                </Typography>
                <Typography variant="body1">
                  {result.action_id}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Execution Time
                </Typography>
                <Typography variant="body1">
                  {result.execution_time_ms}ms
                </Typography>
              </Box>
            </Box>
            
            {result.result_data?.changes_applied && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Changes Applied:
                </Typography>
                <List dense>
                  {result.result_data.changes_applied.map((change: string, index: number) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <SuccessIcon color="success" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText primary={change} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Paper>
        )}

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={isExecuting}>
          Close
        </Button>
        {!isExecuting && !result && (
          <Button 
            onClick={executeAction}
            variant="contained"
            startIcon={<ExecuteIcon />}
          >
            {actionType === 'execute' ? 'Execute Action' : 'Start Review'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ActionWindow;
