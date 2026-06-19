import React from "react";
import { PrescriptionItem } from "@/types/exercise";
import { Button } from "@/components/ui/button";
import { Printer, ArrowLeft, Activity } from "lucide-react";

interface A4PrintViewProps {
  prescription: PrescriptionItem[];
  onBack: () => void;
}

export function A4PrintView({ prescription, onBack }: A4PrintViewProps) {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-muted/20 pb-12">
      {/* Non-printable top bar */}
      <div className="print:hidden sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b px-6 py-4 flex justify-between items-center shadow-sm">
        <Button variant="ghost" onClick={onBack} className="hover:bg-muted">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Builder
        </Button>
        <Button onClick={handlePrint} className="shadow-md">
          <Printer className="mr-2 h-4 w-4" />
          Print Prescription
        </Button>
      </div>

      {/* Printable A4 Page Area */}
      <div className="max-w-[210mm] mx-auto bg-white min-h-[297mm] mt-8 p-12 shadow-xl print:shadow-none print:m-0 print:p-0 print:w-full print:max-w-none text-slate-900">
        
        {/* Header */}
        <div className="flex justify-between items-end border-b-2 border-slate-200 pb-6 mb-8">
          <div>
            <div className="flex items-center gap-2 font-bold text-2xl text-slate-900 mb-1">
              <Activity className="h-8 w-8 text-blue-600" />
              <span>AarogyaVirohan Clinic</span>
            </div>
            <p className="text-slate-500 text-sm">Physical Therapy & Rehabilitation</p>
          </div>
          <div className="text-right text-sm">
            <p className="font-semibold text-slate-700">Date: {new Date().toLocaleDateString()}</p>
            <div className="flex items-center justify-end text-slate-500 mt-1 gap-2">
              <label htmlFor="patientName">Patient Name:</label>
              <input
                id="patientName"
                type="text"
                placeholder="Enter name"
                className="border-b border-slate-300 border-dashed bg-transparent focus:outline-none focus:border-blue-500 focus:border-solid px-1 py-0.5 w-48 text-slate-800 font-medium print:border-none print:p-0 placeholder:text-slate-300 print:placeholder:text-transparent"
              />
            </div>
          </div>
        </div>

        <h1 className="text-xl font-bold mb-6 text-slate-800">Your Home Exercise Program</h1>

        {/* Exercises List */}
        <div className="space-y-8">
          {prescription.map((item, index) => (
            <div key={item.exercise.id} className="border border-slate-200 rounded-lg p-5 break-inside-avoid">
              <div className="flex justify-between items-start mb-4">
                <div className="flex gap-3 items-center">
                  <div className="bg-blue-100 text-blue-700 font-bold h-8 w-8 rounded-full flex items-center justify-center shrink-0">
                    {index + 1}
                  </div>
                  <h2 className="text-lg font-bold text-slate-900">{item.exercise.name}</h2>
                </div>
                <div className="flex gap-4 text-sm font-semibold bg-slate-50 px-4 py-2 rounded-md border border-slate-100">
                  <div className="flex flex-col"><span className="text-slate-500 text-[10px] uppercase">Sets</span><span>{item.sets}</span></div>
                  <div className="flex flex-col"><span className="text-slate-500 text-[10px] uppercase">Reps</span><span>{item.reps}</span></div>
                  <div className="flex flex-col"><span className="text-slate-500 text-[10px] uppercase">Hold</span><span>{item.hold}s</span></div>
                  <div className="flex flex-col"><span className="text-slate-500 text-[10px] uppercase">Frequency</span><span>{item.frequency}</span></div>
                </div>
              </div>
              <div className="pl-11">
                <p className="text-slate-700 leading-relaxed text-sm">
                  {item.exercise.instructions}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-16 pt-6 border-t border-slate-200 text-center text-sm text-slate-500">
          <p>If you experience sharp pain during any exercise, stop immediately and contact your therapist.</p>
        </div>
      </div>
    </div>
  );
}
