import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  IconButton,
  Tooltip,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandMoreIcon,
  Timeline as TimelineIcon,
  Security as SecurityIcon,
  BugReport as BugReportIcon,
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Storage as DatabaseIcon
} from '@mui/icons-material';

interface SystemLog {
  id: string;
  level: string;
  message: string;
  component: string;
  sub_component: string;
  function_name: string;
  line_number: number;
  exception_type?: string;
  exception_message?: string;
  stack_trace?: string;
  execution_time_ms?: number;
  memory_usage_mb?: number;
  cpu_usage_percent?: number;
  created_at: string;
}

interface AuditTrailEntry {
  id: string;
  action_type: string;
  action_description: string;
  user_id: string;
  user_name: string;
  user_role: string;
  session_id: string;
  ip_address: string;
  entity_type: string;
  entity_id: string;
  processing_time_ms: number;
  ai_model_used?: string;
  ai_confidence_score?: number;
  severity: string;
  is_successful: boolean;
  error_message?: string;
  created_at: string;
}

interface DatabaseRecord {
  id: string;
  table_name: string;
  record_data: any;
  created_at: string;
  updated_at: string;
}

interface ExceptionRecord {
  id: string;
  break_type: string;
  severity: string;
  status: string;
  transaction_id: string;
  description: string;
  break_amount: number | null;
  break_currency: string;
  ai_confidence_score: number;
  ai_reasoning: string | null;
  ai_suggested_actions: string[] | null;
  detailed_differences: any | null;
  workflow_triggers: any | null;
  created_at: string;
  updated_at: string;
}



interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`governance-tabpanel-${index}`}
      aria-labelledby={`governance-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Governance: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // System Logs state
  const [systemLogs, setSystemLogs] = useState<SystemLog[]>([]);
  const [systemLogsPage, setSystemLogsPage] = useState(0);
  const [systemLogsRowsPerPage, setSystemLogsRowsPerPage] = useState(10);
  const [systemLogsFilter, setSystemLogsFilter] = useState({
    level: '',
    component: '',
    search: ''
  });

  // Audit Trail state
  const [auditTrail, setAuditTrail] = useState<AuditTrailEntry[]>([]);
  const [auditTrailPage, setAuditTrailPage] = useState(0);
  const [auditTrailRowsPerPage, setAuditTrailRowsPerPage] = useState(10);
  const [auditTrailFilter, setAuditTrailFilter] = useState({
    action_type: '',
    severity: '',
    user: '',
    search: ''
  });





  const fetchSystemLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: systemLogsRowsPerPage.toString(),
        offset: (systemLogsPage * systemLogsRowsPerPage).toString(),
        ...(systemLogsFilter.level && { level: systemLogsFilter.level }),
        ...(systemLogsFilter.component && { component: systemLogsFilter.component }),
        ...(systemLogsFilter.search && { search: systemLogsFilter.search })
      });

      const response = await fetch(`/api/v1/logs/system?${params}`);
      if (!response.ok) throw new Error('Failed to fetch system logs');
      
      const data = await response.json();
      setSystemLogs(data.logs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch system logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditTrail = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: auditTrailRowsPerPage.toString(),
        offset: (auditTrailPage * auditTrailRowsPerPage).toString(),
        ...(auditTrailFilter.action_type && { action_type: auditTrailFilter.action_type }),
        ...(auditTrailFilter.severity && { severity: auditTrailFilter.severity }),
        ...(auditTrailFilter.user && { user: auditTrailFilter.user }),
        ...(auditTrailFilter.search && { search: auditTrailFilter.search })
      });

      const response = await fetch(`/api/v1/logs/audit?${params}`);
      if (!response.ok) throw new Error('Failed to fetch audit trail');
      
      const data = await response.json();
      setAuditTrail(data.audit_entries || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch audit trail');
    } finally {
      setLoading(false);
    }
  };





  useEffect(() => {
    if (activeTab === 0) fetchSystemLogs();
    else if (activeTab === 1) fetchAuditTrail();
  }, [activeTab, systemLogsPage, systemLogsRowsPerPage, systemLogsFilter]);

  useEffect(() => {
    if (activeTab === 1) fetchAuditTrail();
  }, [auditTrailPage, auditTrailRowsPerPage, auditTrailFilter]);



  const getSeverityColor = (severity: string) => {
    if (!severity) return 'default';
    switch (severity.toLowerCase()) {
      case 'critical': return 'error';
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const getLogLevelColor = (level: string) => {
    if (!level) return 'default';
    switch (level.toLowerCase()) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      case 'debug': return 'default';
      default: return 'default';
    }
  };

  const getLogLevelIcon = (level: string) => {
    if (!level) return <InfoIcon />;
    switch (level.toLowerCase()) {
      case 'error': return <ErrorIcon />;
      case 'warning': return <WarningIcon />;
      case 'info': return <InfoIcon />;
      case 'debug': return <BugReportIcon />;
      default: return <InfoIcon />;
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1">
          Governance & Compliance
        </Typography>
        <Box display="flex" gap={1}>
          <Tooltip title="Refresh Data">
            <IconButton onClick={() => {
              if (activeTab === 0) fetchSystemLogs();
              else if (activeTab === 1) fetchAuditTrail();
            }} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {loading && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ width: '100%' }}>
        <Tabs value={activeTab} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab 
            icon={<BugReportIcon />} 
            label="Systems Log" 
            iconPosition="start"
          />
          <Tab 
            icon={<SecurityIcon />} 
            label="Audit Trail" 
            iconPosition="start"
          />
        </Tabs>

        {/* Systems Log Tab */}
        <TabPanel value={activeTab} index={0}>
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr 1.5fr 0.5fr' }, gap: 2, alignItems: 'center' }}>
              <Box>
                <FormControl fullWidth size="small">
                  <InputLabel>Log Level</InputLabel>
                  <Select
                    value={systemLogsFilter.level}
                    label="Log Level"
                    onChange={(e) => setSystemLogsFilter({ ...systemLogsFilter, level: e.target.value })}
                  >
                    <MenuItem value="">All Levels</MenuItem>
                    <MenuItem value="ERROR">Error</MenuItem>
                    <MenuItem value="WARNING">Warning</MenuItem>
                    <MenuItem value="INFO">Info</MenuItem>
                    <MenuItem value="DEBUG">Debug</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              <Box>
                <FormControl fullWidth size="small">
                  <InputLabel>Component</InputLabel>
                  <Select
                    value={systemLogsFilter.component}
                    label="Component"
                    onChange={(e) => setSystemLogsFilter({ ...systemLogsFilter, component: e.target.value })}
                  >
                    <MenuItem value="">All Components</MenuItem>
                    <MenuItem value="api">API</MenuItem>
                    <MenuItem value="agent">Agent</MenuItem>
                    <MenuItem value="database">Database</MenuItem>
                    <MenuItem value="ui">UI</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              <Box>
                <TextField
                  fullWidth
                  size="small"
                  label="Search Logs"
                  value={systemLogsFilter.search}
                  onChange={(e) => setSystemLogsFilter({ ...systemLogsFilter, search: e.target.value })}
                />
              </Box>
              <Box>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<FilterIcon />}
                  onClick={fetchSystemLogs}
                >
                  Filter
                </Button>
              </Box>
            </Box>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Level</TableCell>
                  <TableCell>Component</TableCell>
                  <TableCell>Message</TableCell>
                  <TableCell>Function</TableCell>
                  <TableCell>Time</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {systemLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>
                      <Chip
                        icon={getLogLevelIcon(log.level)}
                        label={log.level || 'Unknown'}
                        color={getLogLevelColor(log.level)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{log.component}</TableCell>
                    <TableCell>
                      <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                        {log.message}
                      </Typography>
                    </TableCell>
                    <TableCell>{log.function_name}</TableCell>
                    <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      {log.execution_time_ms ? `${log.execution_time_ms}ms` : '-'}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <ExpandMoreIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={-1}
            rowsPerPage={systemLogsRowsPerPage}
            page={systemLogsPage}
            onPageChange={(e, newPage) => setSystemLogsPage(newPage)}
            onRowsPerPageChange={(e) => {
              setSystemLogsRowsPerPage(parseInt(e.target.value, 10));
              setSystemLogsPage(0);
            }}
          />
        </TabPanel>

        {/* Audit Trail Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '0.5fr 0.5fr 1fr 1fr 0.5fr' }, gap: 2, alignItems: 'center' }}>
              <Box>
                <FormControl fullWidth size="small">
                  <InputLabel>Action Type</InputLabel>
                  <Select
                    value={auditTrailFilter.action_type}
                    label="Action Type"
                    onChange={(e) => setAuditTrailFilter({ ...auditTrailFilter, action_type: e.target.value })}
                  >
                    <MenuItem value="">All Actions</MenuItem>
                    <MenuItem value="data_ingested">Data Ingested</MenuItem>
                    <MenuItem value="match_created">Match Created</MenuItem>
                    <MenuItem value="exception_detected">Exception Detected</MenuItem>
                    <MenuItem value="resolution_approved">Resolution Approved</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              <Box>
                <FormControl fullWidth size="small">
                  <InputLabel>Severity</InputLabel>
                  <Select
                    value={auditTrailFilter.severity}
                    label="Severity"
                    onChange={(e) => setAuditTrailFilter({ ...auditTrailFilter, severity: e.target.value })}
                  >
                    <MenuItem value="">All Severities</MenuItem>
                    <MenuItem value="critical">Critical</MenuItem>
                    <MenuItem value="high">High</MenuItem>
                    <MenuItem value="medium">Medium</MenuItem>
                    <MenuItem value="low">Low</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              <Box>
                <TextField
                  fullWidth
                  size="small"
                  label="User"
                  value={auditTrailFilter.user}
                  onChange={(e) => setAuditTrailFilter({ ...auditTrailFilter, user: e.target.value })}
                />
              </Box>
              <Box>
                <TextField
                  fullWidth
                  size="small"
                  label="Search"
                  value={auditTrailFilter.search}
                  onChange={(e) => setAuditTrailFilter({ ...auditTrailFilter, search: e.target.value })}
                />
              </Box>
              <Box>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<FilterIcon />}
                  onClick={fetchAuditTrail}
                >
                  Filter
                </Button>
              </Box>
            </Box>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Action</TableCell>
                  <TableCell>User</TableCell>
                  <TableCell>Entity</TableCell>
                  <TableCell>Severity</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Time</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {auditTrail.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {entry.action_type.replace('_', ' ').toUpperCase()}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {entry.action_description}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{entry.user_name}</Typography>
                      <Typography variant="caption" color="textSecondary">
                        {entry.user_role}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{entry.entity_type}</Typography>
                      <Typography variant="caption" color="textSecondary">
                        {entry.entity_id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={entry.severity || 'Unknown'}
                        color={getSeverityColor(entry.severity)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={entry.is_successful ? <CheckCircleIcon /> : <ErrorIcon />}
                        label={entry.is_successful ? 'Success' : 'Failed'}
                        color={entry.is_successful ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {entry.processing_time_ms ? `${entry.processing_time_ms}ms` : '-'}
                    </TableCell>
                    <TableCell>{new Date(entry.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <ExpandMoreIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={-1}
            rowsPerPage={auditTrailRowsPerPage}
            page={auditTrailPage}
            onPageChange={(e, newPage) => setAuditTrailPage(newPage)}
            onRowsPerPageChange={(e) => {
              setAuditTrailRowsPerPage(parseInt(e.target.value, 10));
              setAuditTrailPage(0);
            }}
          />
        </TabPanel>

        {/* Database Management Link */}
        <Box sx={{ mt: 3, p: 3, textAlign: 'center' }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Database Management
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
            Access comprehensive database management with filtering, multi-select, and bulk operations for all tables.
          </Typography>
          <Button
            variant="contained"
            startIcon={<DatabaseIcon />}
            onClick={() => window.location.href = '/database-management'}
            size="large"
          >
            Open Database Management
          </Button>
        </Box>


      </Paper>
    </Box>
  );
};

  export default Governance;
