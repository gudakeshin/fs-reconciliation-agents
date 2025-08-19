import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Chip,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ComposedChart
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  PieChart as PieChartIcon,
  BarChart as BarChartIcon,
  ShowChart,
  Timeline
} from '@mui/icons-material';

interface ChartData {
  name: string;
  value: number;
  [key: string]: any;
}

interface DataVisualizationProps {
  data: ChartData[];
  title: string;
  type: 'bar' | 'line' | 'pie' | 'area' | 'scatter' | 'radar' | 'composed';
  height?: number;
  dataKeys?: string[];
  colors?: string[];
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  xAxisDataKey?: string;
  yAxisDataKey?: string;
  stacked?: boolean;
  animate?: boolean;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

const DataVisualization: React.FC<DataVisualizationProps> = ({
  data,
  title,
  type,
  height = 400,
  dataKeys = ['value'],
  colors = COLORS,
  showLegend = true,
  showGrid = true,
  showTooltip = true,
  xAxisDataKey = 'name',
  yAxisDataKey = 'value',
  stacked = false,
  animate = true
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const renderChart = () => {
    const commonProps = {
      data,
      height: isMobile ? height * 0.7 : height,
      margin: { top: 5, right: 30, left: 20, bottom: 5 }
    };

    switch (type) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            {dataKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[index % colors.length]}
                stackId={stacked ? 'stack' : undefined}
              />
            ))}
          </BarChart>
        );

      case 'line':
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            {dataKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                dot={{ fill: colors[index % colors.length] }}
              />
            ))}
          </LineChart>
        );

      case 'pie':
        return (
          <PieChart {...commonProps}>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${percent !== undefined ? (percent * 100).toFixed(0) : '0'}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey={yAxisDataKey}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
          </PieChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            {dataKeys.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
                stackId={stacked ? 'stack' : undefined}
              />
            ))}
          </AreaChart>
        );

      case 'scatter':
        return (
          <ScatterChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            {dataKeys.map((key, index) => (
              <Scatter
                key={key}
                dataKey={key}
                fill={colors[index % colors.length]}
              />
            ))}
          </ScatterChart>
        );

      case 'radar':
        return (
          <RadarChart {...commonProps}>
            <PolarGrid />
            <PolarAngleAxis dataKey={xAxisDataKey} />
            <PolarRadiusAxis />
            {dataKeys.map((key, index) => (
              <Radar
                key={key}
                name={key}
                dataKey={key}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
              />
            ))}
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
          </RadarChart>
        );

      case 'composed':
        return (
          <ComposedChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            {showTooltip && <Tooltip />}
            {showLegend && <Legend />}
            {dataKeys.map((key, index) => (
              <Bar
                key={`bar-${key}`}
                dataKey={`${key}_bar`}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
              />
            ))}
            {dataKeys.map((key, index) => (
              <Line
                key={`line-${key}`}
                type="monotone"
                dataKey={`${key}_line`}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
              />
            ))}
          </ComposedChart>
        );

      default:
        return <Typography>Unsupported chart type</Typography>;
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <ResponsiveContainer width="100%" height={height}>
          {renderChart()}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// Dashboard Analytics Component
interface DashboardAnalyticsProps {
  exceptionData: ChartData[];
  transactionData: ChartData[];
  trendData: ChartData[];
  performanceData: ChartData[];
}

const DashboardAnalytics: React.FC<DashboardAnalyticsProps> = ({
  exceptionData,
  transactionData,
  trendData,
  performanceData
}) => {
  const [selectedTimeRange, setSelectedTimeRange] = useState('7d');
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const getChartIcon = (type: string) => {
    switch (type) {
      case 'bar': return <BarChartIcon />;
      case 'line': return <ShowChart />;
      case 'pie': return <PieChartIcon />;
      case 'area': return <Timeline />;
      default: return <TrendingUp />;
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          Analytics Dashboard
        </Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value)}
            label="Time Range"
          >
            <MenuItem value="1d">Last 24 Hours</MenuItem>
            <MenuItem value="7d">Last 7 Days</MenuItem>
            <MenuItem value="30d">Last 30 Days</MenuItem>
            <MenuItem value="90d">Last 90 Days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Grid container columns={12} spacing={3}>
        {/* Exception Trends */}
        <Grid sx={{ gridColumn: { xs: 'span 12', lg: 'span 6' } }}>
          <DataVisualization
            title="Exception Trends"
            type="line"
            data={trendData}
            dataKeys={['exceptions', 'resolved']}
            colors={[theme.palette.error.main, theme.palette.success.main]}
            height={300}
          />
        </Grid>

        {/* Break Type Distribution */}
        <Grid sx={{ gridColumn: { xs: 'span 12', lg: 'span 6' } }}>
          <DataVisualization
            title="Break Type Distribution"
            type="pie"
            data={exceptionData}
            height={300}
          />
        </Grid>

        {/* Transaction Volume */}
        <Grid sx={{ gridColumn: { xs: 'span 12', lg: 'span 6' } }}>
          <DataVisualization
            title="Transaction Volume"
            type="area"
            data={transactionData}
            dataKeys={['volume', 'matched', 'unmatched']}
            colors={[theme.palette.primary.main, theme.palette.success.main, theme.palette.warning.main]}
            height={300}
            stacked
          />
        </Grid>

        {/* Performance Metrics */}
        <Grid sx={{ gridColumn: { xs: 'span 12', lg: 'span 6' } }}>
          <DataVisualization
            title="Performance Metrics"
            type="radar"
            data={performanceData}
            dataKeys={['accuracy', 'speed', 'efficiency', 'quality']}
            height={300}
          />
        </Grid>

        {/* Resolution Rate */}
        <Grid sx={{ gridColumn: 'span 12' }}>
          <DataVisualization
            title="Resolution Rate Over Time"
            type="composed"
            data={trendData}
            dataKeys={['resolution_rate']}
            height={400}
          />
        </Grid>
      </Grid>
    </Box>
  );
};

// Real-time Metrics Component
interface RealTimeMetricsProps {
  metrics: {
    totalExceptions: number;
    resolvedExceptions: number;
    pendingExceptions: number;
    resolutionRate: number;
    avgResolutionTime: number;
    activeUsers: number;
  };
}

const RealTimeMetrics: React.FC<RealTimeMetricsProps> = ({ metrics }) => {
  const theme = useTheme();

  const metricCards = [
    {
      title: 'Total Exceptions',
      value: metrics.totalExceptions,
      color: theme.palette.primary.main,
      icon: <TrendingUp />,
      trend: '+5.2%'
    },
    {
      title: 'Resolved',
      value: metrics.resolvedExceptions,
      color: theme.palette.success.main,
      icon: <TrendingUp />,
      trend: '+12.1%'
    },
    {
      title: 'Pending',
      value: metrics.pendingExceptions,
      color: theme.palette.warning.main,
      icon: <TrendingDown />,
      trend: '-3.4%'
    },
    {
      title: 'Resolution Rate',
      value: `${metrics.resolutionRate}%`,
      color: theme.palette.info.main,
      icon: <TrendingUp />,
      trend: '+2.8%'
    }
  ];

  return (
    <Grid container columns={12} spacing={2}>
      {metricCards.map((metric, index) => (
        <Grid sx={{ gridColumn: { xs: 'span 12', sm: 'span 6', md: 'span 3' } }} key={index}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    {metric.title}
                  </Typography>
                  <Typography variant="h4" component="div" sx={{ color: metric.color }}>
                    {metric.value}
                  </Typography>
                  <Chip
                    label={metric.trend}
                    size="small"
                    color={metric.trend.startsWith('+') ? 'success' : 'error'}
                    sx={{ mt: 1 }}
                  />
                </Box>
                <Box sx={{ color: metric.color }}>
                  {metric.icon}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export { DataVisualization, DashboardAnalytics, RealTimeMetrics };
export default DataVisualization;
