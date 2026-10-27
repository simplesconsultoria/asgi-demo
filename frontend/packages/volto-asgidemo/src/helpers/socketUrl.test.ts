import { describe, expect, it } from 'vitest';
import { socketUrl } from './socketUrl';

const UID = '0123456789abcdef0123456789abcdef';

describe('socketUrl', () => {
  it('uses the page host and the API rule by default', () => {
    expect(
      socketUrl({ protocol: 'http:', host: 'asgi-demo.localhost' }, UID, null),
    ).toBe(`ws://asgi-demo.localhost/++api++/++asgi++/breaking-news/${UID}`);
  });

  it('upgrades to wss behind TLS', () => {
    expect(
      socketUrl({ protocol: 'https:', host: 'example.org' }, UID, null),
    ).toMatch(/^wss:\/\/example\.org\//);
  });

  it('encodes the cursor, plus sign included', () => {
    const url = socketUrl(
      { protocol: 'http:', host: 'h' },
      UID,
      '2026-10-04T14:02:11+00:00',
    );
    expect(url).toBe(
      `ws://h/++api++/++asgi++/breaking-news/${UID}?since=2026-10-04T14%3A02%3A11%2B00%3A00`,
    );
  });

  it('can point at a backend directly', () => {
    expect(
      socketUrl(
        { protocol: 'http:', host: 'localhost:3000' },
        UID,
        null,
        'ws://localhost:8080/++asgi++/',
      ),
    ).toBe(`ws://localhost:8080/++asgi++/breaking-news/${UID}`);
  });
});
