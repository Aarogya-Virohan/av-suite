'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import type { ScreeningData } from '@/lib/types';
import { Button, Card, CardHeader, FieldLabel, inputClass } from '@/components/ui/brand';
import { SlideOver } from '@/components/ui/SlideOver';

const CONFIRM_WORD = 'DELETE';

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

/** "a, b and c" */
function listWords(items: string[]) {
  return items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

/**
 * Deletion on request (SRS 3.2). Shown only to holders of screening.delete,
 * which by default is the clinic admin. Shows counts, never results.
 */
export function DeleteDataPanel({ patientId, patientName }: { patientId: string; patientName: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState('');

  const data = useQuery({
    queryKey: ['screening-data', patientId],
    queryFn: () => api.get<ScreeningData>(`/patients/${patientId}/psychosocial/data`),
  });

  const remove = useMutation({
    mutationFn: () =>
      api.post<ScreeningData>(`/patients/${patientId}/psychosocial/data/delete`, { confirm: CONFIRM_WORD }),
    onSuccess: () => {
      toast.success(`Screening data for ${patientName} has been deleted.`);
      setOpen(false);
      setTyped('');
      for (const key of ['screening-data', 'assignments', 'summary', 'patient-referrals', 'trend']) {
        qc.invalidateQueries({ queryKey: [key, patientId] });
      }
      qc.invalidateQueries({ queryKey: ['worklist'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const close = () => {
    if (remove.isPending) return;
    setOpen(false);
    setTyped('');
  };

  const d = data.data;
  const empty = d
    ? d.links === 0 && d.screeners === 0 && d.referral_actions === 0 && d.schedules === 0 && d.consent_records === 0
    : true;

  return (
    <Card className="p-5">
      <CardHeader title="Delete screening data" />
      {data.isPending ? (
        <Loader2 className="h-5 w-5 animate-spin text-grove" aria-label="Loading" />
      ) : data.isError ? (
        <p className="text-sm text-danger">{data.error.message}</p>
      ) : empty ? (
        <p className="text-sm text-ink-2">There is no screening data to delete for this patient.</p>
      ) : (
        <div className="space-y-3 text-sm text-ink-2">
          <p>
            Use this when the patient asks the clinic to delete their screening answers. On file:{' '}
            {listWords([
              plural(d!.screeners, 'questionnaire', 'questionnaires'),
              plural(d!.links, 'link', 'links'),
              plural(d!.referral_actions, 'referral note', 'referral notes'),
              ...(d!.schedules > 0 ? [plural(d!.schedules, 'repeat schedule', 'repeat schedules')] : []),
              plural(d!.consent_records, 'consent record', 'consent records'),
            ])}
            .
          </p>
          <Button
            variant="secondary"
            className="border-danger/60 text-danger hover:border-danger hover:bg-danger-wash"
            onClick={() => setOpen(true)}
          >
            <Trash2 className="h-4 w-4" />
            Delete screening data
          </Button>
        </div>
      )}

      <SlideOver isOpen={open} onClose={close} title="Delete screening data" subtitle={patientName}>
        {d ? (
          <form
            className="space-y-5 text-sm text-ink-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (typed === CONFIRM_WORD) remove.mutate();
            }}
          >
            <div className="rounded-xl border border-danger/40 bg-danger-wash p-4 text-ink">
              <p className="font-semibold">This cannot be undone.</p>
              <p className="mt-1 text-ink-2">
                Every screening record for this patient is removed for good, including results the physiotherapist
                has already reviewed.
              </p>
            </div>
            <div>
              <p className="font-semibold text-ink">What will be deleted</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>{plural(d.screeners, 'questionnaire', 'questionnaires')} with all answers and results</li>
                <li>{plural(d.links, 'patient link', 'patient links')}. Any open link stops working.</li>
                <li>{plural(d.referral_actions, 'referral note', 'referral notes')}</li>
                {d.schedules > 0 ? <li>{plural(d.schedules, 'repeat schedule', 'repeat schedules')}</li> : null}
                <li>{plural(d.consent_records, 'consent record', 'consent records')}</li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-ink">What stays</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {d.withdrawal_on_file ? (
                  <li>
                    The patient&apos;s withdrawal of consent, with its date. No new questionnaire can be sent to
                    them.
                  </li>
                ) : null}
                <li>The patient&apos;s profile in the clinic. Only screening data is deleted.</li>
                <li>A note in the audit log that the data was deleted, by whom and when. It holds counts only.</li>
              </ul>
            </div>
            <div>
              <FieldLabel htmlFor="confirm-delete">Type {CONFIRM_WORD} to confirm</FieldLabel>
              <input
                id="confirm-delete"
                className={inputClass}
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
              />
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <Button type="button" variant="ghost" onClick={close} disabled={remove.isPending}>
                Keep data
              </Button>
              <Button
                type="submit"
                variant="secondary"
                className="border-danger bg-danger text-white hover:border-danger hover:bg-danger/90"
                disabled={typed !== CONFIRM_WORD || remove.isPending}
              >
                {remove.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Delete for good
              </Button>
            </div>
          </form>
        ) : null}
      </SlideOver>
    </Card>
  );
}
