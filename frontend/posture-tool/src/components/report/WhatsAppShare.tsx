"use client"

import { useState } from "react"
import { downloadPostureReportPdf } from "@/lib/api"
import { normalisePhone, reportMessage, whatsappUrl } from "@/lib/whatsapp"
import type { PostureReport } from "@/types/posture"

/*
 * POS-3, 21 November 2026. "WhatsApp" opens a small panel for the patient's
 * number (optional). Send opens WhatsApp with the text filled in, then the
 * PDF downloads on this device for staff to attach. WhatsApp opens first,
 * inside the click, so the browser does not treat it as a popup.
 */
export default function WhatsAppShare({ report }: { report: PostureReport }) {
  const [open, setOpen] = useState(false)
  const [phone, setPhone] = useState("")
  const [busy, setBusy] = useState(false)

  const typed = phone.trim() !== ""
  const normalised = normalisePhone(phone)
  const invalid = typed && !normalised

  async function send() {
    if (invalid) return
    window.open(whatsappUrl(normalised, reportMessage(report)), "_blank", "noopener")
    setBusy(true)
    try {
      await downloadPostureReportPdf(report)
      setOpen(false)
    } catch {
      alert("WhatsApp opened, but the PDF could not be generated. Use Download PDF and attach it.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {open && (
        <div
          role="group"
          aria-label="Share on WhatsApp"
          className="order-first mb-1 basis-full rounded-xl border border-[#E3DCCB] bg-white p-3"
        >
          <label htmlFor="wa-phone" className="block text-[13px] font-semibold text-[#141A33]">
            Patient&apos;s WhatsApp number <span className="font-normal text-[#5D6380]">(optional)</span>
          </label>
          <div className="mt-2 flex gap-2">
            <input
              id="wa-phone"
              type="tel"
              inputMode="tel"
              autoComplete="off"
              placeholder="10-digit mobile"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              aria-invalid={invalid}
              className="h-11 min-w-0 flex-1 rounded-xl border border-[#E3DCCB] px-3 text-[15px] text-[#141A33] outline-none focus:border-[#4E888F]"
            />
            <button
              type="button"
              disabled={busy || invalid}
              onClick={send}
              className="h-11 shrink-0 rounded-xl bg-[#4E888F] px-4 text-[14px] font-semibold text-white transition hover:bg-[#3B6A70] disabled:opacity-60"
            >
              {busy ? "Preparing PDF…" : "Send"}
            </button>
          </div>
          <p className="mt-2 text-[12px] leading-relaxed text-[#5D6380]">
            {invalid
              ? "Enter a 10-digit mobile number, or leave it empty to pick the contact in WhatsApp."
              : "WhatsApp opens with a message ready. The PDF downloads on this device: attach it in the chat before sending."}
          </p>
        </div>
      )}
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="h-11 flex-1 rounded-xl border border-[#E3DCCB] bg-[#FFFDF7] px-4 text-[14px] font-semibold text-[#141A33] transition hover:bg-[#F3EEE2] sm:flex-none"
      >
        WhatsApp
      </button>
    </>
  )
}
