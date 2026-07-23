import React from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = 'Failed to sync clinical records. Check network or server status.',
  onRetry
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-red-500/5 border border-red-500/20 rounded-2xl">
      <div className="p-3.5 rounded-full bg-red-500/10 text-red-500 mb-3 animate-pulse">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-xs font-bold text-red-500 uppercase tracking-wider">Sync Connection Failed</h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 px-4 py-2 text-xs font-bold rounded-lg border border-red-500/20 text-red-500 hover:bg-red-500/10 transition-colors inline-flex items-center gap-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Retry Connection
        </button>
      )}
    </div>
  );
};
export default ErrorState;
