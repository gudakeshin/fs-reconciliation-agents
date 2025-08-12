import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Paper,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Tabs,
  Tab
} from '@mui/material';
import {
  TrendingUp,
  Warning,
  CheckCircle,
  Schedule,
  Error as ErrorIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import AgentStatus from '../../components/AgentStatus';

interface Stats {
  totalTransactions: number;
  matchedTransactions: number;
  unmatchedTransactions: number;
  exceptionsCount: number;
  resolutionRate: number;
  lastUpdated: string;
}

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
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  const refreshStats = async () => {
    setIsLoading(true);
    try {
      // Fetch exception stats summary
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/exceptions/stats/summary', {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      if (!response.ok) {
        throw new Error(String('Failed to fetch stats'));
      }
      const data = await response.json();
      const totalBreaks = Number(data?.total_breaks || 0);
      const resolvedBreaks = Number(data?.resolved_breaks || 0);
      const resolutionRatePercent = Number(data?.resolution_rate || 0);

      // Fetch transaction KPIs
      const txRes = await fetch('/api/v1/metrics/transactions/summary', {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      const tx = txRes.ok ? await txRes.json() : {};

      setStats({
        totalTransactions: Number(tx?.total_transactions || 0),
        matchedTransactions: Number(tx?.matched_transactions || 0),
        unmatchedTransactions: Number(tx?.unmatched_transactions || 0),
        exceptionsCount: totalBreaks,
        resolutionRate: isNaN(resolutionRatePercent) ? 0 : resolutionRatePercent / 100,
        lastUpdated: new Date().toISOString()
      });
    } catch (err) {
      setError('Failed to load stats');
    } finally {
      setIsLoading(false);
    }
  };

  const refreshExceptions = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/exceptions/?skip=0&limit=5', {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      if (!response.ok) {
        throw new Error('Failed to fetch exceptions');
      }
      const data = await response.json();
      const items = Array.isArray(data?.exceptions) ? data.exceptions : [];
      const mapped = items.map((e: any) => ({
        id: String(e.id),
        transactionId: String(e.transaction_id || ''),
        breakType: String(e.break_type || ''),
        severity: String(e.severity || '').toLowerCase() as Exception['severity'],
        status: String(e.status || '').toLowerCase() as Exception['status'],
        description: e.break_details?.description || `${e.break_type || 'Exception'}`,
        createdAt: String(e.created_at || new Date().toISOString()),
        assignedTo: e.assigned_to || undefined,
        priority: Number(e.priority ?? 2)
      }));
      setExceptions(mapped);
    } catch (err) {
      setError('Failed to load exceptions');
    }
  };

  useEffect(() => {
    refreshStats();
    refreshExceptions();
    const id = setInterval(refreshStats, 5000);
    return () => clearInterval(id);
  }, []);

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

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
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
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        <Box display="flex" gap={1}>
          <Tooltip title="Refresh Data">
            <IconButton onClick={refreshStats} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="KPIs & Metrics" />
          <Tab label="Agent Status" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 0 && (
        <>
          {/* Statistics Cards */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 4 }}>
        <Card
          onClick={() => navigate('/upload')}
          sx={{ flex: '1', minWidth: '250px', cursor: 'pointer', '&:hover': { boxShadow: 6 } }}
        >
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="text.secondary" gutterBottom>
                  Total Transactions
                </Typography>
                <Typography variant="h4">
                  {stats?.totalTransactions || 0}
                </Typography>
              </Box>
              <TrendingUp color="primary" sx={{ fontSize: 40 }} />
            </Box>
          </CardContent>
        </Card>

        <Card
          onClick={() => navigate('/exceptions?status=resolved')}
          sx={{ flex: '1', minWidth: '250px', cursor: 'pointer', '&:hover': { boxShadow: 6 } }}
        >
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="text.secondary" gutterBottom>
                  Matched
                </Typography>
                <Typography variant="h4" color="success.main">
                  {stats?.matchedTransactions || 0}
                </Typography>
              </Box>
              <CheckCircle color="success" sx={{ fontSize: 40 }} />
            </Box>
          </CardContent>
        </Card>

        <Card
          onClick={() => navigate('/exceptions?status=open')}
          sx={{ flex: '1', minWidth: '250px', cursor: 'pointer', '&:hover': { boxShadow: 6 } }}
        >
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="text.secondary" gutterBottom>
                  Unmatched
                </Typography>
                <Typography variant="h4" color="warning.main">
                  {stats?.unmatchedTransactions || 0}
                </Typography>
              </Box>
              <Warning color="warning" sx={{ fontSize: 40 }} />
            </Box>
          </CardContent>
        </Card>

        <Card
          onClick={() => navigate('/exceptions')}
          sx={{ flex: '1', minWidth: '250px', cursor: 'pointer', '&:hover': { boxShadow: 6 } }}
        >
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="text.secondary" gutterBottom>
                  Exceptions
                </Typography>
                <Typography variant="h4" color="error.main">
                  {stats?.exceptionsCount || 0}
                </Typography>
              </Box>
              <ErrorIcon color="error" sx={{ fontSize: 40 }} />
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Progress and Status */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 4 }}>
        <Card sx={{ flex: '1', minWidth: '400px' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Reconciliation Progress
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Match Rate
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {stats?.resolutionRate ? `${(stats.resolutionRate * 100).toFixed(1)}%` : '0%'}
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={stats?.resolutionRate ? stats.resolutionRate * 100 : 0}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
            <Typography variant="body2" color="text.secondary">
              Last updated: {stats?.lastUpdated ? new Date(stats.lastUpdated).toLocaleString() : 'Never'}
            </Typography>
          </CardContent>
        </Card>

        <Card sx={{ flex: '1', minWidth: '400px' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              System Status
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Box display="flex" alignItems="center" sx={{ mb: 1 }}>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <Typography variant="body2">API Service: Online</Typography>
              </Box>
              <Box display="flex" alignItems="center" sx={{ mb: 1 }}>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <Typography variant="body2">Database: Connected</Typography>
              </Box>
              <Box display="flex" alignItems="center" sx={{ mb: 1 }}>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <Typography variant="body2">AI Agents: Active</Typography>
              </Box>
              <Box display="flex" alignItems="center">
                <Schedule color="info" sx={{ mr: 1 }} />
                <Typography variant="body2">Last sync: {new Date().toLocaleTimeString()}</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Recent Exceptions */}
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">
              Recent Exceptions
            </Typography>
          </Box>
          {exceptions.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No exceptions found
            </Typography>
          ) : (
            <Box>
              {exceptions.slice(0, 5).map((exception) => (
                <Paper key={exception.id} sx={{ p: 2, mb: 2 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        {exception.description}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Transaction: {exception.transactionId}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Created: {new Date(exception.createdAt).toLocaleString()}
                      </Typography>
                    </Box>
                    <Box display="flex" gap={1}>
                      <Chip 
                        label={exception.severity} 
                        color={getSeverityColor(exception.severity) as any}
                        size="small"
                      />
                      <Chip 
                        label={exception.status} 
                        color={getStatusColor(exception.status) as any}
                        size="small"
                      />
                    </Box>
                  </Box>
                </Paper>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
        </>
      )}

      {activeTab === 1 && (
        <AgentStatus />
      )}
    </Box>
  );
};

export default Dashboard;
