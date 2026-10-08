const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
export function relativeTime(value: string): string {
  const seconds = (new Date(value).getTime() - Date.now()) / 1000;
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units)
    if (Math.abs(seconds) >= size)
      return formatter.format(Math.round(seconds / size), unit);
  return formatter.format(Math.round(seconds), "second");
}
