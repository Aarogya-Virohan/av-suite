import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardPage from '../../app/(dashboard)/dashboard/page';
import { apiClient } from '../../lib/api-client';
import { useAuthStore } from '../../store';

vi.mock('../../components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock('../../lib/api-client', () => ({ apiClient: { get: vi.fn() } }));

const mockedGet = vi.mocked(apiClient.get);

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

describe('Dashboard analytics capability hydration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ capabilities: {} });
    mockedGet.mockResolvedValue({
      data: {
        meta: {
          period: 'month',
          start: '2026-09-01T00:00:00Z',
          end: '2026-10-01T00:00:00Z',
        },
        data: {
          patients: {
            total_patients: 1,
            active_patients: 1,
            new_patients_this_month: 0,
            new_patients_in_period: 0,
          },
          appointments: {
            today_appointments: 0,
            this_week_appointments: 0,
            appointments_in_period: 0,
            completed_appointments: 0,
            cancelled_appointments: 0,
            no_show_appointments: 0,
          },
          revenue: {
            billed_amount_in_period: '0.00',
            collected_amount_in_period: '0.00',
            outstanding_amount: '0.00',
            revenue_this_month: '0.00',
            revenue_in_period: '0.00',
            paid_invoices_count: 0,
            unpaid_invoices_count: 0,
            partial_invoices_count: 0,
            total_outstanding_amount: '0.00',
          },
          patient_revenue: [],
          patient_revenue_sort: 'collected_amount',
          leads: { total_leads: 0, leads_by_stage: {}, conversion_rate: 0 },
          booking: { pending_requests: 0, approved_requests: 0, rejected_requests: 0 },
        },
      },
    } as never);
  });

  afterEach(() => {
    cleanup();
  });

  it('waits for clinic-financial capability hydration, then requests the overview', async () => {
    renderDashboard();

    expect(mockedGet).not.toHaveBeenCalled();

    useAuthStore.setState({ capabilities: { 'analytics.clinic_financials': 'all' } });

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith('/analytics/overview', {
        params: {
          period: 'month',
          patient_revenue_sort: 'collected_amount',
          patient_revenue_limit: 5,
        },
      });
    });
    expect(await screen.findByText('1')).toBeTruthy();
  });
});
