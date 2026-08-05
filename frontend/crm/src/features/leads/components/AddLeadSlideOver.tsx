'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { SlideOver } from '../../../components/ui/SlideOver';
import { leadFormSchema, LeadFormValues } from '../../../lib/schemas';
import { useCreateLead } from '../api';
import { Loader2 } from 'lucide-react';

interface AddLeadSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AddLeadSlideOver({ isOpen, onClose }: AddLeadSlideOverProps) {
  const createLead = useCreateLead();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadFormSchema),
    defaultValues: {
      name: '',
      phone: '',
      email: '',
      source: 'Website Form',
      stage: 'new',
      notes: '',
    },
  });

  const onSubmit = async (values: LeadFormValues) => {
    try {
      await createLead.mutateAsync(values);
      toast.success(`Lead ${values.name} created successfully`);
      reset();
      onClose();
    } catch (err) {
      console.error(err);
      toast.error('Failed to create lead');
    }
  };

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title="Add New Lead" subtitle="Capture prospective patient details">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Lead Name *
          </label>
          <input
            {...register('name')}
            type="text"
            placeholder="Amit Patel"
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
          />
          {errors.name && <p className="text-xs text-rose-500 mt-1">{errors.name.message}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Phone Number *
          </label>
          <input
            {...register('phone')}
            type="tel"
            placeholder="+919988776655"
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
          />
          {errors.phone && <p className="text-xs text-rose-500 mt-1">{errors.phone.message}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Email Address
          </label>
          <input
            {...register('email')}
            type="email"
            placeholder="amit.patel@example.com"
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
          />
          {errors.email && <p className="text-xs text-rose-500 mt-1">{errors.email.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Source *
            </label>
            <input
              {...register('source')}
              type="text"
              placeholder="Website / Google"
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Stage *
            </label>
            <select
              {...register('stage')}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
            >
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="qualified">Qualified</option>
              <option value="converted">Converted</option>
              <option value="lost">Lost</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Notes
          </label>
          <textarea
            {...register('notes')}
            rows={3}
            placeholder="Details about patient inquiry..."
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
          />
        </div>

        <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createLead.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg flex items-center gap-2"
          >
            {createLead.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>Save Lead</span>
          </button>
        </div>
      </form>
    </SlideOver>
  );
}
