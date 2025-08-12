import React, { useState, useEffect } from 'react';
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
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandMoreIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Storage as StorageIcon,
  CheckBox as CheckBoxIcon,
  CheckBoxOutlineBlank as CheckBoxOutlineBlankIcon,
  ViewList as ViewListIcon,
  Assessment as AssessmentIcon,
  Search as SearchIcon,
  Clear as ClearIcon,
  Download as DownloadIcon,
  Upload as UploadIcon
} from '@mui/icons-material';

interface TableConfig {
  display_name: string;
  columns: ColumnConfig[];
  filters: string[];
}

interface ColumnConfig {
  name: string;
  display: string;
  type: string;
  editable: boolean;
}

interface TableData {
  success: boolean;
  data: any[];
  total_count: number;
  skip: number;
  limit: number;
  table_config: {
    display_name: string;
    columns: ColumnConfig[];
  };
}

interface TableStats {
  total_records: number;
  recent_records: number;
  column_stats: Record<string, any>;
}

const DatabaseManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tables, setTables] = useState<Record<string, TableConfig>>({});
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [tableData, setTableData] = useState<TableData | null>(null);
  const [tableStats, setTableStats] = useState<TableStats | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sortBy, setSortBy] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [editForm, setEditForm] = useState<Record<string, any>>({});
  const [showStats, setShowStats] = useState(false);
  const [bulkActionDialogOpen, setBulkActionDialogOpen] = useState(false);
  const [bulkAction, setBulkAction] = useState<'delete' | 'update'>('delete');

  // Fetch available tables
  const fetchTables = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/database/tables');
      if (!response.ok) throw new Error('Failed to fetch tables');
      
      const data = await response.json();
      setTables(data.tables);
      
      // Select first table by default
      if (Object.keys(data.tables).length > 0 && !selectedTable) {
        setSelectedTable(Object.keys(data.tables)[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tables');
    } finally {
      setLoading(false);
    }
  };

  // Fetch table data
  const fetchTableData = async () => {
    if (!selectedTable) return;
    
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: (page * rowsPerPage).toString(),
        limit: rowsPerPage.toString(),
        sort_order: sortOrder
      });

      if (sortBy) {
        params.append('sort_by', sortBy);
      }

      if (Object.keys(filters).length > 0) {
        params.append('filters', JSON.stringify(filters));
      }

      const response = await fetch(`/api/v1/database/${selectedTable}?${params}`);
      if (!response.ok) throw new Error('Failed to fetch table data');
      
      const data = await response.json();
      setTableData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch table data');
    } finally {
      setLoading(false);
    }
  };

  // Fetch table statistics
  const fetchTableStats = async () => {
    if (!selectedTable) return;
    
    try {
      const response = await fetch(`/api/v1/database/${selectedTable}/stats`);
      if (!response.ok) throw new Error('Failed to fetch table stats');
      
      const data = await response.json();
      setTableStats(data.stats);
    } catch (err) {
      console.error('Failed to fetch table stats:', err);
    }
  };

  // Handle table selection
  const handleTableChange = (tableName: string) => {
    setSelectedTable(tableName);
    setPage(0);
    setFilters({});
    setSortBy('');
    setSelectedRows(new Set());
    setTableData(null);
    setTableStats(null);
  };

  // Handle row selection
  const handleRowSelect = (recordId: string) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(recordId)) {
      newSelected.delete(recordId);
    } else {
      newSelected.add(recordId);
    }
    setSelectedRows(newSelected);
  };

  // Handle select all
  const handleSelectAll = () => {
    if (selectedRows.size === tableData?.data.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(tableData?.data.map(record => record.id) || []));
    }
  };

  // Handle edit record
  const handleEditRecord = (record: any) => {
    setEditingRecord(record);
    setEditForm(record);
    setEditDialogOpen(true);
  };

  // Handle save record
  const handleSaveRecord = async () => {
    if (!editingRecord || !selectedTable) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/database/${selectedTable}/${editingRecord.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editForm)
      });
      
      if (!response.ok) throw new Error('Failed to update record');
      
      setEditDialogOpen(false);
      setEditingRecord(null);
      fetchTableData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update record');
    } finally {
      setLoading(false);
    }
  };

  // Handle delete record
  const handleDeleteRecord = async (recordId: string) => {
    if (!window.confirm('Are you sure you want to delete this record?')) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/database/${selectedTable}/${recordId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) throw new Error('Failed to delete record');
      
      fetchTableData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete record');
    } finally {
      setLoading(false);
    }
  };

  // Handle bulk delete
  const handleBulkDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete ${selectedRows.size} records?`)) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/database/${selectedTable}/bulk`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(Array.from(selectedRows))
      });
      
      if (!response.ok) throw new Error('Failed to delete records');
      
      setSelectedRows(new Set());
      setBulkActionDialogOpen(false);
      fetchTableData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete records');
    } finally {
      setLoading(false);
    }
  };

  // Apply filters
  const applyFilters = () => {
    setPage(0);
    fetchTableData();
  };

  // Clear filters
  const clearFilters = () => {
    setFilters({});
    setPage(0);
    fetchTableData();
  };

  // Export data
  const exportData = () => {
    if (!tableData) return;
    
    const csvContent = [
      // Header
      tableData.table_config.columns.map(col => col.display).join(','),
      // Data
      ...tableData.data.map(record => 
        tableData.table_config.columns.map(col => {
          const value = record[col.name];
          return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
        }).join(',')
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedTable}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Effects
  useEffect(() => {
    fetchTables();
  }, []);

  useEffect(() => {
    if (selectedTable) {
      fetchTableData();
      fetchTableStats();
    }
  }, [selectedTable, page, rowsPerPage, sortBy, sortOrder]);

  if (loading && !tableData) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2 }}>Loading database management...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Database Management
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Table Selection */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Select Table
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {Object.entries(tables).map(([tableName, config]) => (
              <Chip
                key={tableName}
                label={config.display_name}
                onClick={() => handleTableChange(tableName)}
                color={selectedTable === tableName ? 'primary' : 'default'}
                variant={selectedTable === tableName ? 'filled' : 'outlined'}
                icon={<StorageIcon />}
              />
            ))}
          </Box>
        </CardContent>
      </Card>

      {selectedTable && tableData && (
        <>
          {/* Statistics */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  {tableData.table_config.display_name} Statistics
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={showStats}
                      onChange={(e) => setShowStats(e.target.checked)}
                    />
                  }
                  label="Show Detailed Stats"
                />
              </Box>
              
              <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
                <Typography>
                  Total Records: <strong>{tableStats?.total_records || 0}</strong>
                </Typography>
                <Typography>
                  Recent Records (Today): <strong>{tableStats?.recent_records || 0}</strong>
                </Typography>
                <Typography>
                  Current Page: <strong>{tableData.data.length}</strong> of {tableData.total_count}
                </Typography>
              </Box>

              {showStats && tableStats?.column_stats && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Column Statistics</Typography>
                  </AccordionSummary>
                                     <AccordionDetails>
                     <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                       {Object.entries(tableStats.column_stats).map(([column, stats]) => (
                         <Box key={column} sx={{ flex: '1 1 300px', minWidth: 0 }}>
                           <Typography variant="subtitle2" color="primary">
                             {column}
                           </Typography>
                           <Typography variant="body2">
                             {JSON.stringify(stats, null, 2)}
                           </Typography>
                         </Box>
                       ))}
                     </Box>
                   </AccordionDetails>
                </Accordion>
              )}
            </CardContent>
          </Card>

          {/* Filters */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Filters & Search
              </Typography>
                             <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
                 {tables[selectedTable]?.filters.map(filter => (
                   <Box key={filter} sx={{ flex: '1 1 200px', minWidth: 0 }}>
                     <TextField
                       fullWidth
                       size="small"
                       label={filter.replace('_', ' ').toUpperCase()}
                       value={filters[filter] || ''}
                       onChange={(e) => setFilters({ ...filters, [filter]: e.target.value })}
                     />
                   </Box>
                 ))}
                 <Box sx={{ flex: '1 1 200px', minWidth: 0 }}>
                   <FormControl fullWidth size="small">
                     <InputLabel>Sort By</InputLabel>
                     <Select
                       value={sortBy}
                       label="Sort By"
                       onChange={(e) => setSortBy(e.target.value)}
                     >
                       <MenuItem value="">Default</MenuItem>
                       {tableData.table_config.columns.map(col => (
                         <MenuItem key={col.name} value={col.name}>
                           {col.display}
                         </MenuItem>
                       ))}
                     </Select>
                   </FormControl>
                 </Box>
                 <Box sx={{ flex: '1 1 200px', minWidth: 0 }}>
                   <FormControl fullWidth size="small">
                     <InputLabel>Sort Order</InputLabel>
                     <Select
                       value={sortOrder}
                       label="Sort Order"
                       onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                     >
                       <MenuItem value="desc">Descending</MenuItem>
                       <MenuItem value="asc">Ascending</MenuItem>
                     </Select>
                   </FormControl>
                 </Box>
                 <Box sx={{ flex: '1 1 200px', minWidth: 0 }}>
                   <Box sx={{ display: 'flex', gap: 1 }}>
                     <Button
                       variant="outlined"
                       startIcon={<FilterIcon />}
                       onClick={applyFilters}
                     >
                       Apply
                     </Button>
                     <Button
                       variant="outlined"
                       startIcon={<ClearIcon />}
                       onClick={clearFilters}
                     >
                       Clear
                     </Button>
                   </Box>
                 </Box>
               </Box>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Actions
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant="outlined"
                    startIcon={<RefreshIcon />}
                    onClick={fetchTableData}
                  >
                    Refresh
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={exportData}
                  >
                    Export CSV
                  </Button>
                  {selectedRows.size > 0 && (
                    <Button
                      variant="contained"
                      color="error"
                      startIcon={<DeleteIcon />}
                      onClick={() => setBulkActionDialogOpen(true)}
                    >
                      Delete Selected ({selectedRows.size})
                    </Button>
                  )}
                </Box>
              </Box>
            </CardContent>
          </Card>

          {/* Data Table */}
          <Card>
            <CardContent>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox">
                        <Checkbox
                          indeterminate={selectedRows.size > 0 && selectedRows.size < tableData.data.length}
                          checked={selectedRows.size === tableData.data.length && tableData.data.length > 0}
                          onChange={handleSelectAll}
                        />
                      </TableCell>
                      {tableData.table_config.columns.map(column => (
                        <TableCell key={column.name}>
                          {column.display}
                        </TableCell>
                      ))}
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {tableData.data.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedRows.has(record.id)}
                            onChange={() => handleRowSelect(record.id)}
                          />
                        </TableCell>
                        {tableData.table_config.columns.map(column => (
                          <TableCell key={column.name}>
                            {column.type === 'datetime' && record[column.name] ? (
                              new Date(record[column.name]).toLocaleString()
                            ) : column.type === 'text' && record[column.name] ? (
                              <Typography sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {record[column.name].substring(0, 100)}
                                {record[column.name].length > 100 ? '...' : ''}
                              </Typography>
                            ) : (
                              record[column.name] || '-'
                            )}
                          </TableCell>
                        ))}
                        <TableCell>
                          <Box display="flex" gap={1}>
                            {tableData.table_config.columns.some(col => col.editable) && (
                              <Tooltip title="Edit Record">
                                <IconButton 
                                  size="small" 
                                  color="primary"
                                  onClick={() => handleEditRecord(record)}
                                >
                                  <EditIcon />
                                </IconButton>
                              </Tooltip>
                            )}
                            <Tooltip title="Delete Record">
                              <IconButton 
                                size="small" 
                                color="error"
                                onClick={() => handleDeleteRecord(record.id)}
                              >
                                <DeleteIcon />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              <TablePagination
                component="div"
                count={tableData.total_count}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={(e, newPage) => setPage(newPage)}
                onRowsPerPageChange={(e) => {
                  setRowsPerPage(parseInt(e.target.value, 10));
                  setPage(0);
                }}
                rowsPerPageOptions={[10, 25, 50, 100]}
              />
            </CardContent>
          </Card>
        </>
      )}

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Record</DialogTitle>
                 <DialogContent>
           <Box sx={{ mt: 1 }}>
             <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
               {editingRecord && tableData?.table_config.columns
                 .filter(col => col.editable)
                 .map(column => (
                   <Box key={column.name} sx={{ flex: '1 1 300px', minWidth: 0 }}>
                     <TextField
                       fullWidth
                       label={column.display}
                       value={editForm[column.name] || ''}
                       onChange={(e) => setEditForm({ ...editForm, [column.name]: e.target.value })}
                       multiline={column.type === 'text'}
                       rows={column.type === 'text' ? 3 : 1}
                     />
                   </Box>
                 ))}
             </Box>
           </Box>
         </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveRecord} variant="contained" color="primary">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Action Dialog */}
      <Dialog open={bulkActionDialogOpen} onClose={() => setBulkActionDialogOpen(false)}>
        <DialogTitle>Bulk Delete Confirmation</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete {selectedRows.size} selected records? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkActionDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleBulkDelete} variant="contained" color="error">
            Delete {selectedRows.size} Records
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DatabaseManagement;
