import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import UpdateCard from './UpdateCard';
import { makeUpdate, renderWithIntl } from './testing';

describe('UpdateCard', () => {
  it('shows the time, the headline and the body', () => {
    const { container } = renderWithIntl(
      <UpdateCard update={makeUpdate()} timeZone="America/Sao_Paulo" />,
    );
    expect(screen.getByRole('heading', { name: 'Polls close' })).toBeTruthy();
    expect(screen.getByText('14:00').getAttribute('dateTime')).toBe(
      '2026-10-04T17:00:00+00:00',
    );
    expect(container.querySelector('.bn-update-body p')?.textContent).toBe(
      'Counting begins now.',
    );
  });

  it('renders the title as text, never as markup', () => {
    renderWithIntl(
      <UpdateCard update={makeUpdate({ title: '<b>Bold</b>' })} />,
    );
    expect(screen.getByRole('heading').textContent).toBe('<b>Bold</b>');
  });

  it('leaves out an empty body', () => {
    const { container } = renderWithIntl(
      <UpdateCard update={makeUpdate({ body: '' })} />,
    );
    expect(container.querySelector('.bn-update-body')).toBeNull();
  });

  it('highlights a fresh update', () => {
    const { container } = renderWithIntl(
      <UpdateCard update={makeUpdate()} fresh />,
    );
    expect(container.querySelector('article')?.className).toContain('is-fresh');
  });
});
