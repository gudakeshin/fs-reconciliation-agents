import React from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Chip,
  Avatar,
  Tooltip,
  IconButton
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  CloudUpload as UploadIcon,
  Error as ExceptionIcon,
  Assessment as ReportsIcon,
  Settings as SettingsIcon,
  Help as HelpIcon,
  Logout as LogoutIcon,
  AccountCircle as UserIcon,
  Notifications as NotificationsIcon,
  Security as GovernanceIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

const DRAWER_WIDTH = 280;

interface NavigationProps {
  open: boolean;
  onClose: () => void;
}

const Navigation: React.FC<NavigationProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      text: 'Dashboard',
      icon: <DashboardIcon />,
      path: '/dashboard',
      badge: null
    },
    {
      text: 'Data Upload',
      icon: <UploadIcon />,
      path: '/upload',
      badge: null
    },
    {
      text: 'Exception Management',
      icon: <ExceptionIcon />,
      path: '/exceptions',
      badge: '5' // Example badge count
    },
    {
      text: 'Reports',
      icon: <ReportsIcon />,
      path: '/reports',
      badge: null
    },
    {
      text: 'Governance',
      icon: <GovernanceIcon />,
      path: '/governance',
      badge: null
    }
  ];

  const secondaryMenuItems = [
    {
      text: 'Settings',
      icon: <SettingsIcon />,
      path: '/settings',
      badge: null
    },
    {
      text: 'Help',
      icon: <HelpIcon />,
      path: '/help',
      badge: null
    }
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
    if (window.innerWidth < 1200) {
      onClose();
    }
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: '#1a1a1a',
          color: '#ffffff',
          borderRight: '1px solid #333333'
        }
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid #333333' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Avatar sx={{ bgcolor: '#1976d2', mr: 2 }}>
            <DashboardIcon />
          </Avatar>
          <Box>
            <Typography variant="h6" sx={{ color: '#ffffff', fontWeight: 'bold' }}>
              FS Reconciliation
            </Typography>
            <Typography variant="caption" sx={{ color: '#888888' }}>
              Agentic AI System
            </Typography>
          </Box>
        </Box>
        
        {/* System Status */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Chip 
            label="System Online" 
            size="small" 
            color="success" 
            sx={{ 
              backgroundColor: '#4caf50',
              color: '#ffffff',
              fontSize: '0.75rem'
            }} 
          />
          <IconButton size="small" sx={{ color: '#888888' }}>
            <NotificationsIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Main Navigation */}
      <Box sx={{ flexGrow: 1, py: 1 }}>
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                sx={{
                  mx: 1,
                  borderRadius: 1,
                  mb: 0.5,
                  backgroundColor: isActive(item.path) ? '#1976d2' : 'transparent',
                  color: isActive(item.path) ? '#ffffff' : '#cccccc',
                  '&:hover': {
                    backgroundColor: isActive(item.path) ? '#1565c0' : '#333333',
                    color: '#ffffff'
                  }
                }}
              >
                <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={item.text} 
                  primaryTypographyProps={{ 
                    fontSize: '0.9rem',
                    fontWeight: isActive(item.path) ? 'bold' : 'normal'
                  }}
                />
                {item.badge && (
                  <Chip 
                    label={item.badge} 
                    size="small" 
                    color="error"
                    sx={{ 
                      backgroundColor: '#f44336',
                      color: '#ffffff',
                      fontSize: '0.7rem',
                      height: 20
                    }} 
                  />
                )}
              </ListItemButton>
            </ListItem>
          ))}
        </List>

        <Divider sx={{ borderColor: '#333333', my: 2 }} />

        {/* Secondary Navigation */}
        <List>
          {secondaryMenuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                sx={{
                  mx: 1,
                  borderRadius: 1,
                  mb: 0.5,
                  backgroundColor: isActive(item.path) ? '#1976d2' : 'transparent',
                  color: isActive(item.path) ? '#ffffff' : '#888888',
                  '&:hover': {
                    backgroundColor: isActive(item.path) ? '#1565c0' : '#333333',
                    color: '#ffffff'
                  }
                }}
              >
                <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={item.text} 
                  primaryTypographyProps={{ 
                    fontSize: '0.85rem',
                    fontWeight: isActive(item.path) ? 'bold' : 'normal'
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>

      {/* User Section */}
      <Box sx={{ p: 2, borderTop: '1px solid #333333' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Avatar sx={{ bgcolor: '#666666', mr: 2 }}>
            <UserIcon />
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="body2" sx={{ color: '#ffffff', fontWeight: 'medium' }}>
              Admin User
            </Typography>
            <Typography variant="caption" sx={{ color: '#888888' }}>
              admin@fsreconciliation.com
            </Typography>
          </Box>
        </Box>
        
        <ListItemButton
          sx={{
            borderRadius: 1,
            color: '#888888',
            '&:hover': {
              backgroundColor: '#333333',
              color: '#ffffff'
            }
          }}
        >
          <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
            <LogoutIcon />
          </ListItemIcon>
          <ListItemText 
            primary="Logout" 
            primaryTypographyProps={{ fontSize: '0.85rem' }}
          />
        </ListItemButton>
      </Box>
    </Drawer>
  );
};

export default Navigation;
