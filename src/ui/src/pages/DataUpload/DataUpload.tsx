import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, 
  Typography, 
  Paper, 
  Button, 
  LinearProgress, 
  Alert, 
  Chip, 
  Card, 
  CardContent, 
  IconButton, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemIcon, 
  Divider,
  Tabs,
  Tab
} from '@mui/material';
import { 
  CloudUpload as UploadIcon, 
  CheckCircle as CheckIcon, 
  Error as ErrorIcon, 
  Delete as DeleteIcon, 
  Description as FileIcon, 
  TableChart as TableIcon, 
  PictureAsPdf as PdfIcon, 
  Code as CodeIcon
} from '@mui/icons-material';
import { Assessment as AssessmentIcon } from '@mui/icons-material';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import { useDropzone } from 'react-dropzone';

interface UploadFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
  result?: any;
  fileObject?: File;
  jobId?: string;
  role?: 'source_a' | 'source_b';
}

const DataUpload: React.FC = () => {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [reconcileJobId, setReconcileJobId] = useState<string | null>(null);
  const [reconcileStatus, setReconcileStatus] = useState<string | null>(null);
  const [reconcileSummary, setReconcileSummary] = useState<any | null>(null);
  const navigate = useNavigate();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'pending',
      progress: 0,
      fileObject: file
    }));
    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/xml': ['.xml'],
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt']
    },
    multiple: true
  });

  // Rehydrate jobs from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('upload_jobs');
    if (!saved) return;
    try {
      const parsed: UploadFile[] = JSON.parse(saved);
      setFiles(parsed);
    } catch {}
  }, []);

  // Persist jobs
  useEffect(() => {
    localStorage.setItem('upload_jobs', JSON.stringify(files));
  }, [files]);

  // Rehydrate reconcile job
  useEffect(() => {
    const r = localStorage.getItem('reconcile_job');
    if (r) {
      const { jobId } = JSON.parse(r);
      setReconcileJobId(jobId);
    }
  }, []);

  // Poll reconcile job
  useEffect(() => {
    if (!reconcileJobId) return;
    let mounted = true;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/upload/data/reconcile/job/${encodeURIComponent(reconcileJobId)}`);
        if (!res.ok) return;
        const job = await res.json();
        if (!mounted) return;
        setReconcileStatus(job.status);
        if (job.status === 'completed' || job.status === 'failed') {
          setReconcileSummary(job.result || null);
          clearInterval(interval);
          setActiveTab(4);
        }
      } catch {}
    }, 1000);
    return () => { mounted = false; clearInterval(interval); };
  }, [reconcileJobId]);

  const getFileIcon = (type: string) => {
    if (type.includes('csv') || type.includes('excel') || type.includes('spreadsheet')) {
      return <TableIcon />;
    } else if (type.includes('pdf')) {
      return <PdfIcon />;
    } else if (type.includes('xml')) {
      return <CodeIcon />;
    } else {
      return <FileIcon />;
    }
  };

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'uploading':
      case 'processing':
        return <LinearProgress sx={{ width: 20, height: 20 }} />;
      default:
        return undefined;
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setIsUploading(true);

    for (const file of files) {
      if (file.status !== 'pending') continue;
      setFiles(prev => prev.map(f => f.id === file.id ? { ...f, status: 'uploading', progress: 0 } : f));

      try {
        const formData = new FormData();
        if (file.fileObject) {
          formData.append('file', file.fileObject, file.name);
        } else {
          throw new Error('Missing file content');
        }
        formData.append('data_source', 'ui-upload');

        // No progress API in fetch; set to indeterminate completing after request
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/v1/upload/data/upload', {
          method: 'POST',
          body: formData,
          headers: token ? { Authorization: `Bearer ${token}` } : undefined
        });

        if (!response.ok) {
          throw new Error(await response.text());
        }

        // Expect 202-style response with job_id
        const accepted = await response.json();
        const jobId = accepted?.job_id;
        if (!jobId) throw new Error('Upload accepted but no job id returned');
        setFiles(prev => prev.map(f => f.id === file.id ? { ...f, status: 'processing', progress: 50, jobId } : f));

        // Poll job status until completion
        let attempts = 0;
        while (attempts < 120) { // up to ~2 minutes if 1s intervals
          await new Promise(r => setTimeout(r, 1000));
          attempts += 1;
          const st = await fetch(`/api/v1/upload/data/upload/job/${encodeURIComponent(jobId)}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined
          });
          if (!st.ok) continue;
          const job = await st.json();
          if (job?.status === 'completed' || job?.status === 'failed') {
            const result = job?.result || {};
            setFiles(prev => prev.map(f => f.id === file.id ? {
              ...f,
              status: job.status === 'completed' && result?.success ? 'completed' : 'error',
              progress: 100,
              error: result?.success ? undefined : (result?.message || 'Processing failed'),
              result: result?.success ? {
                recordsProcessed: result?.processed_records ?? 0,
                matchesFound: result?.summary?.matches_found ?? 0,
                exceptionsFound: result?.summary?.exceptions_found ?? 0
              } : undefined
            } : f));
            break;
          }
        }
      } catch (err: any) {
        setFiles(prev => prev.map(f => f.id === file.id ? { ...f, status: 'error', error: err?.message || 'Upload failed' } : f));
      }
    }

    setIsUploading(false);
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box sx={{ p: 3 }}>
      

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="Upload Files" icon={<UploadIcon />} iconPosition="start" />
          <Tab label="Results" icon={<AssessmentIcon />} iconPosition="start" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
          <Box sx={{ flex: '1', minWidth: '600px' }}>
            <Paper
              {...getRootProps()}
              sx={{
                border: '2px dashed',
                borderColor: isDragActive ? 'primary.main' : 'grey.300',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                cursor: 'pointer',
                backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  borderColor: 'primary.main',
                  backgroundColor: 'action.hover'
                }
              }}
            >
              <input {...getInputProps()} />
              <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                or click to select files
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Supported formats: CSV, Excel (.xlsx, .xls), XML, PDF, TXT
              </Typography>
            </Paper>

            {files.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Files to Upload ({files.length})
                </Typography>
                <List>
                  {files.map((file, index) => (
                    <React.Fragment key={file.id}>
                      <ListItem>
                        <ListItemIcon>
                          {getFileIcon(file.type)}
                        </ListItemIcon>
                        <ListItemText
                          primary={file.name}
                          secondary={`${formatFileSize(file.size)} • ${file.type || 'Unknown type'}`}
                        />
                        <Tabs value={file.role || false} onChange={(e, v) => setFiles(prev => prev.map(f => f.id === file.id ? { ...f, role: v } : f))}>
                          <Tab label="Source A" value="source_a" />
                          <Tab label="Source B" value="source_b" />
                        </Tabs>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {file.status === 'uploading' || file.status === 'processing' ? (
                            <Box sx={{ width: 100 }}>
                              <LinearProgress 
                                variant="determinate" 
                                value={file.progress} 
                                sx={{ height: 6, borderRadius: 3 }}
                              />
                            </Box>
                          ) : (
                            getStatusIcon(file.status)
                          )}
                          <IconButton 
                            size="small" 
                            onClick={() => removeFile(file.id)}
                            disabled={file.status === 'uploading' || file.status === 'processing'}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      </ListItem>
                      {file.status === 'completed' && file.result && (
                        <Box sx={{ ml: 4, mb: 2 }}>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            <Chip 
                              label={`${file.result.recordsProcessed} records`} 
                              size="small" 
                              color="primary" 
                            />
                            <Chip 
                              label={`${file.result.matchesFound} matches`} 
                              size="small" 
                              color="success" 
                            />
                            <Chip 
                              label={`${file.result.exceptionsFound} exceptions`} 
                              size="small" 
                              color="warning" 
                            />
                          </Box>
                        </Box>
                      )}
                      {index < files.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
                
                <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                  <Button
                    variant="contained"
                    onClick={handleUpload}
                    disabled={isUploading || files.filter(f => f.status === 'pending').length === 0}
                    startIcon={<UploadIcon />}
                  >
                    {isUploading ? 'Uploading...' : 'Upload Files'}
                  </Button>
                  <Button
                    variant="outlined"
                    disabled={!files.some(f => f.status === 'completed' && f.role === 'source_a') || !files.some(f => f.status === 'completed' && f.role === 'source_b')}
                    onClick={async () => {
                      const a = files.find(f => f.status === 'completed' && f.role === 'source_a');
                      const b = files.find(f => f.status === 'completed' && f.role === 'source_b');
                      if (!a || !b || !a.jobId || !b.jobId) return;
                      const fd = new FormData();
                      fd.append('job_id_a', a.jobId);
                      fd.append('job_id_b', b.jobId);
                      const res = await fetch('/api/v1/upload/data/reconcile/start', { method: 'POST', body: fd });
                      if (res.ok) {
                        const json = await res.json();
                        const jobId = json?.reconcile_job_id;
                        if (jobId) {
                          setReconcileJobId(jobId);
                          setReconcileStatus('processing');
                          setReconcileSummary(null);
                          localStorage.setItem('reconcile_job', JSON.stringify({ jobId }));
                        }
                      }
                    }}
                  >
                    Reconcile
                  </Button>
                </Box>

                {reconcileStatus && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2">Reconcile Status: {reconcileStatus}</Typography>
                    {reconcileSummary && (
                      <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <Chip label={`Matches: ${reconcileSummary?.matching?.summary?.total_matches ?? 0}`} color="success" size="small" />
                        <Chip label={`Exceptions: ${reconcileSummary?.exceptions?.summary?.total_breaks ?? 0}`} color="warning" size="small" />
                        <Chip label={`Resolved: ${reconcileSummary?.resolution?.summary?.resolved_exceptions ?? 0}`} color="primary" size="small" />
                        <Button size="small" variant="text" onClick={() => setActiveTab(1)}>View Results</Button>
                        <Button size="small" variant="text" onClick={() => navigate('/exceptions')}>Go to Exceptions</Button>
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
            )}
          </Box>

          <Box sx={{ flex: '1', minWidth: '300px' }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Upload Statistics
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Total Files: {files.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Pending: {files.filter(f => f.status === 'pending').length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Completed: {files.filter(f => f.status === 'completed').length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Failed: {files.filter(f => f.status === 'error').length}
                  </Typography>
                </Box>
              </CardContent>
            </Card>

            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Supported Formats
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemIcon><TableIcon /></ListItemIcon>
                    <ListItemText primary="CSV Files (.csv)" secondary="Comma-separated values" />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon><TableIcon /></ListItemIcon>
                    <ListItemText primary="Excel Files (.xlsx, .xls)" secondary="Microsoft Excel spreadsheets" />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon><CodeIcon /></ListItemIcon>
                    <ListItemText primary="XML Files (.xml)" secondary="Extensible Markup Language" />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon><PdfIcon /></ListItemIcon>
                    <ListItemText primary="PDF Files (.pdf)" secondary="Portable Document Format" />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon><FileIcon /></ListItemIcon>
                    <ListItemText primary="Text Files (.txt)" secondary="Plain text files" />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Box>
        </Box>
      )}

      {activeTab === 1 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Reconciliation Results
          </Typography>
          {reconcileSummary ? (
            <Box>
              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                <Chip label={`Matches: ${reconcileSummary?.matching?.summary?.total_matches ?? 0}`} color="success" size="small" />
                <Chip label={`Exceptions: ${reconcileSummary?.exceptions?.summary?.total_breaks ?? 0}`} color="warning" size="small" />
                <Chip label={`Resolved: ${reconcileSummary?.resolution?.summary?.resolved_exceptions ?? 0}`} color="primary" size="small" />
              </Box>
              <Typography variant="subtitle2" sx={{ mt: 1, mb: 1 }}>Matches (first 10):</Typography>
              <TableContainer component={Paper}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>External ID A</TableCell>
                      <TableCell>External ID B</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Confidence</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(reconcileSummary?.matching?.matches || []).slice(0, 10).map((m: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell>{m?.transaction_a?.external_id}</TableCell>
                        <TableCell>{m?.transaction_b?.external_id}</TableCell>
                        <TableCell>{m?.match_type}</TableCell>
                        <TableCell>{m?.confidence_score}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Exceptions (first 10):</Typography>
              <TableContainer component={Paper}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Break Type</TableCell>
                      <TableCell>Transaction</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(reconcileSummary?.exceptions?.exceptions || []).slice(0, 10).map((e: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell>{e?.break_type}</TableCell>
                        <TableCell>{e?.transaction_a?.external_id || e?.transaction_id}</TableCell>
                        <TableCell>{e?.severity}</TableCell>
                        <TableCell>{e?.break_details?.description || '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">No results yet. Start a reconcile or wait for it to complete.</Typography>
          )}
        </Box>
      )}
    </Box>
  );
};

export default DataUpload;
