import { useAuth } from "@clerk/nextjs";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import Layout from "../../components/Layout";
import ConfirmModal from "../../components/ConfirmModal";
import AddPositionModal from "../../components/AddPositionModal";
import { API_URL } from "../../lib/config";

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

export default function AccountDetail() {
  const { getToken } = useAuth();
  const router = useRouter();
  const { id } = router.query;
  const [account, setAccount] = useState<Account | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [editingAccount, setEditingAccount] = useState(false);
  const [editedAccount, setEditedAccount] = useState({ name: '', purpose: '', cash_balance: '' });
  const [editingPosition, setEditingPosition] = useState<string | null>(null);
  const [editedQuantity, setEditedQuantity] = useState('');
  const [showAddPosition, setShowAddPosition] = useState(false);
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    positionId: string;
    symbol: string;
  }>({ isOpen: false, positionId: '', symbol: '' });

  const loadAccount = useCallback(async () => {
    if (!id) return;

    try {
      const token = await getToken();

      // Load account details
      const accountResponse = await fetch(`${API_URL}/api/accounts`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (accountResponse.ok) {
        const accounts = await accountResponse.json();
        const foundAccount = accounts.find((acc: Account) => acc.id === id);

        if (foundAccount) {
          setAccount(foundAccount);
          setEditedAccount({
            name: foundAccount.account_name,
            purpose: foundAccount.account_purpose,
            cash_balance: Number(foundAccount.cash_balance).toLocaleString('en-US'),
          });
        } else {
          setMessage({ type: 'error', text: 'Account not found' });
          setTimeout(() => router.push('/accounts'), 2000);
          return;
        }
      }

      // Load positions
      const positionsResponse = await fetch(
        `${API_URL}/api/accounts/${id}/positions`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (positionsResponse.ok) {
        const data = await positionsResponse.json();
        setPositions(data.positions || []);
      }

    } catch (error) {
      console.error('Error loading account:', error);
      setMessage({ type: 'error', text: 'Failed to load account details' });
    } finally {
      setLoading(false);
    }
  }, [id, getToken, router]);

  useEffect(() => {
    loadAccount();
  }, [loadAccount]);

  const handleSaveAccount = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/accounts/${id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          account_name: editedAccount.name,
          account_purpose: editedAccount.purpose,
          cash_balance: parseFloat(editedAccount.cash_balance.replace(/,/g, '')),
        }),
      });

      if (response.ok) {
        const updatedAccount = await response.json();
        setAccount(updatedAccount);
        setEditingAccount(false);
        setMessage({ type: 'success', text: 'Account updated successfully' });
      } else {
        setMessage({ type: 'error', text: 'Failed to update account' });
      }
    } catch (error) {
      console.error('Error updating account:', error);
      setMessage({ type: 'error', text: 'Error updating account' });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdatePosition = async (positionId: string) => {
    const quantity = parseFloat(editedQuantity);
    if (isNaN(quantity) || quantity < 0) {
      setMessage({ type: 'error', text: 'Please enter a valid quantity' });
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/positions/${positionId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          quantity: quantity,
        }),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Position updated successfully' });
        setEditingPosition(null);
        await loadAccount();
      } else {
        setMessage({ type: 'error', text: 'Failed to update position' });
      }
    } catch (error) {
      console.error('Error updating position:', error);
      setMessage({ type: 'error', text: 'Error updating position' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePosition = async (positionId: string) => {
    setSaving(true);
    setMessage(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/positions/${positionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Position deleted successfully' });
        await loadAccount();
      } else {
        setMessage({ type: 'error', text: 'Failed to delete position' });
      }
    } catch (error) {
      console.error('Error deleting position:', error);
      setMessage({ type: 'error', text: 'Error deleting position' });
    } finally {
      setSaving(false);
    }
  };

  const formatCurrencyInput = (value: string) => {
    const cleaned = value.replace(/[^0-9.]/g, '');
    const parts = cleaned.split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return parts.join('.');
  };

  const calculatePositionsValue = () => {
    return positions.reduce((sum, position) => {
      return sum + (Number(position.quantity) * (position.current_price || 0));
    }, 0);
  };

  const calculateTotalValue = () => {
    return (account ? Number(account.cash_balance) : 0) + calculatePositionsValue();
  };

  if (loading) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="panel p-6">
            <p className="text-center text-muted">Loading account details...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!account) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="panel p-6">
            <p className="text-center text-red-600">Account not found</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <div className="mb-4">
          <button
            onClick={() => router.push('/accounts')}
            className="text-gold hover:text-blue-600 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Accounts
          </button>
        </div>

        {/* Account Details */}
        <div className="panel p-6 mb-6">
          <div className="flex justify-between items-start mb-6">
            <div className="flex-1">
              {editingAccount ? (
                <div className="space-y-4 max-w-md">
                  <div>
                    <label className="block text-sm font-medium text-muted mb-1">
                      Account Name
                    </label>
                    <input
                      type="text"
                      value={editedAccount.name}
                      onChange={(e) => setEditedAccount({ ...editedAccount, name: e.target.value })}
                      className="w-full field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-muted mb-1">
                      Account Purpose
                    </label>
                    <input
                      type="text"
                      value={editedAccount.purpose}
                      onChange={(e) => setEditedAccount({ ...editedAccount, purpose: e.target.value })}
                      className="w-full field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-muted mb-1">
                      Cash Balance
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted">$</span>
                      <input
                        type="text"
                        value={editedAccount.cash_balance}
                        onChange={(e) => setEditedAccount({ ...editedAccount, cash_balance: formatCurrencyInput(e.target.value) })}
                        className="w-full border border-gray-300 rounded-lg pl-8 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleSaveAccount}
                      disabled={saving}
                      className="btn btn-primary px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button
                      onClick={() => {
                        setEditingAccount(false);
                        setEditedAccount({
                          name: account.account_name,
                          purpose: account.account_purpose,
                          cash_balance: Number(account.cash_balance).toLocaleString('en-US'),
                        });
                      }}
                      className="bg-gray-200 hover:bg-gray-300 text-muted px-4 py-2 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <h2 className="text-2xl font-bold text-ink">{account.account_name}</h2>
                  <p className="text-muted mt-1">{account.account_purpose}</p>
                </>
              )}
            </div>
            {!editingAccount && (
              <button
                onClick={() => setEditingAccount(true)}
                className="text-gold hover:bg-primary/10 p-2 rounded transition-colors"
                title="Edit Account"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
            )}
          </div>

          {message && (
            <div className={`mb-4 p-4 rounded-lg ${
              message.type === 'success'
                ? 'alert-success'
                : 'alert-error'
            }`}>
              {message.text}
            </div>
          )}

          {/* Account Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 panel-raised rounded-lg">
            <div>
              <p className="text-sm text-muted">Cash Balance</p>
              <p className="text-lg font-semibold">
                ${Number(account.cash_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted">Positions Value</p>
              <p className="text-lg font-semibold">
                ${calculatePositionsValue().toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted">Total Value</p>
              <p className="text-lg font-semibold text-gold">
                ${calculateTotalValue().toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted">Positions</p>
              <p className="text-lg font-semibold">{positions.length}</p>
            </div>
          </div>
        </div>

        {/* Positions */}
        <div className="panel p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-ink">Positions</h3>
            <button
              onClick={() => setShowAddPosition(true)}
              className="btn btn-primary px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Position
            </button>
          </div>

          {positions.length === 0 ? (
            <div className="text-center py-8 panel-raised rounded-lg">
              <p className="text-muted">No positions in this account yet</p>
              <p className="text-sm text-muted mt-2">Click &ldquo;Add Position&rdquo; to start building your portfolio</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-semibold text-muted">Symbol</th>
                    <th className="text-right py-3 px-4 font-semibold text-muted">Quantity</th>
                    <th className="text-right py-3 px-4 font-semibold text-muted">Price</th>
                    <th className="text-right py-3 px-4 font-semibold text-muted">Value</th>
                    <th className="text-center py-3 px-4 font-semibold text-muted">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position) => (
                    <tr key={position.id} className="border-b border-border hover:bg-white/5 transition-colors">
                      <td className="py-4 px-4 font-medium">{position.symbol}</td>
                      <td className="py-4 px-4 text-right">
                        {editingPosition === position.id ? (
                          <input
                            type="number"
                            value={editedQuantity}
                            onChange={(e) => setEditedQuantity(e.target.value)}
                            className="w-24 border border-gray-300 rounded px-2 py-1 text-right focus:outline-none focus:ring-2 focus:ring-primary"
                            step="0.01"
                            min="0"
                          />
                        ) : (
                          Number(position.quantity).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                        )}
                      </td>
                      <td className="py-4 px-4 text-right">
                        ${position.current_price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'N/A'}
                      </td>
                      <td className="py-4 px-4 text-right font-semibold">
                        ${((position.current_price || 0) * Number(position.quantity)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex justify-center gap-2">
                          {editingPosition === position.id ? (
                            <>
                              <button
                                onClick={() => handleUpdatePosition(position.id)}
                                disabled={saving}
                                className="text-green-600 hover:bg-green-50 p-2 rounded transition-colors disabled:opacity-50"
                                title="Save"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              </button>
                              <button
                                onClick={() => {
                                  setEditingPosition(null);
                                  setEditedQuantity('');
                                }}
                                className="text-muted hover:bg-gray-100 p-2 rounded transition-colors"
                                title="Cancel"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => {
                                  setEditingPosition(position.id);
                                  // Format quantity to remove unnecessary decimal places
                                  const qty = Number(position.quantity);
                                  setEditedQuantity(qty % 1 === 0 ? qty.toString() : qty.toFixed(2));
                                }}
                                className="text-gold hover:bg-primary/10 p-2 rounded transition-colors"
                                title="Edit"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                              </button>
                              <button
                                onClick={() => setConfirmModal({
                                  isOpen: true,
                                  positionId: position.id,
                                  symbol: position.symbol
                                })}
                                disabled={saving}
                                className="text-red-600 hover:bg-red-50 p-2 rounded transition-colors disabled:opacity-50"
                                title="Delete"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <AddPositionModal
          isOpen={showAddPosition}
          accountId={typeof id === 'string' ? id : ''}
          accountName={account.account_name}
          getToken={getToken}
          onClose={() => setShowAddPosition(false)}
          onSuccess={async () => {
            setMessage({ type: 'success', text: 'Position added successfully' });
            await loadAccount();
          }}
        />

        {/* Delete Position Confirmation Modal */}
        <ConfirmModal
          isOpen={confirmModal.isOpen}
          title="Delete Position"
          message={
            <div>
              <p>Are you sure you want to delete your <span className="font-semibold">{confirmModal.symbol}</span> position?</p>
              <p className="text-sm mt-2 text-muted">This will remove this holding from your account.</p>
              <p className="text-sm mt-2 text-red-600 font-semibold">This action cannot be undone.</p>
            </div>
          }
          confirmText="Delete Position"
          cancelText="Cancel"
          confirmButtonClass="btn-danger"
          onConfirm={() => {
            handleDeletePosition(confirmModal.positionId);
            setConfirmModal({ isOpen: false, positionId: '', symbol: '' });
          }}
          onCancel={() => setConfirmModal({ isOpen: false, positionId: '', symbol: '' })}
          isProcessing={saving}
        />
      </div>
    </Layout>
  );
}