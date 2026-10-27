import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createLiveClient, reconnectDelay } from './liveClient';
import type { SocketLike } from './liveClient';
import type { ConnectionState, LiveMessage } from '../types/breakingNews';

class FakeSocket implements SocketLike {
  onopen: SocketLike['onopen'] = null;
  onmessage: SocketLike['onmessage'] = null;
  onclose: SocketLike['onclose'] = null;
  closedWith: number | undefined;

  constructor(public url: string) {}

  close(code?: number) {
    this.closedWith = code;
    this.onclose?.({ code: code ?? 1000 });
  }

  // Test helpers: what the server or the network does.
  serverOpens() {
    this.onopen?.({});
  }
  serverSends(message: unknown) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
  drops(code = 1006) {
    this.onclose?.({ code });
  }
}

function setup(since: string | null = null) {
  const sockets: FakeSocket[] = [];
  const states: ConnectionState[] = [];
  const messages: LiveMessage[] = [];
  const timers: { callback: () => void; delay: number }[] = [];
  let cursor = since;
  const client = createLiveClient({
    url: (value) => `ws://test/story${value ? `?since=${value}` : ''}`,
    since: () => cursor,
    onMessage: (message) => messages.push(message),
    onState: (state) => states.push(state),
    open: (url) => {
      const socket = new FakeSocket(url);
      sockets.push(socket);
      return socket;
    },
    random: () => 0.5,
    schedule: (callback, delay) => {
      timers.push({ callback, delay });
      return timers.length;
    },
    cancel: () => undefined,
  });
  const fire = () => timers.shift()?.callback();
  const setCursor = (value: string) => {
    cursor = value;
  };
  return { client, sockets, states, messages, timers, fire, setCursor };
}

describe('reconnectDelay', () => {
  it('is a random share of a doubling cap', () => {
    expect(reconnectDelay(0, () => 1)).toBe(1000);
    expect(reconnectDelay(3, () => 1)).toBe(8000);
    expect(reconnectDelay(10, () => 1)).toBe(30000);
    expect(reconnectDelay(3, () => 0.25)).toBe(2000);
  });
});

describe('createLiveClient', () => {
  let env: ReturnType<typeof setup>;

  beforeEach(() => {
    env = setup();
  });

  it('connects and reports live once the socket opens', () => {
    env.client.start();
    expect(env.states).toEqual(['connecting']);
    env.sockets[0].serverOpens();
    expect(env.states).toEqual(['connecting', 'live']);
  });

  it('passes version 1 messages on and ignores anything else', () => {
    env.client.start();
    env.sockets[0].serverOpens();
    env.sockets[0].serverSends({
      v: 1,
      kind: 'presence',
      story: 's',
      readers: 3,
    });
    env.sockets[0].serverSends({ v: 2, kind: 'future' });
    env.sockets[0].onmessage?.({ data: 'not json' });
    expect(env.messages).toEqual([
      { v: 1, kind: 'presence', story: 's', readers: 3 },
    ]);
  });

  it('reconnects with the current cursor after a drop', () => {
    env.client.start();
    env.sockets[0].serverOpens();
    env.setCursor('2026-10-04T12:00:00Z');
    env.sockets[0].drops(1012);
    expect(env.states.at(-1)).toBe('reconnecting');
    expect(env.timers[0].delay).toBe(500);
    env.fire();
    expect(env.sockets[1].url).toBe(
      'ws://test/story?since=2026-10-04T12:00:00Z',
    );
  });

  it('backs off further while the server stays away', () => {
    env.client.start();
    env.sockets[0].serverOpens();
    env.sockets[0].drops();
    env.fire();
    env.sockets[1].drops();
    // random() is 0.5: half of a cap that doubles. The first drop waited
    // 0.5 s (already fired); the failed retry waits 1 s.
    expect(env.timers.map((timer) => timer.delay)).toEqual([1000]);
  });

  it('starts the backoff over once a socket opens', () => {
    env.client.start();
    env.sockets[0].serverOpens();
    env.sockets[0].drops();
    env.fire();
    env.sockets[1].serverOpens();
    env.sockets[1].drops();
    expect(env.timers.map((timer) => timer.delay)).toEqual([500]);
  });

  it('gives up after repeated handshakes that never open', () => {
    env.client.start();
    env.sockets[0].drops();
    env.fire();
    env.sockets[1].drops();
    env.fire();
    env.sockets[2].drops();
    expect(env.states.at(-1)).toBe('refused');
    expect(env.timers).toHaveLength(0);
  });

  it('counts only refusals in a row', () => {
    env.client.start();
    env.sockets[0].drops();
    env.fire();
    env.sockets[1].drops();
    env.fire();
    env.sockets[2].serverOpens();
    env.sockets[2].drops();
    expect(env.states.at(-1)).toBe('reconnecting');
  });

  it('stops for good on 1008', () => {
    env.client.start();
    env.sockets[0].serverOpens();
    env.sockets[0].drops(1008);
    expect(env.states.at(-1)).toBe('refused');
    expect(env.timers).toHaveLength(0);
  });

  it('stop closes the socket and never reconnects', () => {
    env.client.start();
    env.sockets[0].serverOpens();
    env.client.stop();
    expect(env.sockets[0].closedWith).toBe(1000);
    expect(env.states.at(-1)).toBe('stopped');
    expect(env.timers).toHaveLength(0);
  });

  it('wake replaces the socket at once', () => {
    env.client.start();
    env.sockets[0].serverOpens();
    env.client.wake();
    expect(env.sockets).toHaveLength(2);
    expect(env.sockets[0].closedWith).toBe(1000);
    expect(env.timers).toHaveLength(0);
  });

  it('wake does nothing once stopped', () => {
    env.client.start();
    env.client.stop();
    env.client.wake();
    expect(env.sockets).toHaveLength(1);
  });

  it('uses jitter from the injected random source', () => {
    const spy = vi.fn(() => 0.1);
    const sockets: FakeSocket[] = [];
    const delays: number[] = [];
    const client = createLiveClient({
      url: () => 'ws://test',
      since: () => null,
      onMessage: () => undefined,
      onState: () => undefined,
      open: (url) => {
        const socket = new FakeSocket(url);
        sockets.push(socket);
        return socket;
      },
      random: spy,
      schedule: (_callback, delay) => delays.push(delay),
      cancel: () => undefined,
    });
    client.start();
    sockets[0].serverOpens();
    sockets[0].drops();
    expect(spy).toHaveBeenCalled();
    expect(delays).toEqual([100]);
  });
});
