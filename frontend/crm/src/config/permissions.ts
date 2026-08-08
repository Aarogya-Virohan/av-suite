import { UserRole } from '../types/api';

// ---------------------------------------------------------
// BACKEND ALIGNMENT
// This map perfectly matches backend/app/core/rbac.py
// ---------------------------------------------------------
export const BACKEND_PERMISSION_MAP: Record<string, UserRole[]> = {
  patients: ['admin', 'therapist', 'front_desk'],
  treatments: ['admin', 'therapist'],
  assessments: ['admin', 'therapist'],
  billing: ['admin', 'front_desk'],
  analytics: ['admin', 'therapist'],
  leads: ['admin', 'front_desk'],
  documents: ['admin', 'therapist', 'front_desk'],
  appointments: ['admin', 'therapist', 'front_desk'],
  exercises: ['admin', 'therapist'],
  posture: ['admin', 'therapist'],
  prescriptions: ['admin', 'therapist'],
  settings: ['admin'],
  packages: ['admin'],
  clinic_admin: ['admin', 'therapist', 'front_desk'],
  booking: ['admin', 'therapist', 'front_desk'],
  appointment_requests: ['admin', 'therapist', 'front_desk'],
};

export function hasBackendPermission(role: UserRole, resource: string): boolean {
  const allowedRoles = BACKEND_PERMISSION_MAP[resource];
  return allowedRoles ? allowedRoles.includes(role) : false;
}

// ---------------------------------------------------------
// FRONTEND UI MAPPINGS
// ---------------------------------------------------------
export interface ModuleVisibility {
  dashboard: boolean;
  patients: boolean;
  appointments: boolean;
  analytics: boolean;
  billing: boolean;
  leads: boolean;
  therapists: boolean;
  recycleBin: boolean;
  settings: boolean;
}

export interface PatientTabVisibility {
  timeline: boolean;
  documents: boolean;
  treatments: boolean;
  soapNotes: boolean;
  assessments: boolean;
  billing: boolean;
}

export interface ActionPermissions {
  createEditPatient: boolean;
  deletePatient: boolean;
  manageAppointments: boolean;
  createEditSoapNote: boolean;
  createInvoiceRecordPayment: boolean;
  createSellPackage: boolean;
  uploadDownloadDocuments: boolean;
  restoreDeletedRecords: boolean;
  manageUsersAndRoles: boolean;
  updateClinicSettings: boolean;
}

export interface RolePermissions {
  sidebar: ModuleVisibility;
  patientTabs: PatientTabVisibility;
  actions: ActionPermissions;
}

export const PERMISSIONS_MATRIX: Record<UserRole, RolePermissions> = {
  admin: {
    sidebar: {
      dashboard: true,
      patients: hasBackendPermission('admin', 'patients'),
      appointments: hasBackendPermission('admin', 'appointments'),
      analytics: hasBackendPermission('admin', 'analytics'),
      billing: hasBackendPermission('admin', 'billing'),
      leads: hasBackendPermission('admin', 'leads'),
      therapists: hasBackendPermission('admin', 'clinic_admin'),
      recycleBin: true, // Frontend virtual module
      settings: hasBackendPermission('admin', 'settings'),
    },
    patientTabs: {
      timeline: true,
      documents: hasBackendPermission('admin', 'documents'),
      treatments: hasBackendPermission('admin', 'treatments'),
      soapNotes: hasBackendPermission('admin', 'assessments'),
      assessments: hasBackendPermission('admin', 'assessments'),
      billing: hasBackendPermission('admin', 'billing'),
    },
    actions: {
      createEditPatient: hasBackendPermission('admin', 'patients'),
      deletePatient: hasBackendPermission('admin', 'patients'),
      manageAppointments: hasBackendPermission('admin', 'appointments'),
      createEditSoapNote: hasBackendPermission('admin', 'assessments'),
      createInvoiceRecordPayment: hasBackendPermission('admin', 'billing'),
      createSellPackage: hasBackendPermission('admin', 'packages'),
      uploadDownloadDocuments: hasBackendPermission('admin', 'documents'),
      restoreDeletedRecords: true,
      manageUsersAndRoles: hasBackendPermission('admin', 'clinic_admin'),
      updateClinicSettings: hasBackendPermission('admin', 'settings'),
    },
  },
  therapist: {
    sidebar: {
      dashboard: true,
      patients: hasBackendPermission('therapist', 'patients'),
      appointments: hasBackendPermission('therapist', 'appointments'),
      analytics: hasBackendPermission('therapist', 'analytics'),
      billing: hasBackendPermission('therapist', 'billing'),
      leads: hasBackendPermission('therapist', 'leads'),
      therapists: false, 
      recycleBin: false,
      settings: hasBackendPermission('therapist', 'settings'),
    },
    patientTabs: {
      timeline: true,
      documents: hasBackendPermission('therapist', 'documents'),
      treatments: hasBackendPermission('therapist', 'treatments'),
      soapNotes: hasBackendPermission('therapist', 'assessments'),
      assessments: hasBackendPermission('therapist', 'assessments'),
      billing: hasBackendPermission('therapist', 'billing'),
    },
    actions: {
      createEditPatient: hasBackendPermission('therapist', 'patients'),
      deletePatient: false,
      manageAppointments: hasBackendPermission('therapist', 'appointments'),
      createEditSoapNote: hasBackendPermission('therapist', 'assessments'),
      createInvoiceRecordPayment: hasBackendPermission('therapist', 'billing'),
      createSellPackage: hasBackendPermission('therapist', 'packages'),
      uploadDownloadDocuments: hasBackendPermission('therapist', 'documents'),
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: hasBackendPermission('therapist', 'settings'),
    },
  },
  front_desk: {
    sidebar: {
      dashboard: true,
      patients: hasBackendPermission('front_desk', 'patients'),
      appointments: hasBackendPermission('front_desk', 'appointments'),
      analytics: hasBackendPermission('front_desk', 'analytics'),
      billing: hasBackendPermission('front_desk', 'billing'),
      leads: hasBackendPermission('front_desk', 'leads'),
      therapists: false,
      recycleBin: false,
      settings: hasBackendPermission('front_desk', 'settings'),
    },
    patientTabs: {
      timeline: true,
      documents: hasBackendPermission('front_desk', 'documents'),
      treatments: hasBackendPermission('front_desk', 'treatments'),
      soapNotes: hasBackendPermission('front_desk', 'assessments'),
      assessments: hasBackendPermission('front_desk', 'assessments'),
      billing: hasBackendPermission('front_desk', 'billing'),
    },
    actions: {
      createEditPatient: hasBackendPermission('front_desk', 'patients'),
      deletePatient: false,
      manageAppointments: hasBackendPermission('front_desk', 'appointments'),
      createEditSoapNote: hasBackendPermission('front_desk', 'assessments'),
      createInvoiceRecordPayment: hasBackendPermission('front_desk', 'billing'),
      createSellPackage: hasBackendPermission('front_desk', 'packages'),
      uploadDownloadDocuments: hasBackendPermission('front_desk', 'documents'),
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: hasBackendPermission('front_desk', 'settings'),
    },
  },
  patient: {
    sidebar: {
      dashboard: false,
      patients: false,
      appointments: false,
      analytics: false,
      billing: false,
      leads: false,
      therapists: false,
      recycleBin: false,
      settings: false,
    },
    patientTabs: {
      timeline: false,
      documents: false,
      treatments: false,
      soapNotes: false,
      assessments: false,
      billing: false,
    },
    actions: {
      createEditPatient: false,
      deletePatient: false,
      manageAppointments: false,
      createEditSoapNote: false,
      createInvoiceRecordPayment: false,
      createSellPackage: false,
      uploadDownloadDocuments: false,
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: false,
    },
  },
};

export function getPermissionsForRole(role: UserRole): RolePermissions {
  return PERMISSIONS_MATRIX[role] || PERMISSIONS_MATRIX.front_desk;
}

export function canAccessModule(role: UserRole, module: keyof ModuleVisibility): boolean {
  return getPermissionsForRole(role).sidebar[module];
}

export function canPerformAction(role: UserRole, action: keyof ActionPermissions): boolean {
  return getPermissionsForRole(role).actions[action];
}
