import { useEffect, useState } from 'react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
  duration?: number;
}

interface ToastProps {
  toast: ToastMessage;
  onClose: (id: string) => void;
}

const Toast = ({ toast, onClose }: ToastProps) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose(toast.id);
    }, toast.duration || 3000);

    return () => clearTimeout(timer);
  }, [toast, onClose]);

  const styles = {
    success: 'border-sage/40 bg-surface text-sage',
    error: 'border-coral/40 bg-surface text-coral',
    info: 'border-gold/40 bg-surface text-gold',
  }[toast.type];

  return (
    <div className={`panel px-4 py-3 flex items-center gap-3 animate-slide-in border ${styles}`}>
      <p className="flex-1 text-sm text-ink">{toast.message}</p>
      <button
        type="button"
        onClick={() => onClose(toast.id)}
        className="btn-ghost text-muted hover:text-ink"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
};

export const ToastContainer = () => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const handleToast = (event: CustomEvent<Omit<ToastMessage, 'id'>>) => {
      const newToast: ToastMessage = {
        ...event.detail,
        id: Date.now().toString()
      };
      setToasts(prev => [...prev, newToast]);
    };

    window.addEventListener('toast', handleToast as EventListener);
    return () => window.removeEventListener('toast', handleToast as EventListener);
  }, []);

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[100] space-y-2 max-w-sm">
      {toasts.map(toast => (
        <Toast key={toast.id} toast={toast} onClose={removeToast} />
      ))}
    </div>
  );
};

export const showToast = (type: 'success' | 'error' | 'info', message: string, duration?: number) => {
  window.dispatchEvent(new CustomEvent('toast', {
    detail: { type, message, duration }
  }));
};
