import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import Timeline from './Timeline';
import { makeUpdate, renderWithIntl } from './testing';

describe('Timeline', () => {
  const items = [
    makeUpdate({
      uid: 'c',
      title: 'Monday news',
      datetime: '2026-10-05T12:00:00Z',
    }),
    makeUpdate({
      uid: 'b',
      title: 'Sunday night',
      datetime: '2026-10-04T22:00:00Z',
    }),
    makeUpdate({
      uid: 'a',
      title: 'Sunday morning',
      datetime: '2026-10-04T11:00:00Z',
    }),
  ];

  it('lists updates in the order given', () => {
    renderWithIntl(<Timeline items={items} timeZone="UTC" />);
    expect(screen.getAllByRole('heading').map((h) => h.textContent)).toEqual([
      'Monday news',
      'Sunday night',
      'Sunday morning',
    ]);
  });

  it('heads each day once', () => {
    const { container } = renderWithIntl(
      <Timeline items={items} timeZone="UTC" />,
    );
    const days = [...container.querySelectorAll('.bn-timeline-day')].map(
      (day) => day.textContent,
    );
    expect(days).toEqual(['Monday, October 5', 'Sunday, October 4']);
  });

  it('highlights only fresh updates', () => {
    const { container } = renderWithIntl(
      <Timeline items={items} fresh={['b']} timeZone="UTC" />,
    );
    expect(container.querySelectorAll('.is-fresh')).toHaveLength(1);
    expect(container.querySelector('.is-fresh h2')?.textContent).toBe(
      'Sunday night',
    );
  });
});
