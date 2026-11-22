'use client';

import React from 'react';
import { cn } from '../../../lib/cn';
import { TOOL_KEYS, type ToolKey, type ToolState, toolHint, toolLabel } from '../tools';

interface Props {
  value: ToolKey[];
  onChange: (next: ToolKey[]) => void;
  /** Clinic plan. A tool marked false is shown disabled. Unknown = allowed (server checks). */
  available?: ToolState;
  labels?: Partial<Record<ToolKey, string>>;
  role: string | null | undefined;
  disabled?: boolean;
}

/** The 3 tool checkboxes (BE-1). Order is fixed: Psychosocial, Exercise Library, Posture. */
export function ToolCheckboxes({ value, onChange, available, labels, role, disabled }: Props) {
  return (
    <fieldset className="space-y-2" disabled={disabled}>
      <legend className="mb-1.5 text-[13px] font-semibold text-ink-2">Tool access</legend>
      {TOOL_KEYS.map((key) => {
        const inPlan = available?.[key] !== false;
        const checked = value.includes(key);
        const id = `tool-${key}`;
        return (
          <label
            key={key}
            htmlFor={id}
            className={cn(
              'flex items-start gap-3 rounded-xl border border-line bg-canvas p-3',
              inPlan && !disabled ? 'cursor-pointer' : 'cursor-not-allowed opacity-60',
            )}
          >
            <input
              id={id}
              type="checkbox"
              checked={checked && inPlan}
              disabled={!inPlan || disabled}
              onChange={(e) => onChange(e.target.checked ? [...value, key] : value.filter((k) => k !== key))}
              className="mt-0.5 h-4 w-4 accent-grove"
            />
            <span className="text-sm">
              <span className="font-semibold text-ink">
                {toolLabel(key, labels)}
                {key === 'psycho-social-screening' && role === 'front_desk' && (
                  <span className="ml-1.5 text-xs font-medium text-muted">(assign only)</span>
                )}
              </span>
              <span className="block text-xs text-muted">{inPlan ? toolHint(key, role) : 'Not in your plan'}</span>
            </span>
          </label>
        );
      })}
    </fieldset>
  );
}
