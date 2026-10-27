/**
 * The time an update was posted, as a news site shows it: `14:05`.
 *
 * @param iso - ISO 8601 timestamp.
 * @param locale - BCP 47 locale.
 * @param timeZone - IANA time zone; the reader's own when omitted.
 */
export function formatTime(
  iso: string,
  locale = 'en',
  timeZone?: string,
): string {
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone,
  }).format(new Date(iso));
}

/**
 * The day an update was posted: `Sunday, October 4`.
 *
 * @param iso - ISO 8601 timestamp.
 * @param locale - BCP 47 locale.
 * @param timeZone - IANA time zone; the reader's own when omitted.
 */
export function formatDay(
  iso: string,
  locale = 'en',
  timeZone?: string,
): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    timeZone,
  }).format(new Date(iso));
}

/**
 * How long ago something happened, in the largest whole unit: `5 min ago`.
 *
 * @param iso - ISO 8601 timestamp.
 * @param now - The current time, in milliseconds.
 * @param locale - BCP 47 locale.
 */
export function timeAgo(iso: string, now: number, locale = 'en'): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const format = new Intl.RelativeTimeFormat(locale, {
    numeric: 'auto',
    style: 'short',
  });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) {
      return format.format(Math.trunc(seconds / size), unit);
    }
  }
  return format.format(0, 'second');
}

/**
 * The reader count, rounded the way the number deserves: it is up to a few
 * seconds old and counts sockets, not people.
 *
 * @param readers - Connected readers across every backend.
 */
export function roundReaders(readers: number): number {
  if (readers < 100) return readers;
  if (readers < 1000) return Math.round(readers / 10) * 10;
  return Math.round(readers / 100) * 100;
}
