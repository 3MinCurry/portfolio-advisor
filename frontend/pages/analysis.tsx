import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '@clerk/nextjs';
import {
  PieChart, Pie, Cell, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import Layout from '../components/Layout';
import PageHeader from '../components/PageHeader';
import MarkdownContent from '../components/MarkdownContent';
import { CHART_COLORS } from '../lib/chartColors';
import { API_URL } from '../lib/config';
import Head from 'next/head';

interface Job {
  id: string;
  created_at: string;
  status: string;
  job_type: string;
  report_payload?: {
    agent: string;
    content: string;
    generated_at: string;
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  charts_payload?: Record<string, any> | null;  // Charter stores charts with dynamic keys
  retirement_payload?: {
    agent: string;
    analysis: string;
    generated_at: string;
  };
  risk_payload?: {
    agent: string;
    analysis: string;
    generated_at: string;
    metrics?: {
      risk_level?: string;
      top_holding_symbol?: string;
      top_holding_pct?: number;
      herfindahl_positions?: number;
      equity_pct?: number;
    };
  };
  error_message?: string;
}

interface JobListItem {
  id: string;
  created_at: string;
  status: string;
  job_type: string;
}

type TabType = 'overview' | 'charts' | 'risk' | 'retirement';

const COLORS = CHART_COLORS;

export default function Analysis() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { job_id } = router.query;
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [fetchingLatest, setFetchingLatest] = useState(false);

  useEffect(() => {
    const loadJob = async (jobId: string) => {
      try {
        const token = await getToken();
        const response = await fetch(`${API_URL}/api/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const jobData = await response.json();
          setJob(jobData);
        } else {
          console.error('Failed to fetch job');
        }
      } catch (error) {
        console.error('Error fetching job:', error);
      } finally {
        setLoading(false);
      }
    };

    const loadLatestJob = async () => {
      setFetchingLatest(true);
      try {
        const token = await getToken();
        // First, get the list of jobs to find the latest completed one
        const response = await fetch(`${API_URL}/api/jobs`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          const jobs: JobListItem[] = data.jobs || [];
          // Find the latest completed job
          const latestCompletedJob = jobs
            .filter(j => j.status === 'completed')
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

          if (latestCompletedJob) {
            // Load the full job details
            await loadJob(latestCompletedJob.id);
            // Update the URL to include the job_id without causing a page reload
            router.replace(`/analysis?job_id=${latestCompletedJob.id}`, undefined, { shallow: true });
          } else {
            setLoading(false);
          }
        } else {
          setLoading(false);
        }
      } catch (error) {
        console.error('Error fetching latest job:', error);
        setLoading(false);
      } finally {
        setFetchingLatest(false);
      }
    };

    if (job_id) {
      loadJob(job_id as string);
    } else if (router.isReady) {
      // Router is ready but no job_id provided - fetch the latest analysis
      loadLatestJob();
    }
  }, [job_id, router.isReady, getToken, router]);


  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto panel px-8 py-12 text-center">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-surface-raised rounded w-1/3 mx-auto" />
            <div className="h-4 bg-surface-raised rounded w-1/2 mx-auto" />
          </div>
        </div>
      </Layout>
    );
  }

  if (!job) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto panel px-8 py-12 text-center">
          <p className="eyebrow mb-2">Analysis</p>
          <h2 className="page-title mb-4">
            {fetchingLatest ? 'Loading...' : 'No analysis yet'}
          </h2>
          <p className="text-muted mb-8 max-w-md mx-auto">
            {fetchingLatest
              ? 'Fetching your latest completed run.'
              : 'Run an analysis from the Advisors page to see results here.'}
          </p>
          {!fetchingLatest && (
            <button type="button" onClick={() => router.push('/advisor-team')} className="btn btn-primary">
              Start analysis
            </button>
          )}
        </div>
      </Layout>
    );
  }

  if (job.status === 'running' || job.status === 'pending') {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto panel px-8 py-12 text-center">
          <p className="eyebrow mb-2">In progress</p>
          <h2 className="page-title mb-4">Analysis running</h2>
          <p className="text-muted mb-8">Your agents are still working. Check back shortly.</p>
          <div className="flex justify-center gap-2 mb-8">
            <div className="w-2 h-2 rounded-full bg-sage animate-pulse" />
            <div className="w-2 h-2 rounded-full bg-sage animate-pulse" style={{ animationDelay: '0.3s' }} />
            <div className="w-2 h-2 rounded-full bg-sage animate-pulse" style={{ animationDelay: '0.6s' }} />
          </div>
          <button type="button" onClick={() => window.location.reload()} className="btn btn-secondary">
            Refresh
          </button>
        </div>
      </Layout>
    );
  }

  if (job.status === 'failed') {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto panel px-8 py-12">
          <p className="eyebrow text-coral mb-2">Failed</p>
          <h2 className="page-title mb-4">Analysis could not complete</h2>
          {job.error_message && (
            <div className="alert-error mb-6 text-sm">{job.error_message}</div>
          )}
          <button type="button" onClick={() => router.push('/advisor-team')} className="btn btn-primary">
            Try again
          </button>
        </div>
      </Layout>
    );
  }


  // Tab content renderers
  const renderOverview = () => {
    const report = job?.report_payload?.content;
    if (!report) {
      return <div className="text-center py-12 text-muted">No portfolio report available.</div>;
    }
    return <MarkdownContent>{report}</MarkdownContent>;
  };

  const renderCharts = () => {
    const chartsPayload = job?.charts_payload;
    if (!chartsPayload || Object.keys(chartsPayload).length === 0) {
      return (
        <div className="text-center py-12 text-muted">
          No chart data available.
        </div>
      );
    }

    // Helper function to format chart title from key
    const formatTitle = (key: string): string => {
      return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    };

    // Helper function to determine chart type based on data structure or chart metadata
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const getChartType = (chartData: any): 'pie' | 'donut' | 'bar' | 'horizontalBar' | 'line' => {
      // If the charter agent specifies a type, use it directly if supported
      if (chartData.type) {
        const supportedTypes = ['pie', 'donut', 'bar', 'horizontalBar', 'line'];
        if (supportedTypes.includes(chartData.type)) {
          return chartData.type;
        }
        // Map variations to supported types
        const typeMap: Record<string, 'pie' | 'donut' | 'bar' | 'horizontalBar' | 'line'> = {
          'column': 'bar',
          'area': 'line'
        };
        if (typeMap[chartData.type]) {
          return typeMap[chartData.type];
        }
      }

      // Otherwise, make an intelligent guess based on the data
      // If data has dates/time series, use line chart
      if (chartData.data?.[0]?.date || chartData.data?.[0]?.year) return 'line';

      // If data represents parts of a whole (has percentages or small dataset), use pie
      if (chartData.data?.length <= 10 && chartData.data?.[0]?.value) return 'pie';

      // Default to bar chart for other cases
      return 'bar';
    };

    // Dynamically render all charts provided by the charter agent
    const chartEntries = Object.entries(chartsPayload);

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        {chartEntries.map(([key, chartData]: [string, any]) => {
          // Skip if no data
          if (!chartData?.data || chartData.data.length === 0) return null;

          const chartType = getChartType(chartData);
          const title = chartData.title || formatTitle(key);

          return (
            <div key={key} className="panel-raised p-6">
              <h3 className="font-display text-xl font-semibold mb-4 text-ink">{title}</h3>
              <ResponsiveContainer width="100%" height={300}>
                {chartType === 'pie' || chartType === 'donut' ? (
                  <PieChart>
                    <Pie
                      data={chartData.data}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label
                      outerRadius={100}
                      innerRadius={chartType === 'donut' ? 60 : 0}  // Donut has inner radius
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                      {chartData.data.map((entry: any, idx: number) => (
                        <Cell key={`cell-${idx}`} fill={entry.color || COLORS[idx % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => `$${value.toLocaleString('en-US')}`} />
                  </PieChart>
                ) : chartType === 'horizontalBar' ? (
                  // For horizontal bars, just use regular vertical bars with rotated labels
                  // Recharts horizontal layout can be problematic
                  <BarChart
                    data={chartData.data}
                    margin={{ left: 10, right: 30, top: 5, bottom: 60 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="name"
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                      height={60}
                    />
                    <YAxis
                      tickFormatter={(value) => `$${(value/1000).toFixed(0)}k`}
                    />
                    <Tooltip formatter={(value: number) => `$${value.toLocaleString('en-US')}`} />
                    <Bar dataKey="value">
                      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                      {chartData.data?.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                ) : chartType === 'bar' ? (
                  <BarChart data={chartData.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                    <YAxis tickFormatter={(value) => `$${(value/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value: number) => `$${value.toLocaleString('en-US')}`} />
                    <Bar dataKey="value" fill={chartData.color || COLORS[0]} />
                  </BarChart>
                ) : (
                  // Line chart for time series data
                  <LineChart data={chartData.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey={chartData.xKey || "year"} />
                    <YAxis tickFormatter={(value) => `$${(value/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value: number) => `$${value.toLocaleString('en-US')}`} />
                    <Line type="monotone" dataKey="value" stroke={COLORS[0]} strokeWidth={2} />
                  </LineChart>
                )}
              </ResponsiveContainer>

              {/* Add legend for pie/donut charts with many items */}
              {(chartType === 'pie' || chartType === 'donut') && chartData.data.length > 6 && (
                <div className="mt-4 grid grid-cols-2 gap-2">
                  {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                  {chartData.data.map((entry: any, idx: number) => (
                    <div key={entry.name} className="flex items-center text-sm">
                      <div
                        className="w-3 h-3 rounded-full mr-2"
                        style={{ backgroundColor: entry.color || COLORS[idx % COLORS.length] }}
                      />
                      <span className="text-muted">{entry.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const riskLevelColor = (level?: string) => {
    switch (level?.toLowerCase()) {
      case 'low': return 'badge-low';
      case 'moderate': return 'badge-moderate';
      case 'elevated': return 'badge-elevated';
      case 'high': return 'badge-high';
      default: return 'panel-raised px-4 py-2 text-muted';
    }
  };

  const renderRisk = () => {
    const risk = job?.risk_payload;
    if (!risk) {
      return (
        <div className="text-center py-12 text-muted">No risk assessment available.</div>
      );
    }

    const riskAnalysis = risk.analysis;
    const metrics = risk.metrics;

    return (
      <div className="space-y-8">
        {metrics?.risk_level && (
          <div className={`inline-flex items-center px-4 py-2 rounded-lg border font-semibold ${riskLevelColor(metrics.risk_level)}`}>
            Overall risk: {metrics.risk_level}
            {metrics.top_holding_symbol != null && (
              <span className="ml-3 font-normal text-sm">
                Largest holding: {metrics.top_holding_symbol} ({metrics.top_holding_pct}%)
              </span>
            )}
          </div>
        )}

        {riskAnalysis && (
          <div className="panel-raised p-6 border-coral/20">
            <MarkdownContent>{riskAnalysis}</MarkdownContent>
          </div>
        )}
      </div>
    );
  };

  const renderRetirement = () => {
    const retirement = job?.retirement_payload;
    if (!retirement) {
      return (
        <div className="text-center py-12 text-muted">No retirement projection available.</div>
      );
    }

    // Backend provides 'analysis' as markdown text
    const retirementAnalysis = retirement.analysis;

    return (
      <div className="space-y-8">
        {/* Analysis Section */}
        {retirementAnalysis && (
          <div className="panel-raised p-6 border-sage/20">
            <MarkdownContent>{retirementAnalysis}</MarkdownContent>
          </div>
        )}

      </div>
    );
  };

  return (
    <>
      <Head>
        <title>Analysis - Alex AI Financial Advisor</title>
      </Head>
      <Layout>
        <div className="max-w-6xl mx-auto">
          <PageHeader
            eyebrow="Results"
            title="Portfolio analysis"
            description={`Completed ${formatDate(job.created_at)}`}
            action={
              <button type="button" onClick={() => router.push('/advisor-team')} className="btn btn-sage">
                New analysis
              </button>
            }
          />

          <div className="panel mb-6 overflow-x-auto">
            <nav className="flex border-b border-border min-w-max">
              {(['overview', 'charts', 'risk', 'retirement'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={activeTab === tab ? 'tab tab-active' : 'tab'}
                >
                  {tab === 'overview' && 'Overview'}
                  {tab === 'charts' && 'Charts'}
                  {tab === 'risk' && 'Risk'}
                  {tab === 'retirement' && 'Retirement'}
                </button>
              ))}
            </nav>
          </div>

          <div className="panel px-8 py-6">
            {activeTab === 'overview' && renderOverview()}
            {activeTab === 'charts' && renderCharts()}
            {activeTab === 'risk' && renderRisk()}
            {activeTab === 'retirement' && renderRetirement()}
          </div>
        </div>
      </Layout>
    </>
  );
}