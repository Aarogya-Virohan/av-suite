import { UserRole } from '../types/api';

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
      patients: true,
      appointments: true,
      analytics: true,
      billing: true,
      leads: true,
      therapists: true,
      recycleBin: true,
      settings: true,
    },
    patientTabs: {
      timeline: true,
      documents: true,
      treatments: true,
      soapNotes: true,
      assessments: true,
      billing: true,
    },
    actions: {
      createEditPatient: true,
      deletePatient: true,
      manageAppointments: true,
      createEditSoapNote: true,
      createInvoiceRecordPayment: true,
      createSellPackage: true,
      uploadDownloadDocuments: true,
      restoreDeletedRecords: true,
      manageUsersAndRoles: true,
      updateClinicSettings: true,
    },
  },
  therapist: {
    sidebar: {
      dashboard: true,
      patients: true,
      appointments: true, // own only (server filtered)
      analytics: true,    // own only (server filtered)
      billing: false,
      leads: false,
      therapists: false,
      recycleBin: false,
      settings: false,
    },
    patientTabs: {
      timeline: true,
      documents: true,
      treatments: true,
      soapNotes: true,
      assessments: true,
      billing: false,
    },
    actions: {
      createEditPatient: true,
      deletePatient: false,
      manageAppointments: true, // own only
      createEditSoapNote: true,  // own only
      createInvoiceRecordPayment: false,
      createSellPackage: false,
      uploadDownloadDocuments: true,
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: false,
    },
  },
  front_desk: {
    sidebar: {
      dashboard: true,
      patients: true,
      appointments: true,
      analytics: false,
      billing: true,
      leads: true,
      therapists: false,
      recycleBin: false,
      settings: false,
    },
    patientTabs: {
      timeline: true,
      documents: true,
      treatments: false,
      soapNotes: false,
      assessments: false,
      billing: true,
    },
    actions: {
      createEditPatient: true,
      deletePatient: false,
      manageAppointments: true,
      createEditSoapNote: false,
      createInvoiceRecordPayment: true,
      createSellPackage: false,
      uploadDownloadDocuments: true,
      restoreDeletedRecords: false,
      manageUsersAndRoles: false,
      updateClinicSettings: false,
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
