import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '@clerk/nextjs';
import Layout from '../components/Layout';
import PageHeader from '../components/PageHeader';
import { API_URL } from '../lib/config';
import { emitAnalysisCompleted, emitAnalysisFailed, emitAnalysisStarted } from '../lib/events';
import Head from 'next/head';

interface Agent {
  glyph: string;
  name: string;
  role: string;
  description: string;
  accent: string;
}

interface Job {
  id: string;
  created_at: string;
  status: string;
  job_type: string;
}

interface AnalysisProgress {
  stage: 'idle' | 'starting' | 'planner' | 'parallel' | 'completing' | 'complete' | 'error';
  message: string;
  activeAgents: string[];
  error?: string;
}

const agents: Agent[] = [
  {
    glyph: '◎',
    name: 'Financial Planner',
    role: 'Orchestrator',
    description: 'Coordinates the full analysis pipeline',
    accent: 'text-gold',
  },
  {
    glyph: '◈',
    name: 'Portfolio Analyst',
    role: 'Reporter',
    description: 'Holdings review and narrative report',
    accent: 'text-sage',
  },
  {
    glyph: '◇',
    name: 'Chart Specialist',
    role: 'Charter',
    description: 'Allocation and exposure visualizations',
    accent: 'text-violet',
  },
  {
    glyph: '△',
    name: 'Risk Manager',
    role: 'Risk',
    description: 'Concentration and diversification assessment',
    accent: 'text-coral',
  },
  {
    glyph: '◐',
    name: 'Retirement Planner',
    role: 'Retirement',
    description: 'Long-term readiness projections',
    accent: 'text-gold',
  },
];

export default function AdvisorTeam() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<AnalysisProgress>({
    stage: 'idle',
    message: '',
    activeAgents: []
  });
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const checkJobStatusLocal = async (jobId: string) => {
      try {
        const token = await getToken();
        const response = await fetch(`${API_URL}/api/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const job = await response.json();

          if (job.status === 'completed') {
            setProgress({
              stage: 'complete',
              message: 'Analysis complete!',
              activeAgents: []
            });

            if (pollInterval) {
              clearInterval(pollInterval);
              setPollInterval(null);
            }

            // Emit completion event so other components can refresh
            emitAnalysisCompleted(jobId);

            // Refresh the jobs list
            fetchJobs();

            setTimeout(() => {
              router.push(`/analysis?job_id=${jobId}`);
            }, 1500);
          } else if (job.status === 'failed') {
            setProgress({
              stage: 'error',
              message: 'Analysis failed',
              activeAgents: [],
              error: job.error || 'Analysis encountered an error'
            });

            if (pollInterval) {
              clearInterval(pollInterval);
              setPollInterval(null);
            }

            // Emit failure event
            emitAnalysisFailed(jobId, job.error);

            setIsAnalyzing(false);
            setCurrentJobId(null);
          }
        }
      } catch (error) {
        console.error('Error checking job status:', error);
      }
    };

    if (currentJobId && !pollInterval) {
      const interval = setInterval(() => {
        checkJobStatusLocal(currentJobId);
      }, 2000);
      setPollInterval(interval);
    }

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
        setPollInterval(null);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentJobId, pollInterval, router]);

  const fetchJobs = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/jobs`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setJobs(data.jobs || []);
      }
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const startAnalysis = async () => {
    setIsAnalyzing(true);
    setProgress({
      stage: 'starting',
      message: 'Initializing analysis...',
      activeAgents: []
    });

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          analysis_type: 'portfolio',
          options: {}
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentJobId(data.job_id);

        // Emit start event
        emitAnalysisStarted(data.job_id);

        setProgress({
          stage: 'planner',
          message: 'Financial Planner coordinating analysis...',
          activeAgents: ['Financial Planner']
        });

        setTimeout(() => {
          setProgress({
            stage: 'parallel',
            message: 'Agents working in parallel...',
            activeAgents: ['Portfolio Analyst', 'Chart Specialist', 'Risk Manager', 'Retirement Planner']
          });
        }, 5000);
      } else {
        throw new Error('Failed to start analysis');
      }
    } catch (error) {
      console.error('Error starting analysis:', error);
      setProgress({
        stage: 'error',
        message: 'Failed to start analysis',
        activeAgents: [],
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      setIsAnalyzing(false);
      setCurrentJobId(null);
    }
  };


  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-sage';
      case 'failed': return 'text-coral';
      case 'running': return 'text-gold';
      default: return 'text-muted';
    }
  };

  const isAgentActive = (agentName: string) => {
    return progress.activeAgents.includes(agentName);
  };

  return (
    <>
      <Head>
        <title>Advisor Team - Alex AI Financial Advisor</title>
      </Head>
      <Layout>
        <div className="max-w-6xl mx-auto">
          <PageHeader
            eyebrow="Agents"
            title="Advisory team"
            description="Specialized AI agents that run in parallel when you start an analysis."
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {agents.map((agent) => (
              <div
                key={agent.name}
                className={`panel p-6 relative overflow-hidden transition-all ${
                  isAgentActive(agent.name) ? 'animate-glow-pulse border-sage/40' : ''
                }`}
              >
                <span
                  className={`text-3xl font-display block mb-3 ${agent.accent} ${isAgentActive(agent.name) ? 'animate-strong-pulse' : ''}`}
                  aria-hidden
                >
                  {agent.glyph}
                </span>
                <h3 className={`font-display text-lg font-semibold ${agent.accent}`}>
                  {agent.name}
                </h3>
                <p className="text-xs text-gold uppercase tracking-wider mt-1 mb-2">{agent.role}</p>
                <p className="text-muted text-sm leading-relaxed">{agent.description}</p>
                {isAgentActive(agent.name) && (
                  <span className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-sage">
                    <span className="w-1.5 h-1.5 rounded-full bg-sage animate-pulse" />
                    Active
                  </span>
                )}
              </div>
            ))}
          </div>

          <div className="panel px-8 py-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
              <h2 className="font-display text-xl font-semibold text-ink">Analysis center</h2>
              <button
                type="button"
                onClick={startAnalysis}
                disabled={isAnalyzing}
                className="btn btn-primary"
              >
                {isAnalyzing ? 'Running...' : 'Start new analysis'}
              </button>
            </div>

            {isAnalyzing && (
              <div className="mb-8 p-6 panel-raised border-gold/20">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-ink">Progress</h3>
                  {progress.stage !== 'error' && progress.stage !== 'complete' && (
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-gold rounded-full animate-pulse" />
                      <div className="w-2 h-2 bg-gold rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
                      <div className="w-2 h-2 bg-gold rounded-full animate-pulse" style={{ animationDelay: '0.8s' }} />
                    </div>
                  )}
                </div>
                <p className={`text-sm mb-4 ${progress.stage === 'error' ? 'text-coral' : 'text-muted'}`}>
                  {progress.message}
                </p>
                {progress.stage === 'error' && progress.error && (
                  <div className="alert-error">
                    <p className="text-sm mb-3">{progress.error}</p>
                    <button
                      type="button"
                      onClick={() => {
                        setIsAnalyzing(false);
                        setCurrentJobId(null);
                        setProgress({ stage: 'idle', message: '', activeAgents: [] });
                      }}
                      className="btn btn-danger text-sm"
                    >
                      Try again
                    </button>
                  </div>
                )}
                {progress.stage !== 'idle' && progress.stage !== 'error' && (
                  <div className="w-full h-1.5 bg-surface-raised rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gold transition-all duration-1000"
                      style={{
                        width: progress.stage === 'starting' ? '10%' :
                               progress.stage === 'planner' ? '30%' :
                               progress.stage === 'parallel' ? '70%' :
                               progress.stage === 'completing' ? '90%' : '100%'
                      }}
                    />
                  </div>
                )}
              </div>
            )}

            <h3 className="label mb-4">Previous runs</h3>
            {jobs.length === 0 ? (
              <p className="text-muted text-sm italic">No analyses yet.</p>
            ) : (
              <div className="space-y-2">
                {jobs.slice(0, 5).map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-4 panel-raised hover:border-gold/20 transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink">Run #{job.id.slice(0, 8)}</p>
                      <p className="text-xs text-muted">{formatDate(job.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`text-sm font-medium ${getStatusColor(job.status)}`}>
                        {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                      </span>
                      {job.status === 'completed' && (
                        <button
                          type="button"
                          onClick={() => router.push(`/analysis?job_id=${job.id}`)}
                          className="btn btn-secondary text-sm py-2"
                        >
                          View
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Layout>
    </>
  );
}