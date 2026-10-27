/** Where a story's websocket lives. */
export interface SocketLocation {
  protocol: string;
  host: string;
}

/**
 * Build the URL of a story's websocket.
 *
 * By default the socket goes through the same host as the page, under the
 * API rule the proxy already has: `/++api++/++asgi++/...`. A `base` (for
 * instance `ws://localhost:8080/++asgi++` in development) points it at a
 * backend directly instead.
 *
 * @param location - The page's location (`window.location`).
 * @param story - The story's UID.
 * @param since - The newest `created` the page has, if any.
 * @param base - Optional socket base URL, overriding the default.
 */
export function socketUrl(
  location: SocketLocation,
  story: string,
  since: string | null,
  base?: string,
): string {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const root = (
    base || `${scheme}://${location.host}/++api++/++asgi++`
  ).replace(/\/+$/, '');
  const url = `${root}/breaking-news/${story}`;
  return since ? `${url}?since=${encodeURIComponent(since)}` : url;
}
