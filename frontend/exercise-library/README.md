# AarogyaVirohan Exercise Library

The Exercise Library UI is a two-panel prescription builder frontend designed for physical therapists. It allows therapists to seamlessly browse a library of exercises, add them to a patient's prescription, adjust dosages (sets, reps, hold time, and frequency), and generate a print-ready A4 report.

## Features Completed

- **Two-Panel Layout**: A beautiful split-screen design separating the exercise library from the prescription builder.
- **Search & Filter**: 
  - Dynamic text search to find exercises by name or condition.
  - Interactive "Filter Chips" to filter exercises by body part (e.g., Neck, Upper Back, Knee).
- **Exercise Selection**: Add exercises directly from the library to the prescription list. The library cards reflect their "Added ✓" state instantly to prevent duplicates.
- **Dosage Customization**: Adjust sets, reps, hold time, and frequency independently for each added exercise using intuitive inputs and dropdowns.
- **Printable A4 Report**: Generates a clean, print-ready document formatted precisely for an A4 page (`210mm x 297mm`), stripping away non-essential UI elements like search bars and buttons.
- **Modern Aesthetics**: Built with a sleek, vibrant, and highly interactive design system utilizing micro-animations, clean borders, and bold typography.

## Tech Stack

- **Framework**: [Next.js 14+ (App Router)](https://nextjs.org/)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/)
- **Icons**: Lucide React

## Getting Started

### Prerequisites

Make sure you have [Node.js](https://nodejs.org/) installed on your machine (v18 or higher recommended).

### Installation

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/tarun1sisodia/AarogyaVirohan.git
   cd AarogyaVirohan/exercise-library
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   ```

4. **Open the app**:
   Open [http://localhost:3000](http://localhost:3000) in your browser to view the application.

## How to Use the UI

1. **Browse Exercises**: Look through the available exercises in the left panel. Use the search bar or body-part filter chips to find what you need.
2. **Add to Prescription**: Click the `+ Add` button on an exercise card to add it to the right panel.
3. **Adjust Dosages**: In the right panel, you can freely modify the Sets, Reps, Hold (seconds), and Frequency for the patient's specific needs.
4. **Remove Exercises**: Click the `X` button on any exercise row in the right panel to remove it from the prescription.
5. **Generate Report**: Once the prescription is ready, click the **Generate Report** button at the bottom of the right panel.
6. **Print**: You will be taken to a clean A4 preview. Click **Print Prescription** to open your browser's print dialog. You can print to a physical printer or save the document as a PDF.

## Project Structure

- `src/app/page.tsx`: Main page orchestrating the layout and state.
- `src/components/layout/`: Global layout components (`Header.tsx`, `SplitLayout.tsx`).
- `src/components/library/`: Left panel components for browsing exercises.
- `src/components/prescription/`: Right panel components for building the prescription.
- `src/components/report/`: Print-ready A4 view component.
- `src/data/exercises.json`: Mock data powering the library.
- `src/types/exercise.ts`: TypeScript interfaces.
