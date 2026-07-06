import { useEffect, useState } from 'react';
import { API_URL } from '../lib/config';

interface Instrument {
  symbol: string;
  name: string;
}

interface AddPositionModalProps {
  isOpen: boolean;
  accountId: string;
  accountName: string;
  getToken: () => Promise<string | null>;
  onClose: () => void;
  onSuccess: () => void;
}

export default function AddPositionModal({
  isOpen,
  accountId,
  accountName,
  getToken,
  onClose,
  onSuccess,
}: AddPositionModalProps) {
  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const loadInstruments = async () => {
      try {
        const token = await getToken();
        const response = await fetch(`${API_URL}/api/instruments`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          setInstruments(await response.json());
        }
      } catch {
        // Autocomplete still works with manual symbol entry
      }
    };

    loadInstruments();
  }, [isOpen, getToken]);

  const resetForm = () => {
    setSymbol('');
    setQuantity('');
    setSearchTerm('');
    setShowSuggestions(false);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    if (!symbol.trim() || !quantity.trim()) {
      setError('Please enter symbol and quantity');
      return;
    }

    const qty = parseFloat(quantity);
    if (Number.isNaN(qty) || qty <= 0) {
      setError('Please enter a valid quantity');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/positions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          account_id: accountId,
          symbol: symbol.toUpperCase(),
          quantity: qty,
        }),
      });

      if (response.ok) {
        resetForm();
        onSuccess();
        onClose();
      } else {
        const data = await response.json().catch(() => ({}));
        setError(typeof data.detail === 'string' ? data.detail : 'Failed to add position');
      }
    } catch {
      setError('Error adding position');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const filteredInstruments = instruments
    .filter(
      (inst) =>
        inst.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inst.name.toLowerCase().includes(searchTerm.toLowerCase()),
    )
    .slice(0, 5);

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="panel max-w-md w-full p-6">
        <h3 className="font-display text-xl font-semibold text-ink mb-1">Add holding</h3>
        <p className="text-sm text-muted mb-4">{accountName}</p>

        <div className="space-y-4">
          <div>
            <label className="label">Symbol *</label>
            <div className="relative">
              <input
                type="text"
                value={searchTerm || symbol}
                onChange={(e) => {
                  const value = e.target.value.toUpperCase();
                  setSearchTerm(value);
                  setSymbol(value);
                  setShowSuggestions(value.length > 0);
                }}
                onFocus={() => setShowSuggestions(searchTerm.length > 0)}
                className="field uppercase"
                placeholder="e.g., SPY, GOOGL"
              />
              {showSuggestions && filteredInstruments.length > 0 && (
                <div className="absolute z-10 w-full mt-1 panel border border-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {filteredInstruments.map((inst) => (
                    <button
                      key={inst.symbol}
                      type="button"
                      onClick={() => {
                        setSymbol(inst.symbol);
                        setSearchTerm('');
                        setShowSuggestions(false);
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-white/5 border-b border-border last:border-b-0"
                    >
                      <div className="font-medium">{inst.symbol}</div>
                      <div className="text-xs text-muted">{inst.name}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <p className="text-xs text-muted mt-1">
              Unknown symbols are added automatically. Adding more of an existing holding increases the quantity.
            </p>
          </div>

          <div>
            <label className="label">Quantity *</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="field"
              placeholder="0"
              step="0.01"
              min="0"
            />
          </div>
        </div>

        {error && <div className="mt-4 alert-error text-sm">{error}</div>}

        <div className="flex gap-3 mt-6">
          <button type="button" onClick={handleSubmit} disabled={saving} className="btn btn-primary flex-1">
            {saving ? 'Adding...' : 'Add holding'}
          </button>
          <button type="button" onClick={handleClose} className="btn btn-secondary flex-1">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
