const amountPattern = /^([+-]?)(\d+)(?:\.(\d+))?$/;

/** Format a backend Decimal string without converting monetary values to floating point. */
export function formatMoney(amount: string | null | undefined): string {
  const value = amount?.trim() || '0';
  const match = amountPattern.exec(value);

  if (!match) {
    return `₹${value}`;
  }

  const [, sign, whole, fraction = ''] = match;
  const groupedWhole = new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 0,
  }).format(BigInt(whole));
  const formattedFraction = fraction.padEnd(2, '0');

  return `₹${sign === '-' ? '-' : ''}${groupedWhole}.${formattedFraction}`;
}
