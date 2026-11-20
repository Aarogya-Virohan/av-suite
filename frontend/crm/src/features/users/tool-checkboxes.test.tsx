import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ToolCheckboxes } from './components/ToolCheckboxes';

const box = (key: string) => document.getElementById(`tool-${key}`) as HTMLInputElement;

describe('ToolCheckboxes (CRM-6)', () => {
  afterEach(cleanup);
  it('shows the 3 tools in contract order and toggles one', () => {
    const onChange = vi.fn();
    render(<ToolCheckboxes value={['posture-tool']} onChange={onChange} role="therapist" />);
    const boxes = screen.getAllByRole('checkbox');
    expect(boxes).toHaveLength(3);
    expect(boxes.map((b) => b.id)).toEqual(['tool-psycho-social-screening', 'tool-exercise-library', 'tool-posture-tool']);
    expect(box('psycho-social-screening').checked).toBe(false);
    expect(box('posture-tool').checked).toBe(true);
    fireEvent.click(box('exercise-library'));
    expect(onChange).toHaveBeenCalledWith(['posture-tool', 'exercise-library']);
  });
  it('disables a tool that is not in the plan', () => {
    render(<ToolCheckboxes value={[]} onChange={() => {}} role="therapist" available={{ 'posture-tool': false }} />);
    expect(box('posture-tool').disabled).toBe(true);
    expect(screen.getByText('Not in your plan')).toBeTruthy();
  });
  it('marks Psychosocial as assign only for front desk', () => {
    render(<ToolCheckboxes value={[]} onChange={() => {}} role="front_desk" />);
    expect(screen.getByText('(assign only)')).toBeTruthy();
    expect(screen.getByText(/Cannot see the answers/)).toBeTruthy();
  });
});
