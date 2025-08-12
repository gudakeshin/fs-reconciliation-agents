import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { Refresh as RefreshIcon, Download as DownloadIcon, Delete as DeleteIcon, Search as InspectIcon, PlayArrow as GenerateIcon } from '@mui/icons-material';

type ReportTypeItem = {
  value: string;
  label: string;
  description?: string;
  formats?: string[];
};

type ReportListItem = {
  filename: string;
  report_type: string;
  format: string;
  file_size: number;
  created_at: string;
  download_url: string;
};

const Reports: React.FC = () => {
  const [types, setTypes] = useState<ReportTypeItem[]>([]);
  const [formats, setFormats] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedFormat, setSelectedFormat] = useState<string>('json');
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inspectItem, setInspectItem] = useState<ReportListItem | null>(null);
  const [inspectData, setInspectData] = useState<any>(null);

  const token = useMemo(() => localStorage.getItem('access_token'), []);

  const fetchTypes = async () => {
    try {
      setError(null);
      const res = await fetch('/api/v1/reports/types', { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (!res.ok) throw new Error('Failed to load report types');
      const data = await res.json();
      const list: ReportTypeItem[] = Array.isArray(data?.report_types) ? data.report_types : [];
      setTypes(list);
      setFormats(Array.isArray(data?.formats) ? data.formats.map((f: any) => f.value || f) : ['json']);
      if (list.length > 0) {
        setSelectedType(list[0].value);
        const f = list[0].formats && list[0].formats.length ? list[0].formats[0] : 'json';
        setSelectedFormat(f);
      }
    } catch (e) {
      setError('Unable to fetch report types');
    }
  };

  const fetchReports = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/v1/reports/list', { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (!res.ok) throw new Error('Failed to load reports');
      const data = await res.json();
      setReports(Array.isArray(data?.reports) ? data.reports : []);
    } catch (e) {
      setError('Unable to fetch reports');
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    if (!selectedType || !selectedFormat) return;
    try {
      setLoading(true);
      setError(null);
      const url = `/api/v1/reports/generate?report_type=${encodeURIComponent(selectedType)}&format=${encodeURIComponent(selectedFormat)}`;
      const res = await fetch(url, { method: 'POST', headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      if (!res.ok) throw new Error('Report generation failed');
      await res.json();
      await fetchReports();
    } catch (e) {
      setError('Report generation failed');
    } finally {
      setLoading(false);
    }
  };

  const deleteReport = async (filename: string) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/reports/${encodeURIComponent(filename)}`, { method: 'DELETE', headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (!res.ok) throw new Error('Delete failed');
      await fetchReports();
    } catch (e) {
      setError('Delete failed');
    } finally {
      setLoading(false);
    }
  };

  const inspectReport = async (item: ReportListItem) => {
    setInspectItem(item);
    setInspectData(null);
    try {
      const res = await fetch(`/api/v1/reports/download/${encodeURIComponent(item.filename)}?meta=true`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined });
      if (!res.ok) throw new Error('Inspect failed');
      const data = await res.json();
      setInspectData(data);
    } catch (e) {
      setInspectData({ error: 'Inspect failed. Backend does not return file stream; only metadata is available.' });
    }
  };

  useEffect(() => {
    fetchTypes();
    fetchReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      {loading && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress />
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
      )}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <FormControl sx={{ minWidth: 240 }}>
            <InputLabel>Report Type</InputLabel>
            <Select label="Report Type" value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
              {types.map((t) => (
                <MenuItem key={t.value} value={t.value}>{t.label || t.value}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl sx={{ minWidth: 160 }}>
            <InputLabel>Format</InputLabel>
            <Select label="Format" value={selectedFormat} onChange={(e) => setSelectedFormat(e.target.value)}>
              {(types.find(t => t.value === selectedType)?.formats || formats).map((f) => (
                <MenuItem key={f} value={f}>{String(f).toUpperCase()}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="contained" startIcon={<GenerateIcon />} onClick={generateReport}>
            Generate
          </Button>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchReports}>
            Refresh
          </Button>
        </Box>
      </Paper>

      <Typography variant="h6" sx={{ mb: 1 }}>Generated Reports</Typography>
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Filename</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Format</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reports.map((r) => (
                <TableRow key={r.filename} hover>
                  <TableCell>{r.filename}</TableCell>
                  <TableCell>{r.report_type}</TableCell>
                  <TableCell>{r.format.toUpperCase()}</TableCell>
                  <TableCell>{(r.file_size / 1024).toFixed(1)} KB</TableCell>
                  <TableCell>{new Date(r.created_at).toLocaleString()}</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => inspectReport(r)} title="Inspect">
                      <InspectIcon />
                    </IconButton>
                    <IconButton size="small" onClick={() => window.open(`/api/v1/reports/download/${encodeURIComponent(r.filename)}`, '_blank')} title="Download">
                      <DownloadIcon />
                    </IconButton>
                    <IconButton size="small" color="error" onClick={() => deleteReport(r.filename)} title="Delete">
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Dialog open={!!inspectItem} onClose={() => setInspectItem(null)} maxWidth="md" fullWidth>
        <DialogTitle>Report Metadata</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
            {inspectData ? JSON.stringify(inspectData, null, 2) : 'Loading...'}
          </Typography>
          <Alert severity="info" sx={{ mt: 2 }}>
            Download endpoint currently returns metadata only. File streaming is not implemented on the backend (data missing).
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInspectItem(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Reports;


