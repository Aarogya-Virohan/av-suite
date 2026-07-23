import React from 'react';

export const LoadingSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div className="w-full space-y-3 animate-pulse p-4">
      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded-lg w-1/4 mb-4" />
      {Array.from({ length: rows }).map((_, idx) => (
        <div key={idx} className="flex space-x-4">
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg flex-1" />
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg w-24" />
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg w-16" />
        </div>
      ))}
    </div>
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-3 bg-white dark:bg-[#1C2541] animate-pulse">
      <div className="flex justify-between items-center">
        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded-lg w-1/3" />
        <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded-full w-12" />
      </div>
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-lg w-1/2" />
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-lg w-3/4" />
    </div>
  );
};
export default LoadingSkeleton;
