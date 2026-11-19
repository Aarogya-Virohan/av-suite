'use client';

import React, { useState, useEffect } from 'react';
import { Search, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  searchField?: (item: T) => string;
  searchPlaceholder?: string;
  isLoading?: boolean;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
  // Server-side pagination support
  totalItems?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  // Server-side search support
  onSearchChange?: (term: string) => void;
}

const PAGE_SIZES = [5, 10, 25, 50, 75] as const;

export function DataTable<T extends { id: string }>({
  columns,
  data,
  searchField,
  searchPlaceholder = 'Search...',
  isLoading = false,
  emptyMessage = 'No records found.',
  onRowClick,
  totalItems,
  currentPage: serverPage,
  pageSize: serverPageSize = 10,
  onPageChange,
  onPageSizeChange,
  onSearchChange,
}: DataTableProps<T>) {
  const [searchTerm, setSearchTerm] = useState('');
  const [clientPage, setClientPage] = useState(1);
  const [clientPageSize, setClientPageSize] = useState(10);

  // Debounce logic for server-side search
  useEffect(() => {
    if (onSearchChange) {
      const handler = setTimeout(() => {
        onSearchChange(searchTerm);
      }, 400); // 400ms debounce
      return () => clearTimeout(handler);
    }
  }, [searchTerm, onSearchChange]);
  
  const isServerSide = totalItems !== undefined && onPageChange !== undefined;
  const currentPage = isServerSide ? (serverPage || 1) : clientPage;
  const pageSize = isServerSide ? serverPageSize : clientPageSize;
  // Rows per page (founder feedback C-27). Server-side tables show it only
  // when the page passes onPageSizeChange.
  const canChangePageSize = !isServerSide || !!onPageSizeChange;
  const handlePageSizeChange = (size: number) => {
    if (isServerSide) {
      onPageSizeChange?.(size);
      onPageChange?.(1);
    } else {
      setClientPageSize(size);
      setClientPage(1);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (isServerSide && onPageChange) {
      onPageChange(newPage);
    } else {
      setClientPage(newPage);
    }
  };

  const filteredData = isServerSide ? data : data.filter((item) => {
    if (!searchTerm || !searchField) return true;
    return searchField(item).toLowerCase().includes(searchTerm.toLowerCase());
  });

  const totalPages = isServerSide 
    ? Math.ceil(totalItems / pageSize) || 1
    : Math.ceil(filteredData.length / pageSize) || 1;
    
  const paginatedData = isServerSide 
    ? data 
    : filteredData.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="space-y-4">
      {/* Search Header */}
      {(searchField || onSearchChange) && (
        <div className="flex items-center justify-between gap-4">
          <div className="relative max-w-xs w-full">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                handlePageChange(1);
              }}
              placeholder={searchPlaceholder}
              className="h-10 w-full rounded-[10px] border border-line bg-card pl-9 pr-4 text-sm text-ink placeholder:text-slate-400 transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15 dark:border-slate-800 dark:bg-slate-900 dark:text-white"
            />
          </div>
          <span className="text-xs font-medium text-muted">
            Showing {isServerSide ? totalItems : filteredData.length} entries
          </span>
        </div>
      )}

      {/* Table Container */}
      <div className="overflow-hidden rounded-2xl border border-line bg-card shadow-card dark:border-slate-800 dark:bg-slate-900">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-line bg-canvas/60 dark:border-slate-800 dark:bg-slate-950">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted dark:text-slate-400"
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft text-sm dark:divide-slate-800">
              {isLoading ? (
                <tr>
                  <td colSpan={columns.length} className="px-5 py-10 text-center text-muted">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin text-grove" />
                      <span>Loading records...</span>
                    </div>
                  </td>
                </tr>
              ) : paginatedData.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="px-5 py-10 text-center text-muted">
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                paginatedData.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => onRowClick && onRowClick(item)}
                    // Only rows that open something get a hover state, so read-only
                    // tables do not look clickable (C-03).
                    className={
                      onRowClick ? 'cursor-pointer transition-colors hover:bg-canvas/70 dark:hover:bg-slate-800/50' : undefined
                    }
                  >
                    {columns.map((col) => (
                      <td key={col.key} className="px-5 py-3.5 text-ink-2 dark:text-slate-200">
                        {col.render
                          ? col.render(item)
                          : (item as Record<string, unknown>)[col.key] != null
                          ? String((item as Record<string, unknown>)[col.key])
                          : '-'}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="flex items-center justify-between border-t border-line px-5 py-3 text-xs dark:border-slate-800 dark:bg-slate-950/50">
          <div className="flex items-center gap-4">
            <span className="text-muted">
              Page {currentPage} of {totalPages}
            </span>
            {canChangePageSize && (
              <label className="flex items-center gap-1.5 text-muted">
                <span>Rows per page</span>
                <select
                  value={pageSize}
                  onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                  className="h-8 cursor-pointer rounded-lg border border-line bg-card px-2 text-xs font-semibold text-ink-2 transition-colors hover:border-slate-300 focus:border-grove focus:outline-none dark:border-slate-700 dark:bg-slate-800"
                >
                  {PAGE_SIZES.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              aria-label="Previous page"
              className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg border border-line bg-card text-ink-2 transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              aria-label="Next page"
              className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg border border-line bg-card text-ink-2 transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
