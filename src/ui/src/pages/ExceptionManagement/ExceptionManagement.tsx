import React, { useState, useEffect } from 'react';
import WorkflowWindow from '../../components/WorkflowWindow';
import { 
  Box, 
  Typography, 
  Paper, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  TablePagination, 
  Chip, 
  Button, 
  TextField, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  Card, 
  CardContent, 
  IconButton, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Alert, 
  LinearProgress, 
  Tooltip,
  Snackbar
} from '@mui/material';
import { 
  FilterList as FilterIcon, 
  Sort as SortIcon, 
  Visibility as ViewIcon, 
  CheckCircle as ResolveIcon, 
  Warning as WarningIcon, 
  Error as ErrorIcon, 
  Info as InfoIcon, 
  Refresh as RefreshIcon, 
  Download as DownloadIcon,
  PlayArrow as PlayArrowIcon,
  Visibility as VisibilityIcon,
  Launch as LaunchIcon
} from '@mui/icons-material';

interface Exception {
  id: string;
  transactionId: string;
  breakType: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  description: string;
  createdAt: string;
  assignedTo?: string;
  priority: number;
  aiReasoning?: string;
  aiSuggestedActions?: string[];
  breakDetails?: any;
  analysis?: any;
  detailedDifferences?: any;
  workflowTriggers?: any[];
}

const ExceptionManagement: React.FC = () => {
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [breakTypeFilter, setBreakTypeFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'breakType' | 'severity' | 'status' | 'createdAt'>('createdAt');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedException, setSelectedException] = useState<Exception | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [resolveDialogOpen, setResolveDialogOpen] = useState(false);
  const [actionSnackbar, setActionSnackbar] = useState<{open: boolean, message: string, severity: 'success' | 'error' | 'info'}>({
    open: false,
    message: '',
    severity: 'info'
  });
  const [workflowWindowOpen, setWorkflowWindowOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null);
  // 1. Add state for review modal
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<string | null>(null);
  const [reviewDetails, setReviewDetails] = useState<any>(null);

  const refreshExceptions = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ skip: '0', limit: '100' });
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/exceptions/?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      if (!response.ok) {
        throw new Error('Failed to fetch exceptions');
      }
      const data = await response.json();
      const items = Array.isArray(data?.exceptions) ? data.exceptions : [];
      const mapped: Exception[] = items.map((e: any) => ({
        id: String(e.id),
        transactionId: String(e.transaction_id || ''),
        breakType: String(e.break_type || ''),
        severity: String(e.severity || '').toLowerCase() as Exception['severity'],
        status: String(e.status || '').toLowerCase() as Exception['status'],
        description: e.break_details?.description || e.ai_reasoning || `${e.break_type || 'Exception'}`,
        createdAt: String(e.created_at || new Date().toISOString()),
        assignedTo: e.assigned_to || undefined,
        priority: Number(e.priority ?? 2),
        aiReasoning: e.ai_reasoning,
        aiSuggestedActions: e.ai_suggested_actions,
        breakDetails: e.break_details,
        analysis: e.break_details?.analysis,
        detailedDifferences: e.detailed_differences,
        workflowTriggers: e.workflow_triggers
      }));
      setExceptions(mapped);
    } catch (err) {
      setError('Failed to load exceptions');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshExceptions();
  }, []);

  const filteredExceptions = exceptions.filter(exception => {
    const matchesSearch = exception.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         exception.transactionId.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSeverity = severityFilter === 'all' || exception.severity === severityFilter;
    const matchesStatus = statusFilter === 'all' || exception.status === statusFilter;
    const matchesBreakType = breakTypeFilter === 'all' || exception.breakType === breakTypeFilter;
    
    return matchesSearch && matchesSeverity && matchesStatus && matchesBreakType;
  });

  const sortedExceptions = [...filteredExceptions].sort((a, b) => {
    const aValue = a[sortBy];
    const bValue = b[sortBy];
    
    if (sortBy === 'createdAt') {
      const aDate = new Date(aValue as string).getTime();
      const bDate = new Date(bValue as string).getTime();
      return sortOrder === 'asc' ? aDate - bDate : bDate - aDate;
    }
    
    if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const paginatedExceptions = sortedExceptions.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleSort = (field: 'breakType' | 'severity' | 'status' | 'createdAt') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'error';
      case 'in_progress': return 'warning';
      case 'resolved': return 'success';
      case 'closed': return 'default';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <ErrorIcon />;
      case 'high': return <WarningIcon />;
      case 'medium': return <InfoIcon />;
      case 'low': return <InfoIcon />;
      default: return <InfoIcon />;
    }
  };

  const handleResolveException = async () => {
    if (selectedException) {
      try {
        setExceptions(prev => prev.map(ex => 
          ex.id === selectedException.id ? { ...ex, status: 'resolved' } : ex
        ));
        setResolveDialogOpen(false);
        setSelectedException(null);
      } catch (error) {
        console.error('Failed to resolve exception:', error);
      }
    }
  };

  const handleExecuteAction = async (action: string, exception: Exception) => {
    try {
      setActionSnackbar({
        open: true,
        message: `🤖 Executing: ${action}`,
        severity: 'info'
      });

      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          action_type: 'execute',
          action_description: action,
          exception_id: exception.id,
          action_data: {
            exception_type: exception.breakType,
            severity: exception.severity,
            action: action
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to execute action');
      }

      const result = await response.json();
      
      setActionSnackbar({
        open: true,
        message: `✅ ${result.message}`,
        severity: 'success'
      });
      
      // Refresh exceptions to show updated status
      refreshExceptions();

    } catch (error) {
      setActionSnackbar({
        open: true,
        message: `❌ Failed to execute: ${action}`,
        severity: 'error'
      });
    }
  };

  const handleReviewAction = async (action: string, exception: Exception) => {
    try {
      setActionSnackbar({
        open: true,
        message: `👤 Reviewing: ${action}`,
        severity: 'info'
      });

      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          action_type: 'review',
          action_description: action,
          exception_id: exception.id,
          action_data: {
            exception_type: exception.breakType,
            severity: exception.severity,
            action: action
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to review action');
      }

      const result = await response.json();
      
      setActionSnackbar({
        open: true,
        message: `📋 ${result.message}`,
        severity: 'success'
      });

    } catch (error) {
      setActionSnackbar({
        open: true,
        message: `❌ Review failed for: ${action}`,
        severity: 'error'
      });
    }
  };

  const handleExecuteWorkflow = (workflow: any) => {
    setSelectedWorkflow(workflow);
    setWorkflowWindowOpen(true);
  };

  const getBreakTypeStats = () => {
    const stats = filteredExceptions.reduce((acc, exception) => {
      acc[exception.breakType] = (acc[exception.breakType] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    return stats;
  };

  const breakTypeStats = getBreakTypeStats();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LinearProgress sx={{ width: '50%' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="flex-end" alignItems="center" sx={{ mb: 2 }}>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={refreshExceptions}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
          >
            Export
          </Button>
        </Box>
      </Box>

      {/* Statistics Cards */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 3 }}>
        <Card sx={{ flex: '1', minWidth: '200px' }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Total Exceptions
            </Typography>
            <Typography variant="h4">
              {filteredExceptions.length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1', minWidth: '200px' }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Open
            </Typography>
            <Typography variant="h4" color="error.main">
              {filteredExceptions.filter(e => e.status === 'open').length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1', minWidth: '200px' }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              In Progress
            </Typography>
            <Typography variant="h4" color="warning.main">
              {filteredExceptions.filter(e => e.status === 'in_progress').length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1', minWidth: '200px' }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Resolved
            </Typography>
            <Typography variant="h4" color="success.main">
              {filteredExceptions.filter(e => e.status === 'resolved').length}
            </Typography>
          </CardContent>
        </Card>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <TextField
            label="Search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by description or transaction ID..."
            sx={{ minWidth: '300px' }}
          />
          <FormControl sx={{ minWidth: '150px' }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              label="Severity"
            >
              <MenuItem value="all">All Severities</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="low">Low</MenuItem>
            </Select>
          </FormControl>
          <FormControl sx={{ minWidth: '150px' }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              label="Status"
            >
              <MenuItem value="all">All Statuses</MenuItem>
              <MenuItem value="open">Open</MenuItem>
              <MenuItem value="in_progress">In Progress</MenuItem>
              <MenuItem value="resolved">Resolved</MenuItem>
              <MenuItem value="closed">Closed</MenuItem>
            </Select>
          </FormControl>
          <FormControl sx={{ minWidth: '150px' }}>
            <InputLabel>Break Type</InputLabel>
            <Select
              value={breakTypeFilter}
              onChange={(e) => setBreakTypeFilter(e.target.value)}
              label="Break Type"
            >
              <MenuItem value="all">All Types</MenuItem>
              <MenuItem value="Security ID">Security ID</MenuItem>
              <MenuItem value="Fixed Income Coupon">Fixed Income Coupon</MenuItem>
              <MenuItem value="Market Price">Market Price</MenuItem>
              <MenuItem value="Trade vs Settlement Date">Trade vs Settlement Date</MenuItem>
              <MenuItem value="FX Rate">FX Rate</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<FilterIcon />}
            onClick={() => {
              setSearchTerm('');
              setSeverityFilter('all');
              setStatusFilter('all');
              setBreakTypeFilter('all');
            }}
          >
            Clear Filters
          </Button>
        </Box>
      </Paper>

      {/* Break Type Distribution */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Break Type Distribution
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {Object.entries(breakTypeStats).map(([breakType, count]) => (
              <Chip
                key={breakType}
                label={`${breakType}: ${count}`}
                variant="outlined"
                size="small"
              />
            ))}
          </Box>
        </CardContent>
      </Card>

      {/* Exceptions Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <Button
                    startIcon={<SortIcon />}
                    onClick={() => handleSort('breakType')}
                    sx={{ textTransform: 'none' }}
                  >
                    Break Type
                  </Button>
                </TableCell>
                <TableCell>Description</TableCell>
                <TableCell>
                  <Button
                    startIcon={<SortIcon />}
                    onClick={() => handleSort('severity')}
                    sx={{ textTransform: 'none' }}
                  >
                    Severity
                  </Button>
                </TableCell>
                <TableCell>
                  <Button
                    startIcon={<SortIcon />}
                    onClick={() => handleSort('status')}
                    sx={{ textTransform: 'none' }}
                  >
                    Status
                  </Button>
                </TableCell>
                <TableCell>Transaction ID</TableCell>
                <TableCell>
                  <Button
                    startIcon={<SortIcon />}
                    onClick={() => handleSort('createdAt')}
                    sx={{ textTransform: 'none' }}
                  >
                    Created
                  </Button>
                </TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedExceptions.map((exception) => (
                <TableRow key={exception.id} hover>
                  <TableCell>
                    <Chip
                      label={exception.breakType}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                      {exception.description}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={getSeverityIcon(exception.severity)}
                      label={exception.severity}
                      color={getSeverityColor(exception.severity) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={exception.status}
                      color={getStatusColor(exception.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {exception.transactionId}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(exception.createdAt).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={1}>
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => {
                            setSelectedException(exception);
                            setDetailDialogOpen(true);
                          }}
                        >
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                      {exception.status !== 'resolved' && (
                        <Tooltip title="Resolve">
                          <IconButton
                            size="small"
                            color="success"
                            onClick={() => {
                              setSelectedException(exception);
                              setResolveDialogOpen(true);
                            }}
                          >
                            <ResolveIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={filteredExceptions.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
        />
      </Paper>

      {/* Detail Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Exception Details
        </DialogTitle>
        <DialogContent>
          {selectedException && (
            <Box>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                <Box sx={{ flex: '1', minWidth: '300px' }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Break Type
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    {selectedException.breakType}
                  </Typography>
                </Box>
                <Box sx={{ flex: '1', minWidth: '300px' }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Transaction ID
                  </Typography>
                  <Typography variant="body1" fontFamily="monospace" sx={{ mb: 2 }}>
                    {selectedException.transactionId}
                  </Typography>
                </Box>
                <Box sx={{ flex: '1', minWidth: '300px' }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Description
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    {selectedException.description}
                  </Typography>
                </Box>
                <Box sx={{ flex: '1', minWidth: '300px' }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Severity
                  </Typography>
                  <Chip
                    icon={getSeverityIcon(selectedException.severity)}
                    label={selectedException.severity}
                    color={getSeverityColor(selectedException.severity) as any}
                    sx={{ mb: 2 }}
                  />
                </Box>
                <Box sx={{ flex: '1', minWidth: '300px' }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Status
                  </Typography>
                  <Chip
                    label={selectedException.status}
                    color={getStatusColor(selectedException.status) as any}
                    sx={{ mb: 2 }}
                  />
                </Box>
                <Box sx={{ flex: '1', minWidth: '300px' }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Created
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    {new Date(selectedException.createdAt).toLocaleString()}
                  </Typography>
                </Box>
                <Box sx={{ flex: '1', minWidth: '300px' }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Priority
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    {selectedException.priority}
                  </Typography>
                </Box>
                {selectedException.assignedTo && (
                  <Box sx={{ flex: '1', minWidth: '300px' }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Assigned To
                    </Typography>
                    <Typography variant="body1">
                      {selectedException.assignedTo}
                    </Typography>
                  </Box>
                )}
              </Box>
              
              {/* Detailed Differences Section - MOVED BEFORE AI ANALYSIS */}
              {selectedException.detailedDifferences && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" sx={{ mb: 2, color: 'error.main' }}>
                    Detailed Differences
                  </Typography>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                        {Object.entries(selectedException.detailedDifferences).map(([key, value]) => (
                          <Box key={key} sx={{ flex: '1', minWidth: '200px' }}>
                            <Typography variant="subtitle2" color="text.secondary">
                              {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                            </Typography>
                            <Typography variant="body1" fontFamily="monospace" color="error.main">
                              {typeof value === 'number' ? value.toFixed(4) : String(value)}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    </CardContent>
                  </Card>
                </Box>
              )}
              
              {/* AI Analysis Section - CLEANED UP */}
              {selectedException.aiReasoning && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
                    AI Analysis
                  </Typography>
                  <Card variant="outlined" sx={{ mb: 2 }}>
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Reasoning
                      </Typography>
                      <Typography variant="body1">
                        {selectedException.aiReasoning.replace(/[A-Za-z\s]+:\s*[\d.,]+/g, '').trim() || selectedException.aiReasoning}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
              )}
              
              {/* Integrated Recommended Actions and Workflows */}
              {((selectedException.aiSuggestedActions && selectedException.aiSuggestedActions.length > 0) || (selectedException.workflowTriggers && selectedException.workflowTriggers.length > 0)) && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" sx={{ mb: 2, color: 'success.main' }}>
                    Recommended Actions & Workflows
                  </Typography>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* AI Suggested Actions */}
                        {selectedException.aiSuggestedActions?.map((action, index) => (
                          <Box key={`action-${index}`} sx={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'space-between',
                            p: 2,
                            border: '1px solid #e0e0e0',
                            borderRadius: 1,
                            backgroundColor: '#fafafa'
                          }}>
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="body1" sx={{ mb: 0.5 }}>
                                {action}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                AI-generated recommendation
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              {/* Find matching workflow for this action */}
                              {selectedException.workflowTriggers && selectedException.workflowTriggers.find((w: any) => 
                                w.action === action || w.title === action
                              ) ? (
                                <Button
                                  size="small"
                                  variant="contained"
                                  color="success"
                                  onClick={() => handleExecuteWorkflow(
                                    selectedException.workflowTriggers!.find((w: any) => 
                                      w.action === action || w.title === action
                                    )!
                                  )}
                                  startIcon={<LaunchIcon />}
                                >
                                  Execute Workflow
                                </Button>
                              ) : (
                                <>
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    color="secondary"
                                    onClick={() => {
                                      setReviewAction(action);
                                      setReviewDetails({
                                        ...selectedException,
                                        aiReviewComment: `AI Review: This action is recommended based on detected break type (${selectedException.breakType}) and severity (${selectedException.severity}). Please verify all details before approval.`
                                      });
                                      setReviewModalOpen(true);
                                    }}
                                    startIcon={<VisibilityIcon />}
                                  >
                                    Review
                                  </Button>
                                </>
                              )}
                            </Box>
                          </Box>
                        ))}
                        
                        {/* Additional Workflows not covered by AI actions */}
                        {selectedException.workflowTriggers && selectedException.workflowTriggers.filter((workflow: any) => 
                          !selectedException.aiSuggestedActions?.some((action: string) => 
                            workflow.action === action || workflow.title === action
                          )
                        ).map((workflow: any, index: number) => (
                          <Box key={`workflow-${index}`} sx={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'space-between',
                            p: 2,
                            border: '1px solid #4caf50',
                            borderRadius: 1,
                            backgroundColor: '#f1f8e9'
                          }}>
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="body1" sx={{ mb: 0.5, color: 'success.main', fontWeight: 'bold' }}>
                                {workflow.title}
                              </Typography>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                                {workflow.description}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1 }}>
                                <Chip label={`Workflow ID: ${workflow.workflow_id}`} size="small" variant="outlined" />
                                <Chip label={`Action: ${workflow.action}`} size="small" variant="outlined" />
                              </Box>
                            </Box>
                            <Button
                              variant="contained"
                              color="success"
                              startIcon={<LaunchIcon />}
                              onClick={() => handleExecuteWorkflow(workflow)}
                              size="small"
                            >
                              Execute Workflow
                            </Button>
                          </Box>
                        ))}
                      </Box>
                      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e0e0e0' }}>
                        <Typography variant="body2" color="text.secondary">
                          💡 Workflows provide automated resolution steps. Click "Execute Workflow" for automated processing or "Execute/Review" for manual actions.
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Box>
              )}
              
              {/* Break Details Section */}
              {selectedException.breakDetails && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" sx={{ mb: 2, color: 'info.main' }}>
                    Break Details
                  </Typography>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                        {Object.entries(selectedException.breakDetails).map(([key, value]) => (
                          <Box key={key} sx={{ flex: '1', minWidth: '200px' }}>
                            <Typography variant="subtitle2" color="text.secondary">
                              {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                            </Typography>
                            <Typography variant="body1" fontFamily="monospace">
                              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    </CardContent>
                  </Card>
                </Box>
              )}
              
              {/* Historical Context Section */}
              {selectedException.analysis?.historical_context && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" sx={{ mb: 2, color: 'warning.main' }}>
                    Historical Context
                  </Typography>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                        {Object.entries(selectedException.analysis.historical_context).map(([key, value]) => (
                          <Box key={key} sx={{ flex: '1', minWidth: '200px' }}>
                            <Typography variant="subtitle2" color="text.secondary">
                              {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                            </Typography>
                            <Typography variant="body1">
                              {String(value)}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    </CardContent>
                  </Card>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Resolve Dialog */}
      <Dialog
        open={resolveDialogOpen}
        onClose={() => setResolveDialogOpen(false)}
      >
        <DialogTitle>
          Resolve Exception
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to mark this exception as resolved?
          </Typography>
          {selectedException && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {selectedException.description}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResolveDialogOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleResolveException} color="success" variant="contained">
            Resolve
          </Button>
        </DialogActions>
      </Dialog>

      {/* Action Snackbar */}
      <Snackbar
        open={actionSnackbar.open}
        autoHideDuration={4000}
        onClose={() => setActionSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={() => setActionSnackbar(prev => ({ ...prev, open: false }))} 
          severity={actionSnackbar.severity}
          sx={{ width: '100%' }}
        >
                  {actionSnackbar.message}
      </Alert>
    </Snackbar>

      {/* Workflow Window */}
      {selectedWorkflow && (
        <WorkflowWindow
          open={workflowWindowOpen}
          onClose={() => {
            setWorkflowWindowOpen(false);
            setSelectedWorkflow(null);
          }}
          workflowData={{
            workflow_id: selectedWorkflow.workflow_id,
            title: selectedWorkflow.title,
            description: selectedWorkflow.description,
            parameters: selectedWorkflow.parameters || {}
          }}
        />
      )}

      {/* Review Modal */}
      <Dialog open={reviewModalOpen} onClose={() => setReviewModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Review Action</DialogTitle>
        <DialogContent>
          {reviewDetails && (
            <Box>
              <Typography variant="subtitle2" color="text.secondary">Action</Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>{reviewAction}</Typography>
              <Typography variant="subtitle2" color="text.secondary">Break Type</Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>{reviewDetails.breakType}</Typography>
              <Typography variant="subtitle2" color="text.secondary">Severity</Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>{reviewDetails.severity}</Typography>
              <Typography variant="subtitle2" color="text.secondary">Description</Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>{reviewDetails.description}</Typography>
              <Typography variant="subtitle2" color="primary.main" sx={{ mt: 2 }}>AI Review Comment</Typography>
              <Paper sx={{ p: 2, mt: 1, backgroundColor: '#f5f5f5' }}>
                <Typography variant="body2">{reviewDetails.aiReviewComment}</Typography>
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewModalOpen(false)}>Close</Button>
          <Button variant="contained" color="success" onClick={() => setReviewModalOpen(false)}>Approve</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExceptionManagement;
