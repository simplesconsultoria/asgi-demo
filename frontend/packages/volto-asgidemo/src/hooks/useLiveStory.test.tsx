import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { SocketLike } from '../helpers/liveClient';
import type { BreakingNewsListing, UpdateMessage } from '../types/breakingNews';
import { useLiveStory } from './useLiveStory';

const STORY = '0123456789abcdef0123456789abcdef';

const update = (uid: string, datetime: string): UpdateMessage => ({
  v: 1,
  kind: 'update',
  story: STORY,
  uid,
  datetime,
  created: datetime,
  title: uid,
  body: '',
});

const page: BreakingNewsListing = {
  '@id': 'http://localhost/story/@breaking-news',
  story: STORY,
  live: true,
  items_total: 2,
  b_start: 0,
  b_size: 20,
  items: [
    update('b', '2026-10-04T12:00:00Z'),
    update('a', '2026-10-04T11:00:00Z'),
  ],
};

class FakeSocket implements SocketLike {
  onopen: SocketLike['onopen'] = null;
  onmessage: SocketLike['onmessage'] = null;
  onclose: SocketLike['onclose'] = null;
  closed = false;
  constructor(public url: string) {}
  close() {
    this.closed = true;
  }
  send(message: unknown) {
    act(() => this.onmessage?.({ data: JSON.stringify(message) }));
  }
}

function setup(live = true) {
  const sockets: FakeSocket[] = [];
  const open = (url: string) => {
    const socket = new FakeSocket(url);
    sockets.push(socket);
    return socket;
  };
  const hook = renderHook(() => useLiveStory(page, live, { open }));
  return { ...hook, sockets };
}

describe('useLiveStory', () => {
  it('starts from the server-rendered page', () => {
    const { result } = setup();
    expect(result.current.items.map((u) => u.uid)).toEqual(['b', 'a']);
    expect(result.current.total).toBe(2);
  });

  it('connects with the newest created as the cursor', () => {
    const { sockets } = setup();
    expect(sockets).toHaveLength(1);
    expect(sockets[0].url).toContain(`/breaking-news/${STORY}?since=`);
    expect(decodeURIComponent(sockets[0].url)).toContain(
      'since=2026-10-04T12:00:00Z',
    );
  });

  it('adds live updates and reader counts', () => {
    const { result, sockets } = setup();
    act(() => sockets[0].onopen?.({}));
    expect(result.current.state).toBe('live');
    sockets[0].send(update('c', '2026-10-04T13:00:00Z'));
    sockets[0].send({ v: 1, kind: 'presence', story: STORY, readers: 7 });
    expect(result.current.items.map((u) => u.uid)).toEqual(['c', 'b', 'a']);
    expect(result.current.fresh).toEqual(['c']);
    expect(result.current.readers).toBe(7);
  });

  it('ignores messages for another story', () => {
    const { result, sockets } = setup();
    sockets[0].send({ ...update('x', '2026-10-04T13:00:00Z'), story: 'other' });
    expect(result.current.items).toHaveLength(2);
  });

  it('does not connect to a story that is no longer live', () => {
    const { sockets } = setup(false);
    expect(sockets).toHaveLength(0);
  });

  it('closes the socket on unmount', () => {
    const { sockets, unmount } = setup();
    unmount();
    expect(sockets[0].closed).toBe(true);
  });
});
