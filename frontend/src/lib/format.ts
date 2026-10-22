/** Number and text formatting shared across the workspace. */

const moneyFormat = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const compactMoneyFormat = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 2,
});
const percentFormat = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const percent2Format = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const money = (value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? "—" : moneyFormat.format(Number(value));
export const compactMoney = (value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? "—" : compactMoneyFormat.format(Number(value));
export const percent = (value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? "—" : percentFormat.format(Number(value));
export const percent2 = (value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? "—" : percent2Format.format(Number(value));
export const multiple = (value: string | number | null | undefined) =>
  value === null || value === undefined || value === "" ? "—" : Number(value).toFixed(2) + "x";
export const signedPercent = (value: string | number) => {
  const number = Number(value);
  return (number > 0 ? "+" : "") + percentFormat.format(number);
};
export const signedMoney = (value: string | number) => {
  const number = Number(value);
  return (number > 0 ? "+" : number < 0 ? "−" : "") + moneyFormat.format(Math.abs(number));
};

export const today = () => new Date().toISOString().slice(0, 10);

/** Parse an ISO string; a bare YYYY-MM-DD date is read as a local calendar day, not UTC midnight. */
export const parseDate = (iso: string) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(iso);
};
export const shortDate = (iso: string) =>
  parseDate(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
export const shortDateTime = (iso: string) =>
  parseDate(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

/** Display a stored decimal rate as a percentage without binary float noise. */
export const toPercentText = (decimalRate: string) =>
  decimalRate === "" ? "" : String(parseFloat((Number(decimalRate) * 100).toPrecision(12)));
export const fromPercentText = (percentText: string) =>
  percentText === "" ? "" : String(parseFloat((Number(percentText) / 100).toPrecision(12)));

export const titleCase = (key: string) => key.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

export const valueBucketFor = (purchasePrice: string | number | null | undefined) => {
  const value = Number(purchasePrice);
  if (!Number.isFinite(value) || value <= 0) return "Custom";
  if (value < 1_000_000) return "Under $1M";
  if (value < 5_000_000) return "$1M-$5M";
  if (value < 10_000_000) return "$5M-$10M";
  if (value < 25_000_000) return "$10M-$25M";
  if (value < 50_000_000) return "$25M-$50M";
  return "$50M+";
};

export const constraintLabel = (key: string | null | undefined) =>
  key === "minimum_dscr" ? "minimum DSCR" : key === "target_levered_irr" ? "target IRR" : "—";
