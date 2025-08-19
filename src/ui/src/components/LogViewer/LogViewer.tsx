import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
  CircularProgress,
  Tooltip,
  Collapse,
  Card,
  CardContent,
  Grid
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

interface LogEntry {
  id: string;
  level: string;
  message: string;
  component?: string;
  sub_component?: string;
  function_name?: string;
  line_number?: number;
  exception_type?: string;
  exception_message?: string;
  stack_trace?: string;
  execution_time_ms?: number;
  memory_usage_mb?: number;
  cpu_usage_percent?: number;
  created_at: string;
  log_data?: any;
}

interface AuditEntry {
  id: string;
  action_type: string;
  action_description?: string;
  action_data?: any;
  user_id?: string;
  user_name?: string;
  user_email?: string;
  user_role?: string;
  session_id?: string;
  ip_address?: string;
  user_agent?: string;
  entity_type?: string;
  entity_id?: string;
  entity_external_id?: string;
  processing_time_ms?: number;
  memory_usage_mb?: number;
  ai_model_used?: string;
  ai_confidence_score?: number;
  ai_reasoning?: any;
  regulatory_requirement?: string;
  compliance_category?: string;
  data_classification?: string;
  severity: string;
  is_successful: boolean;
  error_message?: string;
  error_code?: string;
  created_at: string;
}

interface LogViewerProps {
  type: 'system' | 'audit';
}

const LogViewer: React.FC<LogViewerProps> = ({ type }) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [filters, setFilters] = useState({
    level: '',
    component: '',
    action_type: '',
    severity: '',
    user_id: '',
    entity_type: '',
    start_time: '',
    end_time: ''
  });
  const [showFilters, setShowFilters] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Fetch logs data
  const { data: logsData, isLoading, error, refetch } = useQuery({
    queryKey: ['logs', type, page, rowsPerPage, filters],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: rowsPerPage.toString(),
        offset: (page * rowsPerPage).toString(),
        ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== ''))
      });

      const response = await fetch(`/api/v1/logs/${type === 'system' ? 'system' : 'audit'}?${params}`);
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      return response.json();
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setPage(0);
  };

  const toggleRowExpansion = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      case 'success':
        return 'success';
      default:
        return 'default';
    }
  };

  const getLevelIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
      case 'critical':
        return <ErrorIcon />;
      case 'warning':
        return <WarningIcon />;
      case 'info':
        return <InfoIcon />;
      case 'success':
        return <SuccessIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const renderSystemLogs = () => {
    if (!logsData?.logs) return null;

    return (
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Level</TableCell>
              <TableCell>Message</TableCell>
              <TableCell>Component</TableCell>
              <TableCell>Time</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logsData.logs.map((log: LogEntry) => (
              <React.Fragment key={log.id}>
                <TableRow hover>
                  <TableCell>
                    <Chip
                      icon={getLevelIcon(log.level)}
                      label={log.level}
                      color={getLevelColor(log.level)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {log.message}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {log.component || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatTimestamp(log.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => toggleRowExpansion(log.id)}
                    >
                      {expandedRows.has(log.id) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={5}>
                    <Collapse in={expandedRows.has(log.id)} timeout="auto" unmountOnExit>
                      <Box sx={{ margin: 1 }}>
                        <Grid container columns={12} spacing={2}>
                          {log.sub_component && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                Sub Component: {log.sub_component}
                              </Typography>
                            </Grid>
                          )}
                          {log.function_name && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                Function: {log.function_name}
                              </Typography>
                            </Grid>
                          )}
                          {log.line_number && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                Line: {log.line_number}
                              </Typography>
                            </Grid>
                          )}
                          {log.execution_time_ms && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                Execution Time: {log.execution_time_ms}ms
                              </Typography>
                            </Grid>
                          )}
                          {log.exception_message && (
                            <Grid sx={{ gridColumn: 'span 12' }}>
                              <Alert severity="error" sx={{ mt: 1 }}>
                                <Typography variant="body2">
                                  {log.exception_message}
                                </Typography>
                              </Alert>
                            </Grid>
                          )}
                          {log.log_data && (
                            <Grid sx={{ gridColumn: 'span 12' }}>
                              <Card variant="outlined" sx={{ mt: 1 }}>
                                <CardContent>
                                  <Typography variant="caption" color="text.secondary">
                                    Additional Data:
                                  </Typography>
                                  <pre style={{ fontSize: '0.75rem', margin: '8px 0 0 0' }}>
                                    {JSON.stringify(log.log_data, null, 2)}
                                  </pre>
                                </CardContent>
                              </Card>
                            </Grid>
                          )}
                        </Grid>
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={logsData.total_count || 0}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>
    );
  };

  const renderAuditLogs = () => {
    if (!logsData?.audit_entries) return null;

    return (
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Action</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Time</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logsData.audit_entries.map((entry: AuditEntry) => (
              <React.Fragment key={entry.id}>
                <TableRow hover>
                  <TableCell>
                    <Chip
                      label={entry.action_type}
                      color={entry.is_successful ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {entry.action_description || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {entry.user_name || entry.user_id || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={entry.is_successful ? <SuccessIcon /> : <ErrorIcon />}
                      label={entry.is_successful ? 'Success' : 'Failed'}
                      color={entry.is_successful ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatTimestamp(entry.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => toggleRowExpansion(entry.id)}
                    >
                      {expandedRows.has(entry.id) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
                    <Collapse in={expandedRows.has(entry.id)} timeout="auto" unmountOnExit>
                      <Box sx={{ margin: 1 }}>
                        <Grid container columns={12} spacing={2}>
                          {entry.entity_type && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                Entity: {entry.entity_type}
                              </Typography>
                            </Grid>
                          )}
                          {entry.processing_time_ms && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                Processing Time: {entry.processing_time_ms}ms
                              </Typography>
                            </Grid>
                          )}
                          {entry.ai_model_used && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                AI Model: {entry.ai_model_used}
                              </Typography>
                            </Grid>
                          )}
                          {entry.ai_confidence_score && (
                            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                              <Typography variant="caption" color="text.secondary">
                                Confidence: {(entry.ai_confidence_score * 100).toFixed(1)}%
                              </Typography>
                            </Grid>
                          )}
                          {entry.error_message && (
                            <Grid sx={{ gridColumn: 'span 12' }}>
                              <Alert severity="error" sx={{ mt: 1 }}>
                                <Typography variant="body2">
                                  {entry.error_message}
                                </Typography>
                              </Alert>
                            </Grid>
                          )}
                          {entry.action_data && (
                            <Grid sx={{ gridColumn: 'span 12' }}>
                              <Card variant="outlined" sx={{ mt: 1 }}>
                                <CardContent>
                                  <Typography variant="caption" color="text.secondary">
                                    Action Data:
                                  </Typography>
                                  <pre style={{ fontSize: '0.75rem', margin: '8px 0 0 0' }}>
                                    {JSON.stringify(entry.action_data, null, 2)}
                                  </pre>
                                </CardContent>
                              </Card>
                            </Grid>
                          )}
                        </Grid>
                      </Box>
                    </Collapse>
                  </TableCell>
                </TableRow>
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={logsData.total_count || 0}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>
    );
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          {type === 'system' ? 'System Logs' : 'Audit Trail'}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<FilterIcon />}
            onClick={() => setShowFilters(!showFilters)}
            size="small"
          >
            Filters
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

      {/* Filters */}
      <Collapse in={showFilters}>
        <Paper sx={{ p: 2, mb: 2 }}>
          <Grid container columns={12} spacing={2}>
            {type === 'system' ? (
              <>
                <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Level</InputLabel>
                    <Select
                      value={filters.level}
                      label="Level"
                      onChange={(e) => handleFilterChange('level', e.target.value)}
                    >
                      <MenuItem value="">All</MenuItem>
                      <MenuItem value="DEBUG">DEBUG</MenuItem>
                      <MenuItem value="INFO">INFO</MenuItem>
                      <MenuItem value="WARNING">WARNING</MenuItem>
                      <MenuItem value="ERROR">ERROR</MenuItem>
                      <MenuItem value="CRITICAL">CRITICAL</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Component"
                    value={filters.component}
                    onChange={(e) => handleFilterChange('component', e.target.value)}
                  />
                </Grid>
              </>
            ) : (
              <>
                <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Action Type"
                    value={filters.action_type}
                    onChange={(e) => handleFilterChange('action_type', e.target.value)}
                  />
                </Grid>
                <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Severity</InputLabel>
                    <Select
                      value={filters.severity}
                      label="Severity"
                      onChange={(e) => handleFilterChange('severity', e.target.value)}
                    >
                      <MenuItem value="">All</MenuItem>
                      <MenuItem value="info">Info</MenuItem>
                      <MenuItem value="warning">Warning</MenuItem>
                      <MenuItem value="error">Error</MenuItem>
                      <MenuItem value="critical">Critical</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="User ID"
                    value={filters.user_id}
                    onChange={(e) => handleFilterChange('user_id', e.target.value)}
                  />
                </Grid>
                <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Entity Type"
                    value={filters.entity_type}
                    onChange={(e) => handleFilterChange('entity_type', e.target.value)}
                  />
                </Grid>
              </>
            )}
            <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
              <TextField
                fullWidth
                size="small"
                label="Start Time"
                type="datetime-local"
                value={filters.start_time}
                onChange={(e) => handleFilterChange('start_time', e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }}>
              <TextField
                fullWidth
                size="small"
                label="End Time"
                type="datetime-local"
                value={filters.end_time}
                onChange={(e) => handleFilterChange('end_time', e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
          </Grid>
        </Paper>
      </Collapse>

      {/* Content */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error">
          Failed to load logs. Please try again.
        </Alert>
      ) : (
        type === 'system' ? renderSystemLogs() : renderAuditLogs()
      )}
    </Box>
  );
};

export default LogViewer;
