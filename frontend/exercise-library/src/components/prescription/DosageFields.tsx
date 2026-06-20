import React from "react";
import { PrescriptionItem } from "@/types/exercise";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface DosageFieldsProps {
  item: PrescriptionItem;
  onChange: (updatedItem: PrescriptionItem) => void;
}

export function DosageFields({ item, onChange }: DosageFieldsProps) {
  const updateField = (field: keyof PrescriptionItem, value: any) => {
    onChange({ ...item, [field]: value });
  };

  // Clamps numeric dosage fields to clinically sensible ranges. Browser `min`
  // attributes alone don't block typed/pasted negative numbers, so we enforce
  // bounds here too.
  const updateNumericField = (
    field: "sets" | "reps" | "hold",
    rawValue: string,
    min: number,
    max: number
  ) => {
    const parsed = parseInt(rawValue, 10);
    if (isNaN(parsed)) {
      updateField(field, min);
      return;
    }
    const clamped = Math.min(Math.max(parsed, min), max);
    updateField(field, clamped);
  };

  return (
    <div className="flex flex-col gap-3 mt-3">
      <div className="grid grid-cols-4 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Sets</Label>
          <Input
            type="number"
            min={1}
            max={20}
            value={item.sets}
            onChange={(e) => updateNumericField("sets", e.target.value, 1, 20)}
            className="h-8 text-sm shadow-sm"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Reps</Label>
          <Input
            type="number"
            min={1}
            max={200}
            value={item.reps}
            onChange={(e) => updateNumericField("reps", e.target.value, 1, 200)}
            className="h-8 text-sm shadow-sm"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Hold (s)</Label>
          <Input
            type="number"
            min={0}
            max={600}
            value={item.hold}
            onChange={(e) => updateNumericField("hold", e.target.value, 0, 600)}
            className="h-8 text-sm shadow-sm"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Frequency</Label>
          <Select
            value={item.frequency}
            onValueChange={(val) => updateField("frequency", val)}
          >
            <SelectTrigger className="h-8 text-sm px-2 shadow-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Once daily">Once daily</SelectItem>
              <SelectItem value="Twice daily">Twice daily</SelectItem>
              <SelectItem value="3 times daily">3 times daily</SelectItem>
              <SelectItem value="Every other day">Every other day</SelectItem>
              <SelectItem value="As needed">As needed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Exercise Notes / Specifics</Label>
        <Input
          type="text"
          placeholder="e.g. Keep shoulder blade down, stop if pain occurs..."
          value={item.note || ""}
          onChange={(e) => updateField("note", e.target.value)}
          className="h-8 text-xs shadow-sm bg-muted/20"
        />
      </div>
    </div>

  );
}
