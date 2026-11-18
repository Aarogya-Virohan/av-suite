/**
 * How an exercise title is shown. Most titles are already written the way
 * they should read ("Shoulder abduction active ROM") and are shown as is.
 * Some older ones are in capitals ("CHIN TUCKS"); those are shown in
 * sentence case. The PDF uses the same rule (prescription_pdf.display_title).
 */
export function displayTitle(raw: string): string {
  const title = raw.replace(/\s+/g, " ").trim();
  const letters = title.replace(/[^A-Za-z]/g, "");
  if (!letters) return title;
  const upper = letters.replace(/[^A-Z]/g, "").length;
  const text = upper / letters.length >= 0.6 ? title.toLowerCase() : title;
  return text.charAt(0).toUpperCase() + text.slice(1);
}
