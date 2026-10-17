# AV Suite CRM — Frontend Architecture and Redesign Plan

This document outlines the complete architectural and design strategy for rebuilding the AV Suite CRM frontend from scratch. It aims to deliver a modern, fast, medical/healthcare-focused Single Page Application (SPA) with minimal cognitive load, adopting premium design aesthetics and robust engineering practices.

## User Review Required
> [!IMPORTANT]
> Since we are starting completely from scratch and rebuilding the UI, please review the proposed Folder Structure, Tech Stack, and Information Architecture. This will be the foundation of the new app. Once approved, we will proceed with the step-by-step implementation roadmap.

## 1. Information Architecture (Single Tab Application)

The application operates as a unified Single Page Application (SPA). After the `/login` route, everything exists within a persistent application shell.

**Routes & Modules:**
*   `/login`: Authentication (Outside Shell)
*   `/` (Dashboard Shell):
    *   `/dashboard`: Key metrics, today's appointments, tasks, recent activity.
    *   `/patients`: Patient directory, search, add patient.
        *   `/patients/:id`: Patient Workspace (Header + Tabs: Timeline, Documents, Treatments, SOAP Notes, Assessments, Appointments, Billing).
    *   `/appointments`: Calendar view, scheduling, resource management.
    *   `/billing`: Invoices, payments, claims.
    *   `/settings`: Clinic settings, user management, roles, preferences.

## 2. Role-Based Access Control (RBAC)

The UI will enforce role-based visibility based on the JWT `role` claim (`admin`, `therapist`, `front_desk`). This is purely for UI rendering; the backend remains the source of truth (returning 403s on unauthorized access).

*   **Centralized Configuration**: All permission logic will reside in a single configuration file (e.g., `src/config/permissions.ts`) to align easily with backend updates and allow for adding future roles (like Manager) without rewriting components.
*   **Module Visibility**:
    *   **Admin**: Full access to all modules.
    *   **Therapist**: Dashboard, Patients, own Appointments, own Analytics. No access to Billing, Leads, Therapists, Recycle Bin, or Settings.
    *   **Front Desk**: Dashboard, Patients, Appointments, Billing, Leads. No access to Analytics, Therapists, Recycle Bin, or Settings.
*   **Action Permissions**: Granular action visibility (e.g., Front Desk cannot delete patients or create/sell packages, Therapists can only upload/download documents for their own patients).
*   **Implementation**: No 403 pages are needed as the SPA will simply hide restricted tabs and sidebar items.

## 3. Design System

*   **Color Palette**: Soft neutral backgrounds (e.g., slate/gray-50 to gray-900), accented by a refined primary color (e.g., deep healthcare blue or subtle teal). No heavy gradients.
*   **Typography**: Inter or similar highly legible modern sans-serif. Strict hierarchy emphasizing readability and data scanning.
*   **Spacing**: Generous whitespace. Adopting an 8px base grid system (similar to Notion/Linear).
*   **Radii**: Rounded corners (10–14px) for cards and modals.
*   **Borders & Shadows**: 1px thin borders for structure. Shadows restricted to elevated elements (modals, popovers, dropdowns). No large, diffuse shadows on standard cards.
*   **Iconography**: Lucide icons, consistent stroke widths.

## 4. Component Hierarchy

```text
AppRoot (Providers: Query, Theme, Zustand Store)
 └── AuthLayout (for /login)
 └── AppShell (for authenticated routes, wrapped with RBAC context)
      ├── SidebarNavigation (Collapsible, role-filtered active states)
      ├── CommandBar (Top search, Cmd+K palette)
      ├── MainContentArea (Dynamic content)
      │    └── Route Components (Dashboard, Patient Workspace, etc.)
      └── GlobalOverlays
           ├── ToastContainer
           ├── ModalManager (for forms, confirmations)
           └── SlideOverDrawer (Contextual edits)
```

## 5. Folder Structure (Next.js 14 App Router)

```text
src/
├── app/            # Next.js App Router pages and layouts
│   ├── (auth)/     # Authentication routes (login)
│   ├── (dashboard)/# Authenticated routes (shell)
│   ├── globals.css # Global styles
│   └── layout.tsx  # Root layout
├── components/     # Reusable UI components
│   ├── ui/         # shadcn/ui components (Button, Input, Table, etc.)
│   └── layout/     # AppShell, Sidebar, Topbar, PageWrapper
├── config/         # Centralized configuration (e.g., RBAC permissions)
├── features/       # Feature-based modules (Domain Driven Design)
├── hooks/          # Global custom hooks
├── lib/            # Utility functions, API client, Zod schemas
├── store/          # Global state (Zustand)
└── types/          # Global TypeScript interfaces
```

## 6. Screen-by-Screen Wireframe Descriptions

*   **Login**: Clean, centered card. Email/password or SSO. Minimalist branding.
*   **Dashboard**:
    *   Top: Welcome message, key KPI summary cards (Appointments today, pending tasks).
    *   Middle: Today's schedule (list view) and Recent Activity feed.
    *   Right: Contextual drawer for quick tasks (e.g., approve request).
*   **Patient Directory**:
    *   Header: Title + "Add Patient" button.
    *   Body: Virtualized DataTable. Search bar, filters (status, tags), column visibility toggles.
*   **Patient Workspace (includes Treatments, Assessments, Documents)**:
    *   Header (Sticky): Patient name, avatar, quick demographic info, primary actions (Book Appt, Add Note).
    *   Tabs: Timeline (default), Documents, Treatments, SOAP Notes, Assessments, Billing.
    *   **SOAP Notes/Assessments**: Structured forms, autosaving, progress history view.
    *   **Documents**: Drag-and-drop upload zone, list view with secure download actions.
*   **Leads Module**:
    *   Header: Title + "New Lead" button.
    *   Body: Kanban board layout (drag-and-drop) with columns (New, Contacted, Qualified, Converted). Clicking a lead opens a slide-over for updates/conversion.
*   **Appointments Module**:
    *   Header: Date picker, View toggles (Day/Week/Month/List).
    *   Body: Full calendar view. Filters (by Therapist, Status). Clicking an empty slot opens the "Create Appointment" slide-over. Clicking an existing appointment opens a contextual drawer for reschedule/status management.
*   **Billing Module**:
    *   Header: Tabs (Invoices, Payments, Packages).
    *   Body: DataTables for each tab. Invoice generation actions, package selling flows. Quick link to download Invoice PDFs.
*   **Analytics Module**:
    *   Body: Grid of charts and metrics (Clinic KPIs, Revenue, Appointments volume, Conversion metrics). Filterable by date range.
*   **Settings Module**:
    *   Sidebar (inner): Tabs for Clinic Settings, User Management, Audit Log.
    *   Body: Configuration forms based on the active tab.
*   **Public Booking (External)**:
    *   Clean, standalone clinic branding page.
    *   Multi-step appointment request form (Select Service -> Select Time -> Patient Details).
    *   Booking confirmation UI (Success state).

### Slide-over Forms
Slide-overs slide in from the right, divided into logical sections with a sticky bottom bar (Save/Cancel).
*   **Add/Edit Patient**: Demographics, Contact, Insurance.
*   **Create/Edit Lead**: Lead details, Source, Notes.
*   **Create/Reschedule Appointment**: Patient search, Service selection, Date/Time picker, Provider.
*   **Sell Package / Create Invoice**: Itemized list builder, discounts, total calculation.
*   **Record Payment**: Amount, Method (Card, Cash, Transfer), Reference ID.
*   **User Management**: Add user, Assign Role (Admin, Therapist, Front Desk).

## 7. Interaction Patterns

*   **Command Palette**: `Cmd/Ctrl + K` opens global search to jump to patients, settings, or actions.
*   **Instant Switching**: Routing pre-fetches data; layout does not remount.
*   **Optimistic Updates**: UI updates instantly when mutating data (e.g., checking a task), while the request processes in the background.
*   **Inline Editing**: For minor updates (e.g., patient phone number), click to edit directly rather than opening a full form.
*   **Slide-overs vs. Modals**: Slide-overs for complex forms (creating entities). Modals for confirmations or simple, single-input prompts.

## 8. Responsive Behavior

*   **Desktop First (First priority)**: Optimized for large screens with complex tables, Kanban boards, and dense data displays.
*   **Tablets/Small Screens**: Sidebar collapses to icons. Tables switch to card-based lists or horizontal scrolling. Slide-overs take up 100vw instead of a fixed width.
*   **Mobile (Second primary)**: Bottom navigation replaces the sidebar for core routes. Complex tasks (like full SOAP note authoring or detailed analytics) are simplified or encourage desktop use. Quick actions (like viewing today's schedule) are prioritized.

## 9. Reusable Component Inventory

Building upon `shadcn/ui`, we will maintain a strict inventory:
*   **Form Controls**: Input, Textarea, Select, Checkbox, RadioGroup, DatePicker (Calendar), Switch, Slider.
*   **Navigation**: Tabs, Breadcrumb, DropdownMenu, ContextMenu, Menubar.
*   **Data Display**: DataTable (TanStack), Card, Badge, Avatar, Tooltip, HoverCard, Accordion, ScrollArea (for virtualization).
*   **Feedback**: Skeleton (loading), Toast (notifications), Alert, Dialog (Modal), Sheet (Drawer/Slide-over).
*   **Action**: Button (Variants: Default, Outline, Ghost, Link, Destructive), Command (Menu).

## 10. State Management Strategy

*   **Server State (Primary)**: `TanStack Query` (React Query) for data fetching, caching, synchronization, and optimistic updates.
*   **Form State**: `React Hook Form` paired with `Zod` for validation.
*   **Local UI State**: `useState` and `useReducer`.
*   **Global Client State (Primary)**: `Zustand` will be used as the primary global state manager for things like Sidebar open/closed, current active theme, current user profile, and RBAC context.
*   **URL State**: Search params for filters, pagination, and active tabs so URLs are shareable.

## 11. Step-by-Step Implementation Roadmap

*   **Phase 1: Foundation (Days 1-2)**
    *   Initialize Next.js 14 project with TypeScript (strict) and Tailwind CSS.
    *   Set up centralized RBAC configuration based on the spec.
    *   Install and configure standard `shadcn/ui` core components.
    *   Set up App Router layouts (AuthLayout, AppShell).
*   **Phase 2: Core Layout & Navigation (Days 3-4)**
    *   Implement the Sidebar Navigation (collapsible).
    *   Implement the Top Command Bar and `Cmd+K` palette layout.
    *   Build out empty route shells (Dashboard, Patients, Appointments, Settings).
*   **Phase 3: Data Table & Infrastructure (Days 5-6)**
    *   Configure TanStack Query.
    *   Build the reusable `DataTable` component (with sorting, filtering, virtualization).
    *   Implement the initial Patient Directory view using mock data.
*   **Phase 4: The Patient Workspace (Days 7-9)**
    *   Build the Patient Profile Header.
    *   Implement Tabs for the workspace.
    *   Create the Slide-over (Sheet) component and integrate React Hook Form + Zod for adding/editing patients.
*   **Phase 5: Refinement & Advanced UX (Days 10-12)**
    *   Implement Toast notifications.
    *   Add Skeleton loaders for all async operations.
    *   Refine typography, spacing, and micro-animations.
    *   Conduct Accessibility (a11y) pass (keyboard nav, ARIA labels).

## Package Management

- Prefer existing project dependencies. Add new packages only when they provide substantial long-term value and have active maintenance.

## Engineering Standards

- Strict TypeScript only.
- No `any`.
- Feature-first architecture.
- No duplicated business logic.
- No duplicated UI components.
- Maximum component size: ~250 lines.
- Maximum custom hook: ~150 lines.
- Reusable components over copy-paste.
- Composition over inheritance.
- Absolute imports.
- ESLint + Prettier enforced.

## Performance Standards

- Lazy load feature modules.
- Route-level code splitting.
- Virtualize large tables.
- Memoize expensive computations.
- Skeleton loaders for async content.
- Minimize unnecessary re-renders.
- Optimize bundle size.
- Optimize Core Web Vitals.

## Design Tokens

- Color palette
- Typography scale
- Spacing scale
- Border radius
- Shadows
- Animation duration
- Breakpoints
- Z-index hierarchy

## UX Standards

Every screen must include:

- Loading state
- Empty state
- Error state
- Success feedback
- Search (where applicable)
- Filters (where applicable)
- Primary CTA
- Undo for destructive actions when feasible

## Micro Interactions

- Button hover
- Focus ring
- Sidebar collapse animation
- Drawer transition
- Skeleton loading
- Toast stacking
- Table row hover
- Card hover
- Success animations
- Error animations

## AI Implementation Rules

- Never invent backend APIs.
- Never invent database fields.
- Never hardcode permissions.
- Never duplicate components.
- Never duplicate business logic.
- Follow the RBAC matrix exactly.
- Build reusable, scalable code.
- Prefer configuration over hardcoding.
- Optimize maintainability over shortcuts.
- Keep dependencies minimal.

## Scalability

The architecture must allow:

- New roles without refactoring.
- New modules without changing AppShell.
- New permissions via configuration.
- Easy feature expansion.
- Independent feature ownership.

## Healthcare UX

- Optimize for long working hours.
- Large click targets.
- Fast patient switching.
- Autosave long forms.
- Never lose entered data.
- High information density without clutter.
- Prioritize speed over decorative visuals.

## Error Handling

- Human-readable error messages.
- Retry actions where appropriate.
- Offline-friendly UI states.
- Global error boundary.
- Consistent API error handling.

## Frontend Security

- Sanitize user input.
- Never expose sensitive data.
- Respect RBAC visibility.
- Handle expired JWT gracefully.
- Centralized auth handling.

## Non Goals

- Do not redesign business workflows.
- Do not invent backend endpoints.
- Do not add unnecessary animations.
- Do not introduce heavy UI libraries.
- Do not duplicate business logic.
- Do not optimize prematurely.

## Testing Strategy

- Unit tests
- Component tests
- Integration tests
- Accessibility testing
- End-to-end testing
