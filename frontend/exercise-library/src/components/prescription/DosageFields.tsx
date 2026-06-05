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

  return (
    <div className="grid grid-cols-4 gap-3 mt-3">
      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Sets</Label>
        <Input
          type="number"
          min={1}
          value={item.sets}
          onChange={(e) => updateField("sets", parseInt(e.target.value) || 0)}
          className="h-8 text-sm shadow-sm"
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Reps</Label>
        <Input
          type="number"
          min={1}
          value={item.reps}
          onChange={(e) => updateField("reps", parseInt(e.target.value) || 0)}
          className="h-8 text-sm shadow-sm"
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Hold (s)</Label>
        <Input
          type="number"
          min={0}
          value={item.hold}
          onChange={(e) => updateField("hold", parseInt(e.target.value) || 0)}
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
  );
}
