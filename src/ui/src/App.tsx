import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard/Dashboard';
import DataUpload from './pages/DataUpload/DataUpload';
import ExceptionManagement from './pages/ExceptionManagement/ExceptionManagement';
import Navigation from './components/Navigation/Navigation';
import Reports from './pages/Reports/Reports';
import Governance from './pages/Governance/Governance';
import DatabaseManagement from './pages/DatabaseManagement/DatabaseManagement';
import Settings from './pages/Settings/Settings';
import Help from './pages/Help/Help';

// Create theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  const [navigationOpen, setNavigationOpen] = React.useState(true);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Box sx={{ display: 'flex', minHeight: '100vh' }}>
            <Navigation open={navigationOpen} onClose={() => setNavigationOpen(false)} />
            <Box sx={{ flexGrow: 1, backgroundColor: '#f5f5f5' }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/upload" element={<DataUpload />} />
                <Route path="/exceptions" element={<ExceptionManagement />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/governance" element={<Governance />} />
                <Route path="/database-management" element={<DatabaseManagement />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/help" element={<Help />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Box>
          </Box>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
