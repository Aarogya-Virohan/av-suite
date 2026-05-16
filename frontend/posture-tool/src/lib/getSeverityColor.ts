import { Severity } from "../types/posture"

export function getSeverityColor(severity: Severity) {
  switch (severity) {
    case "none":
      return {
        badgeBg: "bg-emerald-50",
        badgeText: "text-emerald-700",
        badgeBorder: "border-emerald-200"
      }

    case "mild":
      return {
        badgeBg: "bg-amber-50",
        badgeText: "text-amber-700",
        badgeBorder: "border-amber-200"
      }

    case "moderate":
      return {
        badgeBg: "bg-orange-50",
        badgeText: "text-orange-700",
        badgeBorder: "border-orange-300"
      }

    case "severe":
      return {
        badgeBg: "bg-red-50",
        badgeText: "text-red-700",
        badgeBorder: "border-red-300"
      }

    default:
      return {
        badgeBg: "bg-slate-100",
        badgeText: "text-slate-600",
        badgeBorder: "border-slate-300"
      }
  }
}