import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  Patient,
  Lead,
  Appointment,
  AppointmentRequest,
  SOAPAssessment,
  TreatmentSession,
  PatientPackage,
  Invoice,
  InvoiceStatus,
  Payment,
  PatientDocument,
  Therapist,
  ClinicBranding,
  RecycleBinItem,
  RunningCost,
  AuditLog
} from '@/types/crm';

interface CRMStore {
  // Clinic Branding
  branding: ClinicBranding;
  updateBranding: (branding: Partial<ClinicBranding>) => void;

  // Therapists
  therapists: Therapist[];
  addTherapist: (therapist: Omit<Therapist, 'id'>) => void;
  updateTherapist: (id: string, therapist: Partial<Therapist>) => void;
  deleteTherapist: (id: string) => void;

  // Patients
  patients: Patient[];
  addPatient: (patient: Omit<Patient, 'id' | 'clinicId' | 'createdAt'>) => Patient;
  updatePatient: (id: string, patient: Partial<Patient>) => void;
  deletePatient: (id: string) => void;

  // Leads
  leads: Lead[];
  addLead: (lead: Omit<Lead, 'id' | 'clinicId' | 'createdAt'>) => void;
  updateLead: (id: string, lead: Partial<Lead>) => void;
  deleteLead: (id: string) => void;
  convertLeadToPatient: (leadId: string) => Patient | null;

  // Appointments
  appointments: Appointment[];
  addAppointment: (appt: Omit<Appointment, 'id' | 'clinicId' | 'createdAt'>) => void;
  updateAppointmentStatus: (id: string, status: Appointment['status']) => void;
  deleteAppointment: (id: string) => void;

  // Booking Requests
  appointmentRequests: AppointmentRequest[];
  approveRequest: (requestId: string, therapistId?: string, duration?: number) => void;
  rejectRequest: (requestId: string) => void;

  // Clinical Treatments & Assessments
  assessments: SOAPAssessment[];
  addAssessment: (asm: Omit<SOAPAssessment, 'id' | 'clinicId' | 'createdAt'>) => void;
  deleteAssessment: (id: string) => void;

  treatments: TreatmentSession[];
  addTreatment: (tx: Omit<TreatmentSession, 'id' | 'clinicId' | 'createdAt'>) => void;
  deleteTreatment: (id: string) => void;

  // Patient Packages
  packages: PatientPackage[];
  addPackage: (pkg: Omit<PatientPackage, 'id' | 'clinicId' | 'createdAt'>) => void;
  updatePackageSessions: (id: string, sessionsUsed: number) => void;
  expirePackage: (id: string) => void;

  // Invoices & Payments
  invoices: Invoice[];
  addInvoice: (inv: Omit<Invoice, 'id' | 'clinicId' | 'createdAt' | 'paidAmount' | 'status'>) => void;
  deleteInvoice: (id: string) => void;

  payments: Payment[];
  recordPayment: (payment: Omit<Payment, 'id' | 'clinicId'>) => void;

  // Documents
  documents: PatientDocument[];
  addDocument: (doc: Omit<PatientDocument, 'id' | 'clinicId' | 'createdAt'>) => void;
  deleteDocument: (id: string) => void;

  // Running Costs
  runningCosts: RunningCost[];
  addRunningCost: (cost: Omit<RunningCost, 'id'>) => void;
  updateRunningCost: (id: string, cost: Partial<RunningCost>) => void;
  deleteRunningCost: (id: string) => void;

  // Recycle Bin
  recycleBin: RecycleBinItem[];
  restoreFromRecycleBin: (id: string) => void;
  permanentlyDeleteFromRecycleBin: (id: string) => void;

  // Audit Logs
  auditLogs: AuditLog[];
  logAudit: (action: string, entityType: AuditLog['entityType'], entityId: string, description: string) => void;
}

const DEFAULT_CLINIC_ID = 'clinic_01';

const INITIAL_BRANDING: ClinicBranding = {
  clinicName: 'Aarogya Virohan',
  phone: '+91 98765 43210',
  address: '123 Health Avenue, Medical Hub, Mumbai',
  doctorName: 'Dr. Ramesh Sharma (PT)',
  regNo: 'PT-2024-8891',
  brandColor: '#0B2C5F',
  apiUrl: '',
  bookingUrl: 'https://aarogyavirohan.com/book'
};

const INITIAL_THERAPISTS: Therapist[] = [
  {
    id: 'th_1',
    name: 'Dr. Ramesh Sharma',
    specialization: 'Senior Physiotherapist (Ortho & Neuro)',
    mobile: '9876543210',
    email: 'ramesh@aarogyavirohan.com',
    regNo: 'PT-2024-8891',
    salary: 45000,
    qualification: 'MPT (Musculoskeletal), BPT'
  },
  {
    id: 'th_2',
    name: 'Dr. Priya Ananth',
    specialization: 'Neuro & Paediatric PT',
    mobile: '9876543211',
    email: 'priya@aarogyavirohan.com',
    regNo: 'PT-2025-4412',
    salary: 40000,
    qualification: 'MPT (Neurology)'
  }
];

const INITIAL_PATIENTS: Patient[] = [
  {
    id: 'p_101',
    clinicId: DEFAULT_CLINIC_ID,
    name: 'Rajesh Malhotra',
    mobile: '9820112233',
    age: 48,
    gender: 'Male',
    email: 'rajesh.m@example.com',
    address: 'B-402, Green Acres, Andheri West',
    referralSource: 'Doctor Referral',
    status: 'Active',
    diagnosis: 'Chronic Lower Back Pain (L4-L5 Disc Herniation)',
    medicalHistory: 'Hypertension, Sedentary desk job',
    createdAt: '2026-07-01T10:00:00Z'
  },
  {
    id: 'p_102',
    clinicId: DEFAULT_CLINIC_ID,
    name: 'Sunita Deshmukh',
    mobile: '9833445566',
    age: 54,
    gender: 'Female',
    email: 'sunita.d@example.com',
    address: '12-A, Shiv Shahi Society, Dadar',
    referralSource: 'Google Search',
    status: 'Active',
    diagnosis: 'Post-op Knee Arthroscopy (Right Knee)',
    medicalHistory: 'No major comorbidities',
    createdAt: '2026-07-05T14:30:00Z'
  },
  {
    id: 'p_103',
    clinicId: DEFAULT_CLINIC_ID,
    name: 'Anil Kapoor',
    mobile: '7500294955',
    age: 35,
    gender: 'Male',
    email: 'anil.k@example.com',
    address: 'Flat 501, Horizon Tower, Bandra',
    referralSource: 'Instagram',
    status: 'Discharged',
    diagnosis: 'Acute Cervical Spondylosis',
    medicalHistory: 'Frequent computer use',
    createdAt: '2026-06-15T09:15:00Z'
  }
];

const INITIAL_LEADS: Lead[] = [];

const INITIAL_APPOINTMENTS: Appointment[] = [];

const INITIAL_REQUESTS: AppointmentRequest[] = [];

const INITIAL_TREATMENTS: TreatmentSession[] = [
  {
    id: 'tx_1',
    clinicId: DEFAULT_CLINIC_ID,
    patientId: 'p_101',
    date: '2026-07-02',
    therapist: 'Dr. Ramesh Sharma',
    painScore: 8,
    treatment: 'Initial assessment, IFT 15 mins, moist heat, McKenzie extension exercises',
    homeAdvice: 'Perform 10 extension reps every 2 hours, avoid slouching.',
    createdAt: '2026-07-02T11:00:00Z'
  },
  {
    id: 'tx_2',
    clinicId: DEFAULT_CLINIC_ID,
    patientId: 'p_101',
    date: '2026-07-08',
    therapist: 'Dr. Ramesh Sharma',
    painScore: 6,
    treatment: 'Ultrasound therapy 1.5 W/cm², spinal mobilization grade II, pelvic bridging',
    homeAdvice: 'Continue extensions and added abdominal draw-in maneuver.',
    createdAt: '2026-07-08T11:00:00Z'
  },
  {
    id: 'tx_3',
    clinicId: DEFAULT_CLINIC_ID,
    patientId: 'p_101',
    date: '2026-07-15',
    therapist: 'Dr. Ramesh Sharma',
    painScore: 3,
    treatment: 'Advanced core stability, resistance band exercises, gait correction',
    homeAdvice: 'Ergonomic lumbar support at work office chair.',
    createdAt: '2026-07-15T11:00:00Z'
  }
];

const INITIAL_PACKAGES: PatientPackage[] = [];

const INITIAL_INVOICES: Invoice[] = [];

const INITIAL_RUNNING_COSTS: RunningCost[] = [
  { id: 'rc_1', label: 'Clinic Rent', amount: 35000 },
  { id: 'rc_2', label: 'Electricity & Utilities', amount: 8500 },
  { id: 'rc_3', label: 'Medical Supplies & Gel', amount: 5000 }
];

export const useCRMStore = create<CRMStore>()(
  persist(
    (set, get) => ({
      branding: INITIAL_BRANDING,
      updateBranding: (newBranding) =>
        set((state) => ({ branding: { ...state.branding, ...newBranding } })),

      therapists: INITIAL_THERAPISTS,
      addTherapist: (th) =>
        set((state) => ({
          therapists: [...state.therapists, { ...th, id: `th_${Date.now()}` }]
        })),
      updateTherapist: (id, th) =>
        set((state) => ({
          therapists: state.therapists.map((t) => (t.id === id ? { ...t, ...th } : t))
        })),
      deleteTherapist: (id) =>
        set((state) => ({
          therapists: state.therapists.filter((t) => t.id !== id)
        })),

      patients: INITIAL_PATIENTS,
      addPatient: (ptData) => {
        const newPt: Patient = {
          ...ptData,
          id: `p_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID,
          createdAt: new Date().toISOString()
        };
        set((state) => ({ patients: [newPt, ...state.patients] }));
        get().logAudit('CREATE_PATIENT', 'patient', newPt.id, `Added patient ${newPt.name}`);
        return newPt;
      },
      updatePatient: (id, ptData) =>
        set((state) => {
          const updated = state.patients.map((p) =>
            p.id === id ? { ...p, ...ptData, updatedAt: new Date().toISOString() } : p
          );
          get().logAudit('UPDATE_PATIENT', 'patient', id, `Updated patient information`);
          return { patients: updated };
        }),
      deletePatient: (id) => {
        const pt = get().patients.find((p) => p.id === id);
        if (pt) {
          set((state) => ({
            patients: state.patients.filter((p) => p.id !== id),
            recycleBin: [
              {
                id: `rcy_${Date.now()}`,
                type: 'patients',
                data: pt,
                deletedAt: new Date().toISOString()
              },
              ...state.recycleBin
            ]
          }));
          get().logAudit('DELETE_PATIENT', 'patient', id, `Moved patient ${pt.name} to Recycle Bin`);
        }
      },

      leads: INITIAL_LEADS,
      addLead: (leadData) => {
        const newLead: Lead = {
          ...leadData,
          id: `ld_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID,
          createdAt: new Date().toISOString()
        };
        set((state) => ({ leads: [newLead, ...state.leads] }));
        get().logAudit('CREATE_LEAD', 'lead', newLead.id, `Created lead ${newLead.name}`);
      },
      updateLead: (id, leadData) =>
        set((state) => ({
          leads: state.leads.map((l) => (l.id === id ? { ...l, ...leadData } : l))
        })),
      deleteLead: (id) => {
        const ld = get().leads.find((l) => l.id === id);
        if (ld) {
          set((state) => ({
            leads: state.leads.filter((l) => l.id !== id),
            recycleBin: [
              {
                id: `rcy_${Date.now()}`,
                type: 'leads',
                data: ld,
                deletedAt: new Date().toISOString()
              },
              ...state.recycleBin
            ]
          }));
        }
      },
      convertLeadToPatient: (leadId) => {
        const ld = get().leads.find((l) => l.id === leadId);
        if (!ld) return null;
        const newPt = get().addPatient({
          name: ld.name,
          mobile: ld.mobile || '',
          referralSource: ld.source,
          status: 'Active',
          notes: ld.notes
        } as any);
        set((state) => ({
          leads: state.leads.map((l) =>
            l.id === leadId ? { ...l, stage: 'Converted', convertedPatientId: newPt.id } : l
          )
        }));
        return newPt;
      },

      appointments: INITIAL_APPOINTMENTS,
      addAppointment: (apptData) => {
        const newAppt: Appointment = {
          ...apptData,
          id: `apt_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID,
          createdAt: new Date().toISOString()
        };
        set((state) => ({ appointments: [newAppt, ...state.appointments] }));
        get().logAudit('CREATE_APPOINTMENT', 'appointment', newAppt.id, `Scheduled appointment for ${newAppt.patientName}`);
      },
      updateAppointmentStatus: (id, status) =>
        set((state) => ({
          appointments: state.appointments.map((a) => (a.id === id ? { ...a, status } : a))
        })),
      deleteAppointment: (id) => {
        const appt = get().appointments.find((a) => a.id === id);
        if (appt) {
          set((state) => ({
            appointments: state.appointments.filter((a) => a.id !== id),
            recycleBin: [
              {
                id: `rcy_${Date.now()}`,
                type: 'appointments',
                data: appt,
                deletedAt: new Date().toISOString()
              },
              ...state.recycleBin
            ]
          }));
        }
      },

      appointmentRequests: INITIAL_REQUESTS,
      approveRequest: (requestId, therapistId, duration = 30) => {
        const req = get().appointmentRequests.find((r) => r.id === requestId);
        if (!req) return;

        // Auto-create or find Patient
        let pt = get().patients.find((p) => p.mobile === req.mobile);
        if (!pt) {
          pt = get().addPatient({
            name: req.name,
            mobile: req.mobile,
            age: req.age,
            gender: req.gender as any,
            referralSource: req.source || 'Public Booking',
            status: 'Active',
            diagnosis: req.chiefComplaint
          });
        }

        // Auto-create Appointment
        const ther = get().therapists.find((t) => t.id === therapistId);
        get().addAppointment({
          patientId: pt.id,
          patientName: pt.name,
          patientMobile: pt.mobile,
          therapist: ther ? ther.name : 'Unassigned',
          date: req.preferredDate,
          time: req.preferredTime,
          durationMinutes: duration,
          status: 'Confirmed',
          source: 'public_booking',
          notes: req.chiefComplaint
        });

        // Auto-create Lead
        get().addLead({
          name: req.name,
          mobile: req.mobile,
          source: req.source || 'Public Booking',
          stage: 'Appointment Booked',
          notes: `Auto-created from request. Complaint: ${req.chiefComplaint || 'None'}`
        });

        // Update Request Status
        set((state) => ({
          appointmentRequests: state.appointmentRequests.map((r) =>
            r.id === requestId ? { ...r, status: 'Approved' } : r
          )
        }));
      },
      rejectRequest: (requestId) =>
        set((state) => ({
          appointmentRequests: state.appointmentRequests.map((r) =>
            r.id === requestId ? { ...r, status: 'Rejected' } : r
          )
        })),

      assessments: [],
      addAssessment: (asmData) => {
        const newAsm: SOAPAssessment = {
          ...asmData,
          id: `asm_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID,
          createdAt: new Date().toISOString()
        };
        set((state) => ({ assessments: [newAsm, ...state.assessments] }));
      },
      deleteAssessment: (id) =>
        set((state) => ({ assessments: state.assessments.filter((a) => a.id !== id) })),

      treatments: INITIAL_TREATMENTS,
      addTreatment: (txData) => {
        const newTx: TreatmentSession = {
          ...txData,
          id: `tx_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID,
          createdAt: new Date().toISOString()
        };
        set((state) => ({ treatments: [newTx, ...state.treatments] }));

        // Deduct package session if active
        const activePkg = get().packages.find(
          (pkg) => pkg.patientId === txData.patientId && pkg.status === 'Active'
        );
        if (activePkg) {
          const newUsed = activePkg.sessionsUsed + 1;
          get().updatePackageSessions(activePkg.id, newUsed);
        }
      },
      deleteTreatment: (id) =>
        set((state) => ({ treatments: state.treatments.filter((t) => t.id !== id) })),

      packages: INITIAL_PACKAGES,
      addPackage: (pkgData) => {
        const newPkg: PatientPackage = {
          ...pkgData,
          id: `pkg_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID,
          createdAt: new Date().toISOString()
        };
        set((state) => ({ packages: [newPkg, ...state.packages] }));
      },
      updatePackageSessions: (id, sessionsUsed) =>
        set((state) => ({
          packages: state.packages.map((pkg) => {
            if (pkg.id === id) {
              const status = sessionsUsed >= pkg.totalSessions ? 'Expired' : 'Active';
              return { ...pkg, sessionsUsed, status };
            }
            return pkg;
          })
        })),
      expirePackage: (id) =>
        set((state) => ({
          packages: state.packages.map((pkg) => (pkg.id === id ? { ...pkg, status: 'Expired' } : pkg))
        })),

      invoices: INITIAL_INVOICES,
      addInvoice: (invData) => {
        const newInv: Invoice = {
          ...invData,
          id: `INV-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`,
          clinicId: DEFAULT_CLINIC_ID,
          paidAmount: 0,
          status: 'Due',
          createdAt: new Date().toISOString()
        };
        set((state) => ({ invoices: [newInv, ...state.invoices] }));
        get().logAudit('CREATE_INVOICE', 'invoice', newInv.id, `Created invoice for ${newInv.patientName} (Total ₹${newInv.total})`);
      },
      deleteInvoice: (id) => {
        const inv = get().invoices.find((i) => i.id === id);
        if (inv) {
          set((state) => ({
            invoices: state.invoices.filter((i) => i.id !== id),
            recycleBin: [
              {
                id: `rcy_${Date.now()}`,
                type: 'invoices',
                data: inv,
                deletedAt: new Date().toISOString()
              },
              ...state.recycleBin
            ]
          }));
        }
      },

      payments: [],
      recordPayment: (payData) => {
        const newPay: Payment = {
          ...payData,
          id: `pay_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID
        };
        set((state) => {
          const inv = state.invoices.find((i) => i.id === payData.invoiceId);
          if (!inv) return state;

          const newPaid = inv.paidAmount + payData.amount;
          const status: InvoiceStatus = newPaid >= inv.total ? 'Paid' : newPaid > 0 ? 'Partial' : 'Due';

          const updatedInvoices = state.invoices.map((i) =>
            i.id === payData.invoiceId ? { ...i, paidAmount: newPaid, status } : i
          );

          return {
            payments: [newPay, ...state.payments],
            invoices: updatedInvoices
          };
        });
        get().logAudit('RECORD_PAYMENT', 'invoice', payData.invoiceId, `Recorded payment of ₹${payData.amount} (${payData.mode})`);
      },

      documents: [],
      addDocument: (docData) => {
        const newDoc: PatientDocument = {
          ...docData,
          id: `doc_${Date.now()}`,
          clinicId: DEFAULT_CLINIC_ID,
          createdAt: new Date().toISOString()
        };
        set((state) => ({ documents: [newDoc, ...state.documents] }));
      },
      deleteDocument: (id) =>
        set((state) => ({ documents: state.documents.filter((d) => d.id !== id) })),

      runningCosts: INITIAL_RUNNING_COSTS,
      addRunningCost: (cost) =>
        set((state) => ({
          runningCosts: [...state.runningCosts, { ...cost, id: `rc_${Date.now()}` }]
        })),
      updateRunningCost: (id, cost) =>
        set((state) => ({
          runningCosts: state.runningCosts.map((c) => (c.id === id ? { ...c, ...cost } : c))
        })),
      deleteRunningCost: (id) =>
        set((state) => ({
          runningCosts: state.runningCosts.filter((c) => c.id !== id)
        })),

      recycleBin: [],
      restoreFromRecycleBin: (id) => {
        const item = get().recycleBin.find((r) => r.id === id);
        if (!item) return;

        set((state) => {
          const nextBin = state.recycleBin.filter((r) => r.id !== id);
          if (item.type === 'patients') {
            return { recycleBin: nextBin, patients: [item.data, ...state.patients] };
          }
          if (item.type === 'appointments') {
            return { recycleBin: nextBin, appointments: [item.data, ...state.appointments] };
          }
          if (item.type === 'invoices') {
            return { recycleBin: nextBin, invoices: [item.data, ...state.invoices] };
          }
          if (item.type === 'leads') {
            return { recycleBin: nextBin, leads: [item.data, ...state.leads] };
          }
          return { recycleBin: nextBin };
        });
      },
      permanentlyDeleteFromRecycleBin: (id) =>
        set((state) => ({
          recycleBin: state.recycleBin.filter((r) => r.id !== id)
        })),

      auditLogs: [
        {
          id: 'aud_1',
          clinicId: DEFAULT_CLINIC_ID,
          action: 'SYSTEM_INIT',
          entityType: 'patient',
          entityId: 'p_101',
          description: 'Aarogya CRM initialized with demo datasets',
          createdAt: '2026-07-26T12:00:00Z'
        }
      ],
      logAudit: (action, entityType, entityId, description) =>
        set((state) => ({
          auditLogs: [
            {
              id: `aud_${Date.now()}`,
              clinicId: DEFAULT_CLINIC_ID,
              action,
              entityType,
              entityId,
              description,
              createdAt: new Date().toISOString()
            },
            ...state.auditLogs
          ]
        }))
    }),
    {
      name: 'aarogya_crm_store_v1'
    }
  )
);
