import React from 'react';
import { Database } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-white dark:bg-[#1C2541] border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
      <div className="p-4 rounded-full bg-slate-50 dark:bg-slate-900/30 text-slate-400 dark:text-slate-600 mb-4">
        {icon || <Database className="w-8 h-8" />}
      </div>
      <h3 className="text-sm font-bold text-[var(--foreground)]">{title}</h3>
      <p className="text-xs text-slate-400 dark:text-slate-500 max-w-sm mt-1 mb-4">
        {description}
      </p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-5 py-2 text-xs font-bold rounded-xl bg-[var(--navy)] text-white hover:opacity-95 shadow-sm transition-opacity"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
export default EmptyState;
