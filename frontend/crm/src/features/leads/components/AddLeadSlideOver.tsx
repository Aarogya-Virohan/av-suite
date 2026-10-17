'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { SlideOver } from '../../../components/ui/SlideOver';
import { leadFormSchema, LeadFormValues } from '../../../lib/schemas';
import { useCreateLead } from '../api';
import { Button, FieldLabel, inputClass } from '../../../components/ui/brand';
import { cn } from '../../../lib/cn';

interface AddLeadSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
}

const errorText = 'mt-1.5 text-xs font-medium text-danger';

const EMPTY: LeadFormValues = { name: '', phone: '', email: '', source: '', stage: 'new', notes: '' };

/*
 * Fixes:
 * - Source defaulted to "website", so skipped leads were counted as website
 *   leads. It now starts as "Not specified" and is sent as null.
 * - "Converted" is not offered at creation: it produced a converted lead with
 *   no patient record and no Convert action. Conversion happens from the list.
 * - Blank email is sent as null; backend messages are shown on failure.
 */
export function AddLeadSlideOver({ isOpen, onClose }: AddLeadSlideOverProps) {
  const createLead = useCreateLead();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadFormSchema),
    defaultValues: EMPTY,
  });

  React.useEffect(() => {
    if (isOpen) reset(EMPTY);
  }, [isOpen, reset]);

  const onSubmit = async (values: LeadFormValues) => {
    try {
      await createLead.mutateAsync({
        ...values,
        name: values.name.trim(),
        phone: values.phone.trim(),
        email: values.email?.trim() ? values.email.trim() : null,
        source: values.source ? values.source : null,
      });
      toast.success(`Lead ${values.name.trim()} created successfully`);
      onClose();
    } catch (err: any) {
      console.error(err);
      toast.error(err?.message || 'Failed to create lead');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Add New Lead" subtitle="Capture prospective patient details">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <div>
          <FieldLabel htmlFor="lead-name">Lead Name *</FieldLabel>
          <input id="lead-name" {...register('name')} type="text" placeholder="Amit Patel" className={cn(inputClass, errors.name && 'border-danger')} />
          {errors.name && <p className={errorText}>{errors.name.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="lead-phone">Phone Number *</FieldLabel>
            <input id="lead-phone" {...register('phone')} type="tel" placeholder="10-digit mobile" className={cn(inputClass, errors.phone && 'border-danger')} />
            {errors.phone && <p className={errorText}>{errors.phone.message}</p>}
          </div>
          <div>
            <FieldLabel htmlFor="lead-email">Email Address</FieldLabel>
            <input id="lead-email" {...register('email')} type="email" placeholder="name@example.com" className={cn(inputClass, errors.email && 'border-danger')} />
            {errors.email && <p className={errorText}>{errors.email.message}</p>}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="lead-source">Source</FieldLabel>
            <select id="lead-source" {...register('source')} className={inputClass}>
              <option value="">Not specified</option>
              <option value="website">Website</option>
              <option value="referral">Referral</option>
              <option value="social_media">Social Media</option>
              <option value="walk_in">Walk-in</option>
              <option value="advertisement">Advertisement</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <FieldLabel htmlFor="lead-stage">Stage *</FieldLabel>
            <select id="lead-stage" {...register('stage')} className={inputClass}>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="qualified">Qualified</option>
              <option value="lost">Lost</option>
            </select>
          </div>
        </div>

        <div>
          <FieldLabel htmlFor="lead-notes">Notes</FieldLabel>
          <textarea id="lead-notes" {...register('notes')} rows={3} placeholder="Details about the enquiry..." className={cn(inputClass, 'h-auto py-2')} />
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createLead.isPending}>
            {createLead.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Save Lead</span>
          </Button>
        </div>
      </form>
    </SlideOver>
  );
}
