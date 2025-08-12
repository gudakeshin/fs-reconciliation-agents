import React from 'react';
import { Box, Paper, Typography, Link, Alert } from '@mui/material';

const Help: React.FC = () => {
  return (
    <Box sx={{ p: 3, display: 'grid', gap: 2 }}>
      <Alert severity="info">This page provides quick help and links to documentation.</Alert>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>Key Docs</Typography>
        <Typography variant="body2">
          - Business Requirements Document (BRD): <Link href="/BRD.md" target="_blank" rel="noreferrer">Open BRD</Link>
        </Typography>
        <Typography variant="body2">
          - User Guide: <Link href="/docs/USER_GUIDE.md" target="_blank" rel="noreferrer">Open User Guide</Link>
        </Typography>
        <Typography variant="body2">
          - Technical Documentation: <Link href="/docs/TECHNICAL_DOCUMENTATION.md" target="_blank" rel="noreferrer">Open Technical Docs</Link>
        </Typography>
      </Paper>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>Troubleshooting</Typography>
        <Typography variant="body2">- If uploads show 0 records, verify CSV has headers and commas, UTF-8 encoding.</Typography>
        <Typography variant="body2">- Ensure API is healthy: GET /health</Typography>
        <Typography variant="body2">- For auth issues, development uses anonymous mode via ALLOW_ANONYMOUS=true.</Typography>
      </Paper>
    </Box>
  );
};

export default Help;


