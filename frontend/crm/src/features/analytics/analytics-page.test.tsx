import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AnalyticsPage from '../../app/(dashboard)/analytics/page';
import { apiClient } from '../../lib/api-client';
import { canAccessModule, hasCapability } from '../../config/permissions';
import { analyticsKeys } from './api';
import type {
  AnalyticsOverviewEnvelope,
  TherapistPerformanceEnvelope,
} from '../../types/api';

vi.mock('../../components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock('../../components/ui/AccessRestricted', () => ({
  AccessRestricted: ({ message }: { message: string }) => <div>{message}</div>,
}));
vi.mock('../../config/permissions', () => ({
  canAccessModule: vi.fn(() => true),
  hasCapability: vi.fn(() => true),
}));
vi.mock('../../lib/api-client', () => ({ apiClient: { get: vi.fn() } }));

const overviewEnvelope: AnalyticsOverviewEnvelope = {
  meta: {
    period: 'month',
    start: '2026-09-01T00:00:00Z',
    end: '2026-10-01T00:00:00Z',
  },
  data: {
    patients: {
      total_patients: 12,
      active_patients: 10,
      new_patients_this_month: 2,
      new_patients_in_period: 2,
    },
    appointments: {
      today_appointments: 3,
      this_week_appointments: 8,
      appointments_in_period: 22,
      completed_appointments: 15,
      cancelled_appointments: 2,
      no_show_appointments: 1,
    },
    revenue: {
      billed_amount_in_period: '1250.50',
      collected_amount_in_period: '987.65',
      outstanding_amount: '4321.09',
      revenue_this_month: 'legacy-not-used',
      revenue_in_period: 'legacy-not-used',
      paid_invoices_count: 3,
      unpaid_invoices_count: 2,
      partial_invoices_count: 1,
      total_outstanding_amount: '4321.09',
    },
    patient_revenue: [
      {
        patient_id: 'patient-2',
        patient_name: 'Zara Patient',
        billed_amount: '800.00',
        collected_amount: '1200.00',
      },
      {
        patient_id: 'patient-1',
        patient_name: 'Asha Patient',
        billed_amount: '1250.50',
        collected_amount: '987.65',
      },
    ],
    patient_revenue_sort: 'collected_amount',
    leads: { total_leads: 4, leads_by_stage: {}, conversion_rate: 25 },
    booking: { pending_requests: 0, approved_requests: 0, rejected_requests: 0 },
  },
};

const performanceEnvelope: TherapistPerformanceEnvelope = {
  meta: {
    period: 'month',
    start: '2026-09-01T00:00:00Z',
    end: '2026-10-01T00:00:00Z',
  },
  data: {
    today_appointments: 1,
    appointments_in_period: 6,
    completed_appointments_this_month: 4,
    completed_appointments_in_period: 4,
    cancelled_appointments_this_month: 1,
    cancelled_appointments_in_period: 1,
    treatment_sessions_this_month: 3,
    treatment_sessions_in_period: 3,
    soap_notes_this_month: 2,
    soap_notes_in_period: 2,
    patients_seen_this_month: 2,
    patients_seen_in_period: 2,
  },
};

const mockedGet = vi.mocked(apiClient.get);
const mockedCanAccessModule = vi.mocked(canAccessModule);
const mockedHasCapability = vi.mocked(hasCapability);

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AnalyticsPage />
    </QueryClientProvider>,
  );
}

function allowClinicAnalytics() {
  mockedCanAccessModule.mockReturnValue(true);
  mockedHasCapability.mockImplementation((capability) => capability === 'analytics.clinic_financials');
}

describe('AnalyticsPage API integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    allowClinicAnalytics();
    mockedGet.mockResolvedValue({ data: overviewEnvelope } as never);
  });

  afterEach(() => {
    cleanup();
  });

  it('defaults to month and requests the month overview', async () => {
    renderPage();

    expect((await screen.findAllByText('₹1,250.50')).length).toBeGreaterThan(0);
    expect(mockedGet).toHaveBeenCalledWith('/analytics/overview', {
      params: {
        period: 'month',
        patient_revenue_sort: 'collected_amount',
        patient_revenue_limit: 5,
      },
    });
    expect(screen.getByRole('button', { name: 'month' }).getAttribute('aria-pressed')).toBe('true');
  });

  it.each(['today', 'week', 'month', 'year'] as const)(
    'requests the selected %s period', async (period) => {
      renderPage();
      await screen.findAllByText('₹1,250.50');

      fireEvent.click(screen.getByRole('button', { name: period }));

      await waitFor(() => {
        expect(mockedGet).toHaveBeenCalledWith('/analytics/overview', {
          params: {
            period,
            patient_revenue_sort: 'collected_amount',
            patient_revenue_limit: 5,
          },
        });
      });
      expect(screen.getByRole('button', { name: period }).getAttribute('aria-pressed')).toBe('true');
    },
  );

  it('keeps period and patient ranking in the cache key and sends the chosen sort', async () => {
    expect(analyticsKeys.overview('today')).not.toEqual(analyticsKeys.overview('week'));
    expect(analyticsKeys.myPerformance('month')).not.toEqual(analyticsKeys.myPerformance('year'));

    renderPage();
    await screen.findByText('Asha Patient');
    fireEvent.change(screen.getByRole('combobox', { name: 'Rank patients by' }), {
      target: { value: 'billed_amount' },
    });

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith('/analytics/overview', {
        params: {
          period: 'month',
          patient_revenue_sort: 'billed_amount',
          patient_revenue_limit: 5,
        },
      });
    });
  });

  it('displays canonical financial fields and backend-ranked patient amounts', async () => {
    renderPage();

    expect((await screen.findAllByText('₹1,250.50')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('₹987.65').length).toBeGreaterThan(0);
    expect(screen.getAllByText('₹4,321.09').length).toBeGreaterThan(0);
    const patientNames = screen.getAllByText(/(?:Asha|Zara) Patient/).map((node) => node.textContent);
    expect(patientNames).toEqual(['Zara Patient', 'Asha Patient']);
    expect(screen.queryByText(/Revenue pending/i)).toBeNull();
  });

  it('shows an honest empty state when there is no patient revenue', async () => {
    mockedGet.mockResolvedValue({
      data: { ...overviewEnvelope, data: { ...overviewEnvelope.data!, patient_revenue: [] } },
    } as never);
    renderPage();

    expect(await screen.findByText('No patient financial activity for this period.')).toBeTruthy();
  });

  it('shows loading and error states without presenting a prior period as current', async () => {
    let resolveRequest: ((value: unknown) => void) | undefined;
    mockedGet.mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve; }) as never);
    renderPage();

    expect(await screen.findByRole('status')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'today' }));
    expect(await screen.findByText('Loading analytics for today...')).toBeTruthy();
    expect(screen.queryByText('₹1,250.50')).toBeNull();
    resolveRequest?.({ data: overviewEnvelope });

    cleanup();
    mockedGet.mockRejectedValueOnce(new Error('request failed'));
    renderPage();
    expect(await screen.findByRole('alert')).toBeTruthy();
  });

  it('requests selected-period personal performance only for the authenticated-user view', async () => {
    mockedHasCapability.mockImplementation((capability) => capability === 'analytics.my_performance');
    mockedGet.mockResolvedValue({ data: performanceEnvelope } as never);
    renderPage();

    expect(await screen.findByText('Completed (Month)')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'week' }));

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith('/analytics/my-performance', {
        params: { period: 'week' },
      });
    });
    expect(await screen.findByText('Completed (Week)')).toBeTruthy();
    expect(mockedGet).not.toHaveBeenCalledWith('/analytics/overview', expect.anything());
  });

  it('preserves permission-based access restrictions', () => {
    mockedCanAccessModule.mockReturnValue(false);
    mockedHasCapability.mockReturnValue(false);
    renderPage();

    expect(screen.getByText('Analytics access is restricted for your role.')).toBeTruthy();
    expect(mockedGet).not.toHaveBeenCalled();
  });
});
