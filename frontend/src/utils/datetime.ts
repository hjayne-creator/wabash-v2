const PACIFIC_TZ = "America/Los_Angeles";

/** Backend datetimes are UTC; ISO strings may omit the trailing Z. */
function parseUtc(iso: string): Date {
  const normalized =
    iso.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`;
  return new Date(normalized);
}

export function formatPacificDateTime(iso: string): string {
  return parseUtc(iso).toLocaleString("en-US", {
    timeZone: PACIFIC_TZ,
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  });
}
