import { describe, expect, it } from 'vitest';
import { formatDay, formatTime, roundReaders, timeAgo } from './format';

describe('formatTime', () => {
  it('shows hours and minutes on a 24-hour clock', () => {
    expect(
      formatTime('2026-10-04T17:05:00+00:00', 'en', 'America/Sao_Paulo'),
    ).toBe('14:05');
  });
});

describe('formatDay', () => {
  it('names the day', () => {
    expect(formatDay('2026-10-04T17:05:00+00:00', 'en', 'UTC')).toBe(
      'Sunday, October 4',
    );
  });
});

describe('timeAgo', () => {
  const now = Date.parse('2026-10-04T18:00:00Z');

  it.each([
    ['2026-10-04T17:59:30Z', 'now'],
    ['2026-10-04T17:55:00Z', '5 min. ago'],
    ['2026-10-04T15:00:00Z', '3 hr. ago'],
    ['2026-10-02T18:00:00Z', '2 days ago'],
  ])('%s is %s', (iso, expected) => {
    expect(timeAgo(iso, now)).toBe(expected);
  });
});

describe('roundReaders', () => {
  it.each([
    [7, 7],
    [99, 99],
    [123, 120],
    [1234, 1200],
    [15678, 15700],
  ])('%i reads as about %i', (readers, expected) => {
    expect(roundReaders(readers)).toBe(expected);
  });
});
