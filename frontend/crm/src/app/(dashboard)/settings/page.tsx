'use client';

import React, { useState } from 'react';
import { AppShell } from '../../../components/layout/AppShell';
import { DataTable, Column } from '../../../components/ui/DataTable';
import { AccessRestricted } from '../../../components/ui/AccessRestricted';
import { AuditLog, User } from '../../../types/api';
import { useUsers, useDeleteUser } from '../../../features/users/api';
import { useAuditLogs } from '../../../features/audit/api';
import { useAuthStore } from '../../../store';
import { canAccessModule, hasCapability, usePermissionSubscription } from '../../../config/permissions';
import { Settings as SettingsIcon, Users, FileText, Save, Plus, Loader2, Trash2, Info, RotateCcw, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { useClinicSettings, useUpdateClinicSettings } from '../../../features/settings/api';
import { AddUserSlideOver } from '../../../features/users/components/AddUserSlideOver';
import { UserPermissionsSlideOver } from '../../../features/users/components/UserPermissionsSlideOver';
import { JsonViewerSlideOver } from '../../../components/ui/JsonViewerSlideOver';
import {
  Avatar,
  Badge,
  type BadgeTone,
  Button,
  Card,
  FieldLabel,
  PageHeader,
  SegmentGroup,
  SegmentTab,
  inputClass,
} from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

type TabKey = 'clinic' | 'users' | 'audit';

/** The AV Suite theme colour (globals.css --brand-navy). Used when a clinic has no colour of its own. */
const THEME_DEFAULT_COLOR = '#0b1238';

const ROLE_TONE: Record<string, BadgeTone> = {
  admin: 'info',
  therapist: 'active',
  front_desk: 'warn',
};

const timestampFormat = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

function formatTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : timestampFormat.format(date);
}

function actionTone(action: string): BadgeTone {
  if (action.includes('delete')) return 'danger';
  if (action.includes('update')) return 'warn';
  return 'ok';
}

export default function SettingsPage() {
  usePermissionSubscription(); // see Decisions.md D-013
  const userId = useAuthStore((s) => s.userId);

  const hasAccess = canAccessModule('settings');
  const canViewClinic = hasCapability('settings.view');
  const canEditClinic = hasCapability('settings.edit');
  const canViewUsers = hasCapability('users.view');
  const canCreateUser = hasCapability('users.create');
  const canDeleteUser = hasCapability('users.delete');
  const canEditPermissions = hasCapability('permissions.edit');
  const canViewAudit = hasCapability('audit.view');

  // Default tab is derived each render (capabilities can load after the first
  // render); a user's explicit choice wins while it stays visible.
  const tabs: { key: TabKey; label: string; icon: React.ElementType; visible: boolean }[] = [
    { key: 'clinic', label: 'Clinic & Branding', icon: SettingsIcon, visible: canViewClinic },
    { key: 'users', label: 'User Management', icon: Users, visible: canViewUsers },
    { key: 'audit', label: 'Audit Log', icon: FileText, visible: canViewAudit },
  ];
  const visibleTabs = tabs.filter((t) => t.visible);
  const [selectedTab, setSelectedTab] = useState<TabKey | null>(null);
  const activeTab: TabKey | null =
    selectedTab && visibleTabs.some((t) => t.key === selectedTab) ? selectedTab : visibleTabs[0]?.key ?? null;

  const [clinicName, setClinicName] = useState('');
  // null = no clinic colour, the AV Suite theme applies.
  const [brandColor, setBrandColor] = useState<string | null>(null);
  const [colorDirty, setColorDirty] = useState(false);
  const [logoBase64, setLogoBase64] = useState<string | null>(null);
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);
  const [isPermissionsOpen, setIsPermissionsOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [auditPage, setAuditPage] = useState(1);
  const [auditOnlyMine, setAuditOnlyMine] = useState(false);
  const [selectedLogForDetails, setSelectedLogForDetails] = useState<AuditLog | null>(null);

  const { data: clinicSettings, isLoading: isLoadingSettings } = useClinicSettings(canViewClinic);
  const updateSettings = useUpdateClinicSettings();
  const deleteUser = useDeleteUser();
  const savedColor = clinicSettings?.branding_color ?? null;

  React.useEffect(() => {
    if (clinicSettings) {
      setClinicName(clinicSettings.name || '');
      setBrandColor(clinicSettings.branding_color ?? null);
      setColorDirty(false);
      setLogoBase64(clinicSettings.branding_logo_url ?? null);
    }
  }, [clinicSettings]);

  // Live preview of the colour while editing. Leaving the page without saving
  // restores the saved colour so an unsaved preview does not stick around.
  React.useEffect(() => {
    document.documentElement.style.setProperty('--brand-navy', brandColor || THEME_DEFAULT_COLOR);
  }, [brandColor]);
  const savedColorRef = React.useRef<string | null>(savedColor);
  savedColorRef.current = savedColor;
  React.useEffect(() => {
    // Unmount only: read the latest saved colour from the ref.
    return () => {
      document.documentElement.style.setProperty('--brand-navy', savedColorRef.current || THEME_DEFAULT_COLOR);
    };
  }, []);

  const { data: usersResponse, isLoading: isLoadingUsers } = useUsers(canViewUsers);
  const users = usersResponse || [];

  // Audit logs are clinic-scoped by the backend. Previously the page always
  // filtered to the signed-in user, so admins only saw their own actions.
  const { data: auditResponse, isLoading: isLoadingAudit } = useAuditLogs(
    auditPage,
    50,
    auditOnlyMine ? userId : null,
    canViewAudit,
  );
  const auditLogs = auditResponse?.data || [];
  const auditTotal = auditResponse?.meta?.total ?? auditLogs.length;

  const userName = (id: string | null | undefined) => {
    if (!id) return 'System';
    const u = users.find((user) => user.id === id);
    return u ? `${u.first_name} ${u.last_name}` : `User #${id.slice(0, 8).toUpperCase()}`;
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 200 * 1024) {
      toast.error('Logo file size must be under 200KB');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setLogoBase64(reader.result as string);
      toast.success('Logo ready. Save to apply it.');
    };
    reader.readAsDataURL(file);
  };

  const handleSaveClinic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEditClinic) {
      toast.error('You do not have permission to edit clinic settings');
      return;
    }
    try {
      await updateSettings.mutateAsync({
        name: clinicName,
        // Only send the colour when it was changed, so saving the name never
        // writes a default colour over the theme (null resets to the theme).
        ...(colorDirty ? { branding_color: brandColor } : {}),
        branding_logo_url: logoBase64,
      });
      toast.success('Clinic settings saved');
    } catch (err) {
      toast.error('Failed to save clinic settings');
    }
  };

  const auditColumns: Column<AuditLog>[] = [
    {
      key: 'action',
      header: 'Action',
      render: (log) => (
        <Badge tone={actionTone(log.action)} className="font-mono uppercase">
          {log.action}
        </Badge>
      ),
    },
    {
      key: 'entity_type',
      header: 'Entity',
      render: (log) => <span className="font-semibold capitalize text-ink">{log.entity_type.replace(/_/g, ' ')}</span>,
    },
    {
      key: 'entity_id',
      header: 'Entity Ref',
      render: (log) =>
        log.entity_id ? (
          <span title={log.entity_id} className="font-mono text-xs text-muted">
            #{log.entity_id.slice(0, 8).toUpperCase()}
          </span>
        ) : (
          <span className="text-slate-400">-</span>
        ),
    },
    { key: 'user_id', header: 'By', render: (log) => <span className="text-ink-2">{userName(log.user_id)}</span> },
    {
      key: 'details',
      header: 'Details',
      render: (log) => (
        <button
          onClick={() => setSelectedLogForDetails(log)}
          className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg border border-line bg-card px-2.5 text-xs font-semibold text-ink-2 transition-colors hover:bg-canvas"
        >
          <FileText className="h-3.5 w-3.5" />
          View Payload
        </button>
      ),
    },
    {
      key: 'created_at',
      header: 'Time',
      render: (log) => <span className="whitespace-nowrap text-xs tabular-nums text-muted">{formatTimestamp(log.created_at)}</span>,
    },
  ];

  const userColumns: Column<User>[] = [
    {
      key: 'name',
      header: 'User',
      render: (u) => (
        <div className="flex items-center gap-3">
          <Avatar name={`${u.first_name} ${u.last_name}`} size={32} />
          <div>
            <p className="font-semibold text-ink">
              {u.first_name} {u.last_name}
              {u.id === userId && <span className="ml-1.5 text-xs font-medium text-muted">(you)</span>}
            </p>
            <p className="text-xs text-muted">{u.email}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (u) => (
        <Badge tone={ROLE_TONE[u.role] ?? 'neutral'} className="capitalize">
          {u.role.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (u) => (u.is_active ? <Badge tone="ok">Active</Badge> : <Badge tone="neutral">Inactive</Badge>),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (u) => (
        <div className="flex items-center gap-2">
          {canEditPermissions && (
            <button
              onClick={() => {
                setSelectedUser(u);
                setIsPermissionsOpen(true);
              }}
              className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-lg bg-info-wash px-2.5 text-xs font-semibold text-info transition-colors hover:bg-[#dde2fa]"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Edit Permissions
            </button>
          )}
          {canDeleteUser && u.id !== userId && (
            <button
              onClick={async () => {
                if (window.confirm(`Are you sure you want to remove ${u.first_name} ${u.last_name}?`)) {
                  try {
                    await deleteUser.mutateAsync(u.id);
                    toast.success('User removed successfully');
                  } catch (err: any) {
                    toast.error(err.response?.data?.detail || 'Failed to remove user');
                  }
                }
              }}
              disabled={deleteUser.isPending}
              className="grid h-8 w-8 cursor-pointer place-items-center rounded-lg text-danger transition-colors hover:bg-danger-wash disabled:opacity-50"
              title="Remove User"
              aria-label={`Remove ${u.first_name} ${u.last_name}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      ),
    },
  ];

  if (!hasAccess || visibleTabs.length === 0) {
    // AccessRestricted renders its own AppShell.
    return <AccessRestricted message="Clinic settings are restricted." />;
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <PageHeader
          title="Clinic Settings"
          subtitle="Manage clinic branding, users and audit logs"
          actions={
            activeTab === 'users' && canCreateUser ? (
              <Button onClick={() => setIsAddUserOpen(true)}>
                <Plus className="h-4 w-4" />
                <span>Add User</span>
              </Button>
            ) : null
          }
        />

        <SegmentGroup>
          {visibleTabs.map((tab) => (
            <SegmentTab key={tab.key} active={activeTab === tab.key} onClick={() => setSelectedTab(tab.key)} icon={tab.icon}>
              {tab.label}
              {tab.key === 'audit' && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold tabular-nums text-muted">
                  {auditTotal}
                </span>
              )}
            </SegmentTab>
          ))}
        </SegmentGroup>

        {/* Clinic Branding Settings Tab */}
        {activeTab === 'clinic' && (
          <form onSubmit={handleSaveClinic} className="grid max-w-5xl gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
            <Card className="space-y-5 p-6">
              <div className="flex items-start gap-2.5 rounded-xl border border-logo-teal/25 bg-logo-teal-wash px-3.5 py-3 text-xs leading-relaxed text-logo-teal-ink">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Your clinic name, colour and logo appear in this CRM&apos;s sidebar and header, and on your public
                  booking page.
                </span>
              </div>

              {isLoadingSettings ? (
                <div className="flex items-center gap-2 py-6 text-sm text-muted">
                  <Loader2 className="h-4 w-4 animate-spin text-grove" /> Loading clinic settings...
                </div>
              ) : (
                <>
                  <div>
                    <FieldLabel htmlFor="clinic-name">Clinic Name</FieldLabel>
                    <input
                      id="clinic-name"
                      type="text"
                      value={clinicName}
                      onChange={(e) => setClinicName(e.target.value)}
                      disabled={!canEditClinic}
                      className={inputClass}
                    />
                  </div>

                  <div>
                    <FieldLabel htmlFor="brand-color">Brand Accent Colour</FieldLabel>
                    <div className="flex flex-wrap items-center gap-3">
                      <input
                        id="brand-color"
                        type="color"
                        value={brandColor || THEME_DEFAULT_COLOR}
                        onChange={(e) => {
                          setBrandColor(e.target.value);
                          setColorDirty(true);
                        }}
                        disabled={!canEditClinic}
                        className="h-10 w-12 cursor-pointer rounded-[10px] border border-line bg-card p-1 disabled:cursor-not-allowed disabled:opacity-60"
                      />
                      <span className="font-mono text-xs uppercase text-muted">
                        {brandColor ? brandColor : `${THEME_DEFAULT_COLOR} (AV Suite default)`}
                      </span>
                      {canEditClinic && brandColor && (
                        <button
                          type="button"
                          onClick={() => {
                            setBrandColor(null);
                            setColorDirty(true);
                          }}
                          className="inline-flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-grove hover:text-grove-hover"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          Use AV Suite default
                        </button>
                      )}
                    </div>
                  </div>

                  <div>
                    <FieldLabel htmlFor="clinic-logo">Clinic Logo (max 200KB)</FieldLabel>
                    {canEditClinic && (
                      <input
                        id="clinic-logo"
                        type="file"
                        accept="image/*"
                        onChange={handleLogoUpload}
                        className="w-full cursor-pointer text-xs text-muted file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-grove-wash file:px-4 file:py-2 file:text-xs file:font-semibold file:text-grove hover:file:bg-[#d3eedc]"
                      />
                    )}
                    {logoBase64 && (
                      <div className="mt-3 flex items-center gap-3">
                        <div className="w-fit rounded-xl border border-line bg-canvas p-2">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={logoBase64} alt="Clinic logo preview" className="h-12 rounded object-contain" />
                        </div>
                        {canEditClinic && (
                          <button
                            type="button"
                            onClick={() => setLogoBase64(null)}
                            className="cursor-pointer text-xs font-semibold text-danger hover:underline"
                          >
                            Remove logo
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {canEditClinic && (
                    <div className="border-t border-line pt-5">
                      <Button type="submit" disabled={updateSettings.isPending}>
                        {updateSettings.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        <span>Save Settings</span>
                      </Button>
                    </div>
                  )}
                </>
              )}
            </Card>

            {/* Live preview of how the branding looks in the sidebar */}
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">Sidebar preview</p>
              <div
                className="overflow-hidden rounded-2xl p-4 text-white shadow-card"
                style={{ background: brandColor || THEME_DEFAULT_COLOR }}
              >
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-[11px] bg-white p-1">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={logoBase64 || '/brand/av-logo-mark.png'} alt="" className="h-full w-full object-contain" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate font-display text-sm font-bold">{clinicName || 'Your clinic'}</p>
                    <p className="text-[11px] text-white/70">Clinic CRM</p>
                  </div>
                </div>
                <div className="mt-4 space-y-1">
                  <div className="flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-xs font-semibold">
                    <span className="h-1.5 w-1.5 rounded-full bg-lime" /> Dashboard
                  </div>
                  <div className="px-3 py-2 text-xs text-white/70">Patients</div>
                </div>
              </div>
            </div>
          </form>
        )}

        {/* User Management Tab */}
        {activeTab === 'users' && <DataTable columns={userColumns} data={users} isLoading={isLoadingUsers} />}

        {/* Audit Log Tab */}
        {activeTab === 'audit' && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <SegmentGroup aria-label="Audit log scope">
                <SegmentTab
                  active={!auditOnlyMine}
                  onClick={() => {
                    setAuditOnlyMine(false);
                    setAuditPage(1);
                  }}
                  icon={Users}
                >
                  All users
                </SegmentTab>
                <SegmentTab
                  active={auditOnlyMine}
                  onClick={() => {
                    setAuditOnlyMine(true);
                    setAuditPage(1);
                  }}
                  icon={ShieldCheck}
                >
                  Only my actions
                </SegmentTab>
              </SegmentGroup>
              <span className="text-xs font-medium text-muted">{auditTotal} entries</span>
            </div>
            {/* No search box: the audit API pages on the server and has no search
                parameter, so a client-side box would only filter the current page. */}
            <DataTable
              columns={auditColumns}
              data={auditLogs}
              isLoading={isLoadingAudit}
              totalItems={auditTotal}
              currentPage={auditPage}
              pageSize={50}
              onPageChange={(page) => setAuditPage(page)}
              emptyMessage="No audit entries yet."
            />
          </div>
        )}
      </div>

      <AddUserSlideOver isOpen={isAddUserOpen} onClose={() => setIsAddUserOpen(false)} />
      <UserPermissionsSlideOver
        isOpen={isPermissionsOpen}
        onClose={() => setIsPermissionsOpen(false)}
        user={selectedUser}
      />
      <JsonViewerSlideOver
        isOpen={!!selectedLogForDetails}
        onClose={() => setSelectedLogForDetails(null)}
        title={`Log Details: ${selectedLogForDetails?.action || ''}`}
        data={selectedLogForDetails?.details || {}}
      />
    </AppShell>
  );
}
