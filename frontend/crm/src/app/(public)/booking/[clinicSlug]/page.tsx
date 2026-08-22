'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { Stethoscope, Calendar, Clock, User, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '../../../../lib/api-client';

export default function PublicBookingPage() {
  const params = useParams();
  const clinicSlug = (params?.clinicSlug as string) || 'aarogya';

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [service, setService] = useState('Physiotherapy Consultation');
  const [preferredDate, setPreferredDate] = useState(new Date().toISOString().slice(0, 10));
  const [preferredSlot, setPreferredSlot] = useState('10:00 AM');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    if (!name || !phone || !chiefComplaint) {
      toast.error('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Fetch clinic ID from branding endpoint using the slug
      const brandingRes = await apiClient.get(`/booking/branding/${clinicSlug}`);
      const clinicId = brandingRes.data?.data?.clinic_id || brandingRes.data?.clinic_id;

      if (!clinicId) {
        toast.error('Could not verify clinic. Please check the URL.');
        setIsSubmitting(false);
        return;
      }

      // 2. Submit the booking request
      await apiClient.post(`/booking/request?clinic_id=${clinicId}`, {
        name: name,
        phone: phone,
        chief_complaint: chiefComplaint,
        preferred_date: preferredDate,
        preferred_slot: preferredSlot,
        notes: `Service Requested: ${service}`,
      });

      setIsSuccess(true);
      toast.success('Appointment request submitted!');
    } catch (err) {
      console.error(err);
      toast.error('Failed to submit appointment request');
      setIsSubmitting(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-2xl text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Booking Requested!</h2>
          <p className="text-sm text-slate-500">
            Thank you, <strong className="text-slate-800 dark:text-slate-200">{name}</strong>. The clinic staff at{' '}
            <span className="capitalize font-semibold text-teal-600">{clinicSlug}</span> will contact you at{' '}
            <strong>{phone}</strong> to confirm your slot for {preferredDate} at {preferredSlot}.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 p-4 md:p-8 flex items-center justify-center">
      <div className="max-w-lg w-full bg-white dark:bg-slate-900 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div className="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center">
            <Stethoscope className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white capitalize">
              {clinicSlug.replace('-', ' ')} Clinic
            </h1>
            <p className="text-xs text-slate-400">Request an appointment online</p>
          </div>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-between text-xs font-bold text-slate-400 border-b border-slate-100 dark:border-slate-800 pb-3">
          <span className={step >= 1 ? 'text-teal-600' : ''}>1. Service</span>
          <span className={step >= 2 ? 'text-teal-600' : ''}>2. Time</span>
          <span className={step >= 3 ? 'text-teal-600' : ''}>3. Details</span>
        </div>

        {/* Form Steps */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {step === 1 && (
            <div className="space-y-3">
              <label className="block text-xs font-bold uppercase text-slate-400">Select Service</label>
              {['Physiotherapy Consultation', 'Spine & Back Rehab', 'Sports Injury Rehab', 'Post-Operative Therapy'].map((s) => (
                <button
                  type="button"
                  key={s}
                  onClick={() => {
                    setService(s);
                    setStep(2);
                  }}
                  className={`w-full p-3.5 rounded-xl border text-left text-sm font-semibold transition-all flex items-center justify-between ${
                    service === s
                      ? 'border-teal-600 bg-teal-50 dark:bg-teal-950 text-teal-600'
                      : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  <span>{s}</span>
                  <Calendar className="w-4 h-4" />
                </button>
              ))}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Preferred Date</label>
                <input
                  type="date"
                  value={preferredDate}
                  onChange={(e) => setPreferredDate(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Preferred Time Slot</label>
                <div className="grid grid-cols-3 gap-2">
                  {['09:00 AM', '10:00 AM', '11:30 AM', '02:00 PM', '04:00 PM', '06:00 PM'].map((slot) => (
                    <button
                      type="button"
                      key={slot}
                      onClick={() => setPreferredSlot(slot)}
                      className={`p-2 rounded-lg text-xs font-bold border transition-colors ${
                        preferredSlot === slot
                          ? 'border-teal-600 bg-teal-600 text-white'
                          : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      {slot}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between pt-3">
                <button type="button" onClick={() => setStep(1)} className="text-xs text-slate-400 hover:text-white">
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="px-4 py-2 bg-teal-600 text-white text-xs font-bold rounded-lg"
                >
                  Next: Enter Details
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Your Full Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Ramesh Shah"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Phone Number *</label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+919876543210"
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Chief Complaint *</label>
                <textarea
                  rows={3}
                  value={chiefComplaint}
                  onChange={(e) => setChiefComplaint(e.target.value)}
                  placeholder="Describe your pain or reason for visit..."
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm"
                />
              </div>

              <div className="flex items-center justify-between pt-3">
                <button type="button" onClick={() => setStep(2)} className="text-xs text-slate-400 hover:text-white">
                  Back
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg flex items-center gap-2 cursor-pointer shadow-md shadow-teal-600/30"
                >
                  {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  <span>Submit Appointment Request</span>
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
