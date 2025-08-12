import React, { useEffect, useMemo, useState } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  TextField, 
  Switch, 
  FormControlLabel, 
  Button, 
  Alert, 
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider
} from '@mui/material';
import { Warning as WarningIcon, Delete as DeleteIcon } from '@mui/icons-material';

const Settings: React.FC = () => {
  const [tolerancePct, setTolerancePct] = useState<number>(0.5);
  const [notifyOnHighSeverity, setNotifyOnHighSeverity] = useState<boolean>(true);
  const [notifyOnAllExceptions, setNotifyOnAllExceptions] = useState<boolean>(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const token = useMemo(() => localStorage.getItem('access_token'), []);

  useEffect(() => {
    const load = async () => {
      try {
        setInfo(null);
        const res = await fetch('/api/v1/settings/', { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
        if (!res.ok) throw new Error('Failed to load settings');
        const data = await res.json();
        const s = data?.settings || {};
        if (typeof s.tolerancePct === 'number') setTolerancePct(s.tolerancePct);
        if (typeof s.notifyOnHighSeverity === 'boolean') setNotifyOnHighSeverity(s.notifyOnHighSeverity);
        if (typeof s.notifyOnAllExceptions === 'boolean') setNotifyOnAllExceptions(s.notifyOnAllExceptions);
      } catch (e) {
        setInfo('Using defaults; settings not found yet.');
      }
    };
    load();
    
    // Show admin section for anyone logged in (for demo purposes)
    // In a real app, you'd decode the JWT and check the user role
    setIsAdmin(true); // Show admin section for everyone
  }, [token]);

  const onSave = async () => {
    try {
      setSaving(true);
      setError(null);
      const payload = {
        settings: {
          tolerancePct,
          notifyOnHighSeverity,
          notifyOnAllExceptions
        }
      };
      const res = await fetch('/api/v1/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Save failed');
      setInfo('Settings saved');
    } catch (e) {
      setError('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const onClearExceptions = async () => {
    try {
      setClearing(true);
      setError(null);
      const res = await fetch('/api/v1/exceptions/clear-all', {
        method: 'DELETE',
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to clear exceptions');
      }
      
      const data = await res.json();
      setInfo(data.message || 'Exceptions cleared successfully');
      setClearDialogOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to clear exceptions');
    } finally {
      setClearing(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {saving && <LinearProgress sx={{ mb: 2 }} />}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {info && <Alert severity="info" sx={{ mb: 2 }}>{info}</Alert>}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Reconciliation Thresholds</Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <TextField
            type="number"
            label="Amount Tolerance Percentage"
            value={tolerancePct}
            onChange={(e) => setTolerancePct(Number(e.target.value))}
            inputProps={{ step: '0.1', min: '0', max: '100' }}
            sx={{ minWidth: '250px' }}
            helperText="Percentage difference threshold for reconciliation breaks"
          />
        </Box>
      </Paper>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Notifications</Typography>
        <FormControlLabel control={<Switch checked={notifyOnHighSeverity} onChange={(e) => setNotifyOnHighSeverity(e.target.checked)} />} label="Notify on High/Critical Exceptions" />
        <FormControlLabel control={<Switch checked={notifyOnAllExceptions} onChange={(e) => setNotifyOnAllExceptions(e.target.checked)} />} label="Notify on All Exceptions" />
      </Paper>

      {isAdmin && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, color: 'warning.main' }}>
            <WarningIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Administrative Actions
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
            These actions are restricted to administrators only and cannot be undone.
          </Typography>
          <Button 
            variant="outlined" 
            color="error" 
            startIcon={<DeleteIcon />}
            onClick={() => setClearDialogOpen(true)}
            sx={{ mr: 2 }}
          >
            Clear All Exceptions
          </Button>
        </Paper>
      )}

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button variant="contained" onClick={onSave}>Save Settings</Button>
      </Box>

      {/* Clear Exceptions Confirmation Dialog */}
      <Dialog open={clearDialogOpen} onClose={() => setClearDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ color: 'error.main' }}>
          <WarningIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Clear All Exceptions
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to clear all exceptions? This action cannot be undone.
          </Typography>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will permanently delete all reconciliation exceptions from the system.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearDialogOpen(false)} disabled={clearing}>
            Cancel
          </Button>
          <Button 
            onClick={onClearExceptions} 
            color="error" 
            variant="contained" 
            disabled={clearing}
            startIcon={clearing ? <LinearProgress sx={{ width: 16, height: 16 }} /> : <DeleteIcon />}
          >
            {clearing ? 'Clearing...' : 'Clear All Exceptions'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Settings;


