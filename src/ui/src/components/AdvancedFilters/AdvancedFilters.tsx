import React, { useState, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Button,
  IconButton,
  Collapse,
  Slider,
  FormControlLabel,
  Switch,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
  useMediaQuery,
  Grid
} from '@mui/material';
import {
  FilterList,
  ExpandMore,
  Clear,
  Search,
  DateRange,
  AttachMoney,
  Security,
  TrendingUp
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

interface FilterState {
  searchTerm: string;
  breakType: string[];
  severity: string[];
  status: string[];
  assignedTo: string[];
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
  amountRange: {
    min: number;
    max: number;
  };
  priority: string[];
  dataSource: string[];
}

interface AdvancedFiltersProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  onClearFilters: () => void;
  onApplyFilters: () => void;
  availableOptions: {
    breakTypes: string[];
    severities: string[];
    statuses: string[];
    users: string[];
    priorities: string[];
    dataSources: string[];
  };
}

const AdvancedFilters: React.FC<AdvancedFiltersProps> = ({
  filters,
  onFiltersChange,
  onClearFilters,
  onApplyFilters,
  availableOptions
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [expanded, setExpanded] = useState(false);

  const handleFilterChange = useCallback((key: keyof FilterState, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  }, [filters, onFiltersChange]);

  const handleArrayFilterChange = useCallback((key: keyof FilterState, value: string, add: boolean) => {
    const currentArray = filters[key] as string[];
    const newArray = add 
      ? [...currentArray, value]
      : currentArray.filter(item => item !== value);
    
    handleFilterChange(key, newArray);
  }, [filters, handleFilterChange]);

  const handleDateRangeChange = useCallback((field: 'start' | 'end', value: Date | null) => {
    handleFilterChange('dateRange', {
      ...filters.dateRange,
      [field]: value
    });
  }, [filters.dateRange, handleFilterChange]);

  const handleAmountRangeChange = useCallback((field: 'min' | 'max', value: number) => {
    handleFilterChange('amountRange', {
      ...filters.amountRange,
      [field]: value
    });
  }, [filters.amountRange, handleFilterChange]);

  const clearAllFilters = () => {
    onClearFilters();
  };

  const getActiveFiltersCount = () => {
    let count = 0;
    if (filters.searchTerm) count++;
    if (filters.breakType.length > 0) count++;
    if (filters.severity.length > 0) count++;
    if (filters.status.length > 0) count++;
    if (filters.assignedTo.length > 0) count++;
    if (filters.dateRange.start || filters.dateRange.end) count++;
    if (filters.amountRange.min > 0 || filters.amountRange.max < 1000000) count++;
    if (filters.priority.length > 0) count++;
    if (filters.dataSource.length > 0) count++;
    return count;
  };

  const FilterChip = ({ label, onDelete }: { label: string; onDelete: () => void }) => (
    <Chip
      label={label}
      onDelete={onDelete}
      size="small"
      sx={{ m: 0.5 }}
    />
  );

  const FilterSection = ({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) => (
    <Accordion defaultExpanded={!isMobile}>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Box display="flex" alignItems="center" gap={1}>
          {icon}
          <Typography variant="subtitle2">{title}</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {children}
      </AccordionDetails>
    </Accordion>
  );

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <FilterList color="primary" />
            <Typography variant="h6">Advanced Filters</Typography>
            {getActiveFiltersCount() > 0 && (
              <Chip
                label={getActiveFiltersCount()}
                color="primary"
                size="small"
              />
            )}
          </Box>
          <Box display="flex" gap={1}>
            <Button
              variant="outlined"
              size="small"
              onClick={() => setExpanded(!expanded)}
              startIcon={expanded ? <ExpandMore /> : <FilterList />}
            >
              {expanded ? 'Collapse' : 'Expand'}
            </Button>
            {getActiveFiltersCount() > 0 && (
              <Button
                variant="outlined"
                size="small"
                onClick={clearAllFilters}
                startIcon={<Clear />}
                color="error"
              >
                Clear All
              </Button>
            )}
          </Box>
        </Box>

        <Collapse in={expanded || !isMobile}>
          <Grid container columns={12} spacing={2}>
            {/* Search and Basic Filters */}
            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
              <TextField
                fullWidth
                label="Search"
                value={filters.searchTerm}
                onChange={(e) => handleFilterChange('searchTerm', e.target.value)}
                placeholder="Search exceptions, descriptions, IDs..."
                InputProps={{
                  startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
                }}
                size="small"
              />
            </Grid>

            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  multiple
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {availableOptions.statuses.map((status) => (
                    <MenuItem key={status} value={status}>
                      {status}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Break Type and Severity */}
            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
              <FormControl fullWidth size="small">
                <InputLabel>Break Type</InputLabel>
                <Select
                  multiple
                  value={filters.breakType}
                  onChange={(e) => handleFilterChange('breakType', e.target.value)}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {availableOptions.breakTypes.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
              <FormControl fullWidth size="small">
                <InputLabel>Severity</InputLabel>
                <Select
                  multiple
                  value={filters.severity}
                  onChange={(e) => handleFilterChange('severity', e.target.value)}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {availableOptions.severities.map((severity) => (
                    <MenuItem key={severity} value={severity}>
                      {severity}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Date Range */}
            <Grid sx={{ gridColumn: 'span 12' }}>
              <FilterSection title="Date Range" icon={<DateRange />}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <Grid container columns={12} spacing={2}>
                    <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                      <DatePicker
                        label="Start Date"
                        value={filters.dateRange.start}
                        onChange={(date) => handleDateRangeChange('start', date)}
                        slotProps={{
                          textField: {
                            fullWidth: true,
                            size: 'small'
                          }
                        }}
                      />
                    </Grid>
                    <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
                      <DatePicker
                        label="End Date"
                        value={filters.dateRange.end}
                        onChange={(date) => handleDateRangeChange('end', date)}
                        slotProps={{
                          textField: {
                            fullWidth: true,
                            size: 'small'
                          }
                        }}
                      />
                    </Grid>
                  </Grid>
                </LocalizationProvider>
              </FilterSection>
            </Grid>

            {/* Amount Range */}
            <Grid sx={{ gridColumn: 'span 12' }}>
              <FilterSection title="Amount Range" icon={<AttachMoney />}>
                <Box sx={{ px: 2 }}>
                  <Typography gutterBottom>
                    Amount Range: ${filters.amountRange.min.toLocaleString()} - ${filters.amountRange.max.toLocaleString()}
                  </Typography>
                  <Slider
                    value={[filters.amountRange.min, filters.amountRange.max]}
                    onChange={(_, value) => {
                      const [min, max] = value as number[];
                      handleFilterChange('amountRange', { min, max });
                    }}
                    min={0}
                    max={1000000}
                    step={1000}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) => `$${value.toLocaleString()}`}
                  />
                </Box>
              </FilterSection>
            </Grid>

            {/* Assigned To and Priority */}
            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
              <FilterSection title="Assigned To" icon={<Security />}>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {availableOptions.users.map((user) => (
                    <Chip
                      key={user}
                      label={user}
                      onClick={() => handleArrayFilterChange('assignedTo', user, !filters.assignedTo.includes(user))}
                      color={filters.assignedTo.includes(user) ? 'primary' : 'default'}
                      variant={filters.assignedTo.includes(user) ? 'filled' : 'outlined'}
                      clickable
                    />
                  ))}
                </Box>
              </FilterSection>
            </Grid>

            <Grid sx={{ gridColumn: { xs: 'span 12', md: 'span 6' } }}>
              <FilterSection title="Priority" icon={<TrendingUp />}>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {availableOptions.priorities.map((priority) => (
                    <Chip
                      key={priority}
                      label={priority}
                      onClick={() => handleArrayFilterChange('priority', priority, !filters.priority.includes(priority))}
                      color={filters.priority.includes(priority) ? 'primary' : 'default'}
                      variant={filters.priority.includes(priority) ? 'filled' : 'outlined'}
                      clickable
                    />
                  ))}
                </Box>
              </FilterSection>
            </Grid>

            {/* Data Source */}
            <Grid sx={{ gridColumn: 'span 12' }}>
              <FilterSection title="Data Source" icon={<Security />}>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {availableOptions.dataSources.map((source) => (
                    <Chip
                      key={source}
                      label={source}
                      onClick={() => handleArrayFilterChange('dataSource', source, !filters.dataSource.includes(source))}
                      color={filters.dataSource.includes(source) ? 'primary' : 'default'}
                      variant={filters.dataSource.includes(source) ? 'filled' : 'outlined'}
                      clickable
                    />
                  ))}
                </Box>
              </FilterSection>
            </Grid>
          </Grid>

          {/* Action Buttons */}
          <Box display="flex" justifyContent="flex-end" gap={2} mt={2}>
            <Button
              variant="outlined"
              onClick={clearAllFilters}
              startIcon={<Clear />}
            >
              Clear Filters
            </Button>
            <Button
              variant="contained"
              onClick={onApplyFilters}
              startIcon={<FilterList />}
            >
              Apply Filters
            </Button>
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default AdvancedFilters;
