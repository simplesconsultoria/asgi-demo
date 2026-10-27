import { describe, expect, it, vi } from 'vitest';
import { fireEvent, screen } from '@testing-library/react';
import ConnectionStatus from './ConnectionStatus';
import LiveBadge from './LiveBadge';
import LoadOlder from './LoadOlder';
import NewUpdatesBanner from './NewUpdatesBanner';
import ReaderCount from './ReaderCount';
import StoryHeader from './StoryHeader';
import { renderWithIntl } from './testing';

describe('LiveBadge', () => {
  it('says Live while the story runs', () => {
    const { container } = renderWithIntl(<LiveBadge live />);
    expect(screen.getByText('Live')).toBeTruthy();
    expect(container.querySelector('.bn-live-dot')).toBeTruthy();
  });

  it('says the coverage ended otherwise', () => {
    const { container } = renderWithIntl(<LiveBadge live={false} />);
    expect(screen.getByText('Coverage ended')).toBeTruthy();
    expect(container.querySelector('.bn-live-dot')).toBeNull();
  });
});

describe('ReaderCount', () => {
  it('shows nothing until a count arrives', () => {
    const { container } = renderWithIntl(<ReaderCount readers={null} />);
    expect(container.textContent).toBe('');
  });

  it('rounds large counts', () => {
    renderWithIntl(<ReaderCount readers={1234} />);
    expect(screen.getByText('About 1,200 people reading')).toBeTruthy();
  });

  it('speaks of one reader in the singular', () => {
    renderWithIntl(<ReaderCount readers={1} />);
    expect(screen.getByText('1 person reading')).toBeTruthy();
  });
});

describe('ConnectionStatus', () => {
  it.each([
    ['connecting', 'Connecting to live updates…'],
    ['live', 'Updates appear automatically'],
    ['reconnecting', 'Connection lost, reconnecting…'],
    [
      'refused',
      'Live updates are unavailable. Reload the page for the latest.',
    ],
  ] as const)('%s', (state, text) => {
    renderWithIntl(<ConnectionStatus state={state} />);
    expect(screen.getByRole('status').textContent).toBe(text);
  });

  it('is silent when stopped', () => {
    const { container } = renderWithIntl(<ConnectionStatus state="stopped" />);
    expect(container.textContent).toBe('');
  });
});

describe('NewUpdatesBanner', () => {
  it('hides with nothing new', () => {
    const { container } = renderWithIntl(
      <NewUpdatesBanner count={0} onClick={() => {}} />,
    );
    expect(container.textContent).toBe('');
  });

  it('counts new updates and takes the reader up', () => {
    const onClick = vi.fn();
    renderWithIntl(<NewUpdatesBanner count={3} onClick={onClick} />);
    fireEvent.click(screen.getByRole('button', { name: /3 new updates/ }));
    expect(onClick).toHaveBeenCalledOnce();
  });
});

describe('LoadOlder', () => {
  it('hides when everything is shown', () => {
    const { container } = renderWithIntl(
      <LoadOlder remaining={0} loading={false} onClick={() => {}} />,
    );
    expect(container.textContent).toBe('');
  });

  it('says how many are left', () => {
    const onClick = vi.fn();
    renderWithIntl(
      <LoadOlder remaining={23} loading={false} onClick={onClick} />,
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Show 23 earlier updates' }),
    );
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled while loading', () => {
    renderWithIntl(<LoadOlder remaining={5} loading onClick={() => {}} />);
    expect((screen.getByRole('button') as HTMLButtonElement).disabled).toBe(
      true,
    );
  });
});

describe('StoryHeader', () => {
  it('puts the tag, title, standfirst and freshness together', () => {
    renderWithIntl(
      <StoryHeader
        title="Brazil Elections 2026"
        description="Live coverage."
        live
        readers={42}
        lastUpdate="2026-10-04T17:55:00Z"
        now={Date.parse('2026-10-04T18:00:00Z')}
      />,
    );
    expect(
      screen.getByRole('heading', { level: 1, name: 'Brazil Elections 2026' }),
    ).toBeTruthy();
    expect(screen.getByText('Live coverage.')).toBeTruthy();
    expect(screen.getByText('Updated 5 min. ago')).toBeTruthy();
    expect(screen.getByText('About 42 people reading')).toBeTruthy();
  });
});
