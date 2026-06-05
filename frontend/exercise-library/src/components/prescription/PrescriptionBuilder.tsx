import React from "react";
import { PrescriptionItem } from "@/types/exercise";
import { ExerciseRow } from "./ExerciseRow";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileText, ClipboardList } from "lucide-react";

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
  return (
    <div className="flex flex-col flex-1 relative min-h-0">
      <div className="mb-4 flex items-center justify-between shrink-0">
        <h2 className="font-bold text-lg flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-primary" />
          Prescription
        </h2>
        <span className="text-sm font-medium bg-primary/10 text-primary px-2.5 py-0.5 rounded-full">
          {prescription.length} items
        </span>
      </div>

      {prescription.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 border-2 border-dashed rounded-xl bg-muted/30">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4 text-primary">
            <ClipboardList className="h-6 w-6" />
          </div>
          <h3 className="font-semibold text-base mb-1">No exercises added yet</h3>
          <p className="text-sm text-muted-foreground max-w-[250px]">
            Browse the library on the left and click "+ Add" to build a prescription.
          </p>
        </div>
      ) : (
        <>
          <ScrollArea className="flex-1 pr-4 -mr-4 min-h-0">
            <div className="pb-20">
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
          
          <div className="absolute bottom-0 left-0 right-0 pt-4 pb-2 bg-gradient-to-t from-background via-background to-transparent shrink-0">
            <Button
              onClick={onGenerateReport}
              className="w-full shadow-lg shadow-primary/20 transition-all hover:shadow-primary/30 active:scale-[0.98] font-semibold h-11"
            >
              <FileText className="mr-2 h-4 w-4" />
              Generate Report
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
