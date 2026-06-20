

import React, { useState, useEffect, useRef } from "react";
import { PrescriptionItem } from "@/types/exercise";
import { ExerciseRow } from "./ExerciseRow";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ClipboardList, FileText, Plus, Save, Loader2, Printer } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  fetchPatients,
  createPatient,
  createPrescription,
  generatePrescriptionPDF,
  updatePrescription,
} from "@/lib/api";

interface PrescriptionBuilderProps {
  prescription: PrescriptionItem[];
  onChange: (item: PrescriptionItem) => void;
  onRemove: (id: string) => void;
  onGenerateReport: () => void;
}

export function PrescriptionBuilder({
  prescription,
  onChange,
  onRemove,
  onGenerateReport,
}: PrescriptionBuilderProps) {
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [isPrinting, setIsPrinting] = useState(false);
  const [savedPrescriptionId, setSavedPrescriptionId] = useState<string | null>(null);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(true);

  // Tracks the live blob URL so we can revoke it before creating a new one —
  // generatePrescriptionPDF() creates a fresh object URL each call, and without
  // revoking the previous one, repeated edit -> print cycles leak memory.
  const generatedPdfUrlRef = useRef<string | null>(null);
  const setPdfUrl = (url: string | null) => {
    if (generatedPdfUrlRef.current) {
      URL.revokeObjectURL(generatedPdfUrlRef.current);
    }
    generatedPdfUrlRef.current = url;
    setGeneratedPdfUrl(url);
  };

  // Patient Modal / Inline Create Form state
  const [showAddPatient, setShowAddPatient] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [isCreatingPatient, setIsCreatingPatient] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load patients on mount
  useEffect(() => {
    loadPatients();
  }, []);

  async function loadPatients(autoSelectId?: string) {
    try {
      const data = await fetchPatients();
      setPatients(data);
      if (autoSelectId) {
        setSelectedPatientId(autoSelectId);
      }
      // Intentionally NOT auto-selecting the first patient on initial load.
      // Auto-selecting risked silently prescribing exercises to the wrong patient.
    } catch (err) {
      console.error("Failed to fetch patients", err);
    }
  }

  const handleCreatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName || !lastName) {
      setError("First and Last name are required");
      return;
    }
    setError(null);
    setIsCreatingPatient(true);
    try {
      const newPatient = await createPatient({
        first_name: firstName,
        last_name: lastName,
        phone: phone || undefined,
        date_of_birth: dateOfBirth || undefined,
      });
      setFirstName("");
      setLastName("");
      setPhone("");
      setDateOfBirth("");
      setShowAddPatient(false);
      await loadPatients(newPatient.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to register patient");
    } finally {
      setIsCreatingPatient(false);
    }
  };

  const handleSavePrescription = async () => {
    if (!selectedPatientId) {
      alert("Please select a patient first.");
      return;
    }
    if (prescription.length === 0) {
      alert("Please add at least one exercise to prescribe.");
      return;
    }

    setIsSaving(true);
    try {
      const itemsPayload = prescription.map((item) => ({
        exercise_id: item.exercise.id,
        sets: item.sets,
        reps: item.reps,
        hold: item.hold,
        frequency: item.frequency,
        note: item.note,
      }));

      if (savedPrescriptionId) {
        // Edit existing prescription
        await updatePrescription(savedPrescriptionId, {
          items: itemsPayload
        });
        setHasUnsavedChanges(false);
        alert("Exercise Prescription updated successfully in the database!");
      } else {
        // Create new prescription
        const payload = {
          patient_id: selectedPatientId,
          physio_notes: "Please follow sets and reps instructions carefully. Reach out if you feel acute discomfort.",
          status: "active",
          items: itemsPayload,
        };
        const result = await createPrescription(payload);
        setSavedPrescriptionId(result.id);
        setHasUnsavedChanges(false);
        alert("Exercise Prescription saved successfully in the database!");
      }
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Failed to save prescription.");
    } finally {
      setIsSaving(false);
    }
  };

  const handlePrintPDF = async () => {
    if (!selectedPatientId) {
      alert("Please select a patient first.");
      return;
    }
    if (prescription.length === 0) {
      alert("Please add at least one exercise.");
      return;
    }

    setIsPrinting(true);
    let targetId = savedPrescriptionId;
    try {
      const itemsPayload = prescription.map((item) => ({
        exercise_id: item.exercise.id,
        sets: item.sets,
        reps: item.reps,
        hold: item.hold,
        frequency: item.frequency,
        note: item.note,
      }));

      if (targetId) {
        // Update existing prescription before printing
        await updatePrescription(targetId, {
          items: itemsPayload
        });
      } else {
        // Create new prescription
        const payload = {
          patient_id: selectedPatientId,
          physio_notes: "Please follow sets and reps instructions carefully. Reach out if you feel acute discomfort.",
          items: itemsPayload,
        };
        const result = await createPrescription(payload);
        targetId = result.id;
        setSavedPrescriptionId(targetId);
      }

      setHasUnsavedChanges(false);

      // Generate PDF
      const pdfUrl = await generatePrescriptionPDF(targetId!);
      setPdfUrl(pdfUrl);
      
      // Attempt to open in a new tab (might get blocked by browser popup blocker)
      try {
        window.open(pdfUrl, "_blank");
      } catch (err) {
        console.error("Popup blocker prevented auto-opening the PDF.", err);
      }
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Failed to generate PDF report.");
    } finally {
      setIsPrinting(false);
    }
  };

  // Reset prescription status and PDF URL when selected patient changes
  useEffect(() => {
    setSavedPrescriptionId(null);
    setPdfUrl(null);
  }, [selectedPatientId]);

  // Revoke any live blob URL when the component unmounts
  useEffect(() => {
    return () => {
      if (generatedPdfUrlRef.current) {
        URL.revokeObjectURL(generatedPdfUrlRef.current);
      }
    };
  }, []);

  // Reset PDF URL and mark unsaved when prescription items list changes
  useEffect(() => {
    setPdfUrl(null);
    setHasUnsavedChanges(true);
  }, [prescription]);

  return (
    <div className="flex flex-col flex-1 relative min-h-0">
      {/* Header section */}
      <div className="mb-4 flex items-center justify-between shrink-0">
        <h2 className="font-bold text-lg flex items-center gap-2 text-foreground">
          <ClipboardList className="h-5 w-5 text-primary" />
          Rehab Prescriber
        </h2>
        <span className="text-xs font-semibold bg-primary/10 text-primary px-2.5 py-0.5 rounded-full">
          {prescription.length} items
        </span>
      </div>

      {/* Patient Section */}
      <div className="mb-4 p-3 bg-muted/30 border rounded-xl flex flex-col gap-2 shrink-0">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Select a Patient</Label>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAddPatient(!showAddPatient)}
            className="h-7 text-xs font-bold text-primary hover:text-primary/90 hover:bg-primary/5 flex items-center gap-1 px-2"
          >
            <Plus className="h-3.5 w-3.5" />
            Add New Patient 
          </Button>
        </div>

        {showAddPatient ? (
          <form onSubmit={handleCreatePatient} className="border-t pt-3 mt-1 flex flex-col gap-2.5">
            <h4 className="text-xs font-bold text-foreground">Register New Patient</h4>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex flex-col gap-1">
                <Label className="text-[10px] text-muted-foreground">First Name</Label>
                <Input
                  className="h-8 text-xs"
                  placeholder="e.g. John"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                />
              </div>
              <div className="flex flex-col gap-1">
                <Label className="text-[10px] text-muted-foreground">Last Name</Label>
                <Input
                  className="h-8 text-xs"
                  placeholder="e.g. Doe"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-[10px] text-muted-foreground">Phone Number</Label>
              <Input
                className="h-8 text-xs"
                placeholder="e.g. 9876543210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-[10px] text-muted-foreground">Date of Birth</Label>
              <Input
                type="date"
                className="h-8 text-xs"
                value={dateOfBirth}
                onChange={(e) => setDateOfBirth(e.target.value)}
              />
            </div>
            {error && <span className="text-[10px] text-destructive font-medium">{error}</span>}
            <div className="flex justify-end gap-2 mt-1">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowAddPatient(false)}
                className="h-7 text-xs"
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" className="h-7 text-xs" disabled={isCreatingPatient}>
                {isCreatingPatient && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                Add Patient
              </Button>
            </div>
          </form>
        ) : (
          <Select value={selectedPatientId} onValueChange={(val) => setSelectedPatientId(val || "")}>
            <SelectTrigger className="h-9 w-full shadow-sm text-sm">
              <SelectValue placeholder="Select patient...">
                {selectedPatientId && patients.length > 0 ? (
                  (() => {
                    const selectedPatient = patients.find((p) => p.id === selectedPatientId);
                    return selectedPatient
                      ? `${selectedPatient.first_name} ${selectedPatient.last_name}`
                      : undefined;
                  })()
                ) : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {patients.map((pat) => (
                <SelectItem key={pat.id} value={pat.id}>
                  {pat.first_name} {pat.last_name} {pat.phone ? `(${pat.phone})` : ""}
                </SelectItem>
              ))}
              {patients.length === 0 && (
                <div className="p-2 text-xs text-muted-foreground text-center">No patients found</div>
              )}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Exercises Prescribed list */}
      {prescription.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 border-2 border-dashed rounded-xl bg-muted/20">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4 text-primary">
            <ClipboardList className="h-6 w-6" />
          </div>
          <h3 className="font-semibold text-base mb-1">Prescription panel is empty</h3>
          <p className="text-sm text-muted-foreground max-w-[250px]">
            Select items from the library on the left and define dosage instructions.
          </p>
        </div>
      ) : (
        <>
          <ScrollArea className="flex-1 pr-4 -mr-4 min-h-0">
            <div className="pb-28">
              {prescription.map((item) => (
                <ExerciseRow
                  key={item.exercise.id}
                  item={item}
                  onChange={onChange}
                  onRemove={onRemove}
                />
              ))}
            </div>
          </ScrollArea>
          
          {/* Action buttons (Save & Print) */}
          <div className="absolute bottom-0 left-0 right-0 pt-4 pb-2 bg-gradient-to-t from-background via-background to-transparent shrink-0 flex gap-2">
            <Button
              variant="outline"
              onClick={handleSavePrescription}
              disabled={isSaving}
              className="flex-1 shadow-sm font-semibold h-11 border-primary/30 hover:bg-primary/5 active:scale-[0.98]"
            >
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin text-primary" />
              ) : (
                <Save className="mr-2 h-4 w-4 text-primary" />
              )}
              {savedPrescriptionId && !hasUnsavedChanges ? "Saved" : "Save Plan"}
            </Button>
            {generatedPdfUrl ? (
              <a
                href={generatedPdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-emerald-600/20 hover:shadow-emerald-600/30 transition-all active:scale-[0.98]"
              >
                <FileText className="mr-2 h-4 w-4" />
                Open / Save PDF
              </a>
            ) : (
              <Button
                onClick={handlePrintPDF}
                disabled={isPrinting}
                className="flex-1 shadow-lg shadow-primary/20 transition-all hover:shadow-primary/30 active:scale-[0.98] font-semibold h-11"
              >
                {isPrinting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Printer className="mr-2 h-4 w-4" />
                )}
                Print PDF
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

