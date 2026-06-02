import { useAuth } from "@clerk/nextjs";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import Layout from "../components/Layout";
import PageHeader from "../components/PageHeader";
import ConfirmModal from "../components/ConfirmModal";
import { API_URL } from "../lib/config";
import { SkeletonTable } from "../components/Skeleton";
import Head from "next/head";

interface Position {
  id: string;
  symbol: string;
  quantity: number;
  current_price?: number;
}

interface Account {
  id: string;
  account_name: string;
  account_purpose: string;
  cash_balance: number;
  positions?: Position[];
}

interface TestScenarioOption {
  id: string;
  name: string;
  description: string;
}

const FALLBACK_SCENARIOS: TestScenarioOption[] = [
  { id: 'balanced', name: 'Balanced retirement', description: 'Three-account mix (~$90k), mid-career goals.' },
  { id: 'conservative', name: 'Conservative', description: 'Bond-heavy portfolio, shorter horizon.' },
  { id: 'aggressive_growth', name: 'Aggressive growth', description: 'Equity-tilted ETFs, long horizon.' },
  { id: 'near_retirement', name: 'Near retirement', description: 'Income-focused (~$175k), 5 years out.' },
  { id: 'simple_starter', name: 'Simple starter', description: 'One account, SPY + BND (~$28k).' },
  { id: 'tech_stocks', name: 'Tech stocks + ETFs', description: 'Mega-cap tech concentration demo.' },
  { id: 'legacy_simple', name: 'Basic 401(k) demo', description: 'Single 401(k) with five ETFs.' },
];

export default function Accounts() {
  const { getToken } = useAuth();
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [populatingData, setPopulatingData] = useState(false);
  const [testScenarios, setTestScenarios] = useState<TestScenarioOption[]>([]);
  const [selectedScenario, setSelectedScenario] = useState('balanced');
  const [resettingAccounts, setResettingAccounts] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newAccount, setNewAccount] = useState({ name: '', purpose: '', cash_balance: '' });
  const [savingAccount, setSavingAccount] = useState(false);
  const [deletingAccountId, setDeletingAccountId] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'reset' | 'delete' | 'switch_demo';
    accountId?: string;
    accountName?: string;
  }>({ isOpen: false, type: 'reset' });

  const scenarioOptions = testScenarios.length > 0 ? testScenarios : FALLBACK_SCENARIOS;
  const selectedScenarioMeta = scenarioOptions.find((s) => s.id === selectedScenario);

  const loadAccounts = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/accounts`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Accounts received from API:', data);
        // For each account, load positions
        const accountsWithPositions = await Promise.all(
          data.map(async (account: Account) => {
            console.log('Processing account:', account.id, account.account_name);
            // Skip if account has no ID
            if (!account.id) {
              console.warn('Account missing ID:', account);
              return { ...account, positions: [] };
            }

            try {
              const positionsResponse = await fetch(
                `${API_URL}/api/accounts/${account.id}/positions`,
                {
                  headers: {
                    'Authorization': `Bearer ${token}`,
                  },
                }
              );
              if (positionsResponse.ok) {
                const data = await positionsResponse.json();
                const positions = data.positions || [];
                console.log(`Loaded ${positions.length} positions for account ${account.id}`);
                return { ...account, positions };
              }
            } catch (err) {
              console.error(`Error loading positions for account ${account.id}:`, err);
            }
            return { ...account, positions: [] };
          })
        );
        console.log('Final accounts with positions:', accountsWithPositions);
        setAccounts(accountsWithPositions);
      }
    } catch (error) {
      console.error('Error loading accounts:', error);
      setMessage({ type: 'error', text: 'Failed to load accounts' });
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  useEffect(() => {
    const loadScenarios = async () => {
      try {
        const response = await fetch(`${API_URL}/api/test-data-scenarios`);
        if (response.ok) {
          const data = await response.json();
          setTestScenarios(data.scenarios || []);
          if (data.default) {
            setSelectedScenario(data.default);
          }
        }
      } catch (error) {
        console.error('Error loading test scenarios:', error);
      }
    };
    loadScenarios();
  }, []);

  // Listen for analysis completion events to refresh data
  useEffect(() => {
    const handleAnalysisCompleted = () => {
      // Refresh accounts to get updated prices after analysis
      console.log('Analysis completed - refreshing accounts...');
      loadAccounts();
    };

    // Listen for the completion event
    window.addEventListener('analysis:completed', handleAnalysisCompleted);

    return () => {
      window.removeEventListener('analysis:completed', handleAnalysisCompleted);
    };
  }, [loadAccounts]);

  const populateTestData = async () => {
    setPopulatingData(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/populate-test-data`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ scenario: selectedScenario }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: data.message || 'Test data loaded' });
        await loadAccounts();
      } else {
        const err = await response.json().catch(() => ({}));
        setMessage({
          type: 'error',
          text: typeof err.detail === 'string' ? err.detail : 'Failed to load demo portfolio',
        });
      }
    } catch (error) {
      console.error('Error populating test data:', error);
      setMessage({ type: 'error', text: 'Error populating test data' });
    } finally {
      setPopulatingData(false);
    }
  };

  const resetAccounts = async (): Promise<boolean> => {
    setResettingAccounts(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/reset-accounts`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: data.message });
        setAccounts([]);
        await loadAccounts();
        return true;
      }
      setMessage({ type: 'error', text: 'Failed to reset accounts' });
      return false;
    } catch (error) {
      console.error('Error resetting accounts:', error);
      setMessage({ type: 'error', text: 'Error resetting accounts' });
      return false;
    } finally {
      setResettingAccounts(false);
    }
  };

  const calculateAccountTotal = (account: Account) => {
    const positionsValue = account.positions?.reduce((sum, position) => {
      const value = Number(position.quantity) * (Number(position.current_price) || 0);
      return sum + value;
    }, 0) || 0;
    return Number(account.cash_balance) + positionsValue;
  };

  const calculatePortfolioTotal = () => {
    return accounts.reduce((sum, account) => sum + calculateAccountTotal(account), 0);
  };

  const handleAddAccount = async () => {
    if (!newAccount.name.trim()) {
      setMessage({ type: 'error', text: 'Please enter an account name' });
      return;
    }

    setSavingAccount(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/accounts`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          account_name: newAccount.name,
          account_purpose: newAccount.purpose || 'Investment Account',
          cash_balance: parseFloat(newAccount.cash_balance.replace(/,/g, '')) || 0,
        }),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Account created successfully' });
        setShowAddModal(false);
        setNewAccount({ name: '', purpose: '', cash_balance: '' });
        await loadAccounts();
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to create account' });
      }
    } catch (error) {
      console.error('Error creating account:', error);
      setMessage({ type: 'error', text: 'Error creating account' });
    } finally {
      setSavingAccount(false);
    }
  };

  const handleDeleteAccount = async (accountId: string) => {
    setDeletingAccountId(accountId);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/accounts/${accountId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Account deleted successfully' });
        await loadAccounts();
      } else {
        setMessage({ type: 'error', text: 'Failed to delete account' });
      }
    } catch (error) {
      console.error('Error deleting account:', error);
      setMessage({ type: 'error', text: 'Error deleting account' });
    } finally {
      setDeletingAccountId(null);
    }
  };

  const switchDemoPortfolio = async () => {
    const cleared = await resetAccounts();
    if (cleared) {
      await populateTestData();
    }
  };

  const renderDemoPortfolioPicker = (variant: 'empty' | 'compact' = 'empty') => (
    <div
      className={
        variant === 'empty'
          ? 'panel-raised p-6 border border-gold/30'
          : 'panel-raised p-4 mb-6 border border-border'
      }
    >
      <p className="label mb-1">Demo portfolio</p>
      <p className="text-sm text-muted mb-4">
        {variant === 'empty'
          ? 'Load sample accounts and positions to try analysis without entering data manually.'
          : 'Replace your current accounts with a different sample portfolio.'}
      </p>
      <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
        <div className="flex-1 min-w-0">
          <label htmlFor="demo-scenario" className="label sr-only">
            Scenario
          </label>
          <select
            id="demo-scenario"
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            className="field w-full"
          >
            {scenarioOptions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={
            variant === 'empty'
              ? populateTestData
              : () => setConfirmModal({ isOpen: true, type: 'switch_demo' })
          }
          disabled={populatingData || resettingAccounts}
          className="btn btn-secondary shrink-0"
        >
          {populatingData
            ? 'Loading...'
            : variant === 'empty'
              ? 'Load demo'
              : 'Switch demo'}
        </button>
      </div>
      {selectedScenarioMeta?.description && (
        <p className="text-xs text-muted mt-3">{selectedScenarioMeta.description}</p>
      )}
    </div>
  );

  const formatCurrencyInput = (value: string) => {
    // Remove non-numeric characters except decimal
    const cleaned = value.replace(/[^0-9.]/g, '');
    // Format with commas
    const parts = cleaned.split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return parts.join('.');
  };

  return (
    <>
      <Head>
        <title>Accounts - Alex AI Financial Advisor</title>
      </Head>
      <Layout>
      <div className="max-w-6xl mx-auto">
        <PageHeader
          eyebrow="Holdings"
          title="Accounts"
          description="Manage investment accounts and positions."
          action={
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setShowAddModal(true)}
                className="btn btn-primary flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add account
              </button>
              {accounts.length > 0 && (
                <button
                  type="button"
                  onClick={() => setConfirmModal({ isOpen: true, type: 'reset' })}
                  disabled={resettingAccounts}
                  className="btn btn-secondary"
                >
                  {resettingAccounts ? 'Resetting...' : 'Reset all'}
                </button>
              )}
            </div>
          }
        />

        <div className="panel p-6 mb-6">
          {message && (
            <div className={`mb-4 ${message.type === 'success' ? 'alert-success' : 'alert-error'}`}>
              {message.text}
            </div>
          )}

          {loading ? (
            <SkeletonTable rows={3} />
          ) : accounts.length === 0 ? (
            <div className="space-y-6">
              <div className="alert-info text-center">
                <p className="font-semibold mb-2 text-gold">No accounts yet</p>
                <p className="text-sm text-muted">
                  Load a demo portfolio below, or use &quot;Add account&quot; to build your own.
                </p>
              </div>
              {renderDemoPortfolioPicker('empty')}
            </div>
          ) : (
            <>
              {renderDemoPortfolioPicker('compact')}
              {/* Portfolio Summary */}
              <div className="panel-raised p-4 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="label">Total value</p>
                    <p className="stat-value text-xl">
                      ${calculatePortfolioTotal().toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                  </div>
                  <div>
                    <p className="label">Accounts</p>
                    <p className="stat-value text-xl text-ink">{accounts.length}</p>
                  </div>
                  <div>
                    <p className="label">Positions</p>
                    <p className="stat-value text-xl text-ink">
                      {accounts.reduce((sum, acc) => sum + (acc.positions?.length || 0), 0)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Accounts Table */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-muted">Account</th>
                      <th className="text-left py-3 px-4 text-xs uppercase tracking-wider text-muted hidden md:table-cell">Type</th>
                      <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-muted">Positions</th>
                      <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-muted">Cash</th>
                      <th className="text-right py-3 px-4 text-xs uppercase tracking-wider text-muted">Total</th>
                      <th className="text-center py-3 px-4 text-xs uppercase tracking-wider text-muted">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((account) => {
                      const positionsValue = calculateAccountTotal(account) - Number(account.cash_balance);
                      return (
                        <tr key={account.id} className="border-b border-border hover:bg-white/5 transition-colors">
                          <td className="py-4 px-4">
                            <div>
                              <p className="font-semibold text-ink">{account.account_name}</p>
                              <p className="text-xs text-muted md:hidden">{account.account_purpose}</p>
                            </div>
                          </td>
                          <td className="py-4 px-4 hidden md:table-cell">
                            <span className="text-sm text-muted">{account.account_purpose}</span>
                          </td>
                          <td className="py-4 px-4 text-right">
                            <div>
                              <p className="font-medium">{account.positions?.length || 0}</p>
                              {positionsValue > 0 && (
                                <p className="text-xs text-muted">
                                  ${positionsValue.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                </p>
                              )}
                            </div>
                          </td>
                          <td className="py-4 px-4 text-right">
                            ${Number(account.cash_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="py-4 px-4 text-right">
                            <p className="font-semibold text-gold">
                              ${calculateAccountTotal(account).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </p>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex justify-center gap-2">
                              <button
                                onClick={() => router.push(`/accounts/${account.id}`)}
                                className="text-gold hover:bg-gold-dim p-2 rounded-lg transition-colors"
                                title="View/Edit"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                              </button>
                              <button
                                onClick={() => setConfirmModal({
                                  isOpen: true,
                                  type: 'delete',
                                  accountId: account.id,
                                  accountName: account.account_name
                                })}
                                disabled={deletingAccountId === account.id}
                                className="text-coral hover:bg-coral-dim p-2 rounded-lg transition-colors disabled:opacity-50"
                                title="Delete"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Add Account Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="panel max-w-md w-full p-6">
              <h3 className="font-display text-xl font-semibold text-ink mb-4">Add account</h3>

              <div className="space-y-4">
                <div>
                  <label className="label">Account name *</label>
                  <input
                    type="text"
                    value={newAccount.name}
                    onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
                    className="field"
                    placeholder="e.g., 401k, Roth IRA, Brokerage"
                  />
                </div>

                <div>
                  <label className="label">Purpose</label>
                  <input
                    type="text"
                    value={newAccount.purpose}
                    onChange={(e) => setNewAccount({ ...newAccount, purpose: e.target.value })}
                    className="field"
                    placeholder="e.g., Long-term Growth, Retirement"
                  />
                </div>

                <div>
                  <label className="label">Initial cash</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted">$</span>
                    <input
                      type="text"
                      value={newAccount.cash_balance}
                      onChange={(e) => setNewAccount({ ...newAccount, cash_balance: formatCurrencyInput(e.target.value) })}
                      className="field pl-8"
                      placeholder="0.00"
                    />
                  </div>
                </div>
              </div>

              {message && message.type === 'error' && (
                <div className="mt-4 alert-error text-sm">
                  {message.text}
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button type="button" onClick={handleAddAccount} disabled={savingAccount} className="btn btn-primary flex-1">
                  {savingAccount ? 'Creating...' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setNewAccount({ name: '', purpose: '', cash_balance: '' });
                    setMessage(null);
                  }}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Confirmation Modal */}
        <ConfirmModal
          isOpen={confirmModal.isOpen}
          title={
            confirmModal.type === 'reset'
              ? 'Reset All Accounts'
              : confirmModal.type === 'switch_demo'
                ? 'Switch Demo Portfolio'
                : 'Delete Account'
          }
          message={
            confirmModal.type === 'switch_demo' ? (
              <div>
                <p className="font-semibold mb-2">
                  Replace all accounts with &ldquo;{selectedScenarioMeta?.name || selectedScenario}&rdquo;?
                </p>
                <p className="text-sm text-muted">{selectedScenarioMeta?.description}</p>
                <p className="text-sm mt-3 text-red-600 font-semibold">
                  Your current accounts and positions will be deleted first.
                </p>
              </div>
            ) : confirmModal.type === 'reset' ? (
              <div>
                <p className="font-semibold mb-2">Are you sure you want to delete all your accounts?</p>
                <p className="text-sm">This will permanently remove:</p>
                <ul className="list-disc list-inside text-sm mt-1 ml-2">
                  <li>All {accounts.length} account{accounts.length !== 1 ? 's' : ''}</li>
                  <li>All positions in those accounts</li>
                  <li>All transaction history</li>
                </ul>
                <p className="text-sm mt-3 text-red-600 font-semibold">This action cannot be undone.</p>
              </div>
            ) : (
              <div>
                <p>Are you sure you want to delete <span className="font-semibold">&ldquo;{confirmModal.accountName}&rdquo;</span>?</p>
                <p className="text-sm mt-2">This will also delete all positions in this account.</p>
                <p className="text-sm mt-2 text-red-600 font-semibold">This action cannot be undone.</p>
              </div>
            )
          }
          confirmText={
            confirmModal.type === 'reset'
              ? 'Delete All Accounts'
              : confirmModal.type === 'switch_demo'
                ? 'Switch Demo'
                : 'Delete Account'
          }
          cancelText="Cancel"
          confirmButtonClass="btn-danger"
          onConfirm={() => {
            if (confirmModal.type === 'reset') {
              resetAccounts();
            } else if (confirmModal.type === 'switch_demo') {
              switchDemoPortfolio();
            } else if (confirmModal.accountId) {
              handleDeleteAccount(confirmModal.accountId);
            }
            setConfirmModal({ isOpen: false, type: 'reset' });
          }}
          onCancel={() => setConfirmModal({ isOpen: false, type: 'reset' })}
          isProcessing={resettingAccounts || populatingData || deletingAccountId !== null}
        />
      </div>
      </Layout>
    </>
  );
}