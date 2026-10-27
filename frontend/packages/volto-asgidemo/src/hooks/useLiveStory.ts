import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { createLiveClient } from '../helpers/liveClient';
import type { LiveClientOptions } from '../helpers/liveClient';
import { socketUrl } from '../helpers/socketUrl';
import { emptyTimeline, timelineReducer } from '../helpers/timeline';
import type {
  BreakingNewsListing,
  ConnectionState,
  UpdateMessage,
} from '../types/breakingNews';

export interface UseLiveStoryOptions {
  /** Socket base URL; the page's host and API rule when omitted. */
  socketBase?: string;
  /** Open sockets with this; injectable for tests. */
  open?: LiveClientOptions['open'];
  /** Called when the server says the reader fell too far behind. */
  onReset?: () => void;
}

export interface LiveStory {
  items: UpdateMessage[];
  fresh: string[];
  total: number;
  readers: number | null;
  state: ConnectionState;
  /** Add an older page fetched from `@breaking-news`. */
  addOlder: (page: BreakingNewsListing) => void;
  /** Clear the highlight on updates that arrived live. */
  markSeen: () => void;
}

/**
 * A story's timeline, kept current over a websocket.
 *
 * The first page comes from the server render. The socket opens in the
 * browser only, with the newest `created` the page has as its cursor, so a
 * cached page still catches up on everything it missed.
 *
 * @param initial - The first page of `@breaking-news`, if the story has one.
 * @param live - Whether the story is live; nothing connects when it is not.
 * @param options - Socket and reset options.
 */
export function useLiveStory(
  initial: BreakingNewsListing | undefined,
  live: boolean,
  options: UseLiveStoryOptions = {},
): LiveStory {
  const [timeline, dispatch] = useReducer(
    timelineReducer,
    initial,
    (page): typeof emptyTimeline =>
      page
        ? timelineReducer(emptyTimeline, {
            type: 'load',
            items: page.items,
            total: page.items_total,
          })
        : emptyTimeline,
  );
  const [readers, setReaders] = useState<number | null>(null);
  const [state, setState] = useState<ConnectionState>('stopped');

  // The client reads the cursor at every reconnect; a ref keeps it current
  // without reconnecting each time the timeline changes.
  const since = useRef(timeline.since);
  since.current = timeline.since;
  const onReset = useRef(options.onReset);
  onReset.current = options.onReset;

  const story = initial?.story;
  const { socketBase, open } = options;

  useEffect(() => {
    if (!story || !live || typeof window === 'undefined') return undefined;
    const client = createLiveClient({
      url: (cursor) => socketUrl(window.location, story, cursor, socketBase),
      since: () => since.current,
      onState: setState,
      onMessage: (message) => {
        if (message.story !== story) return;
        if (message.kind === 'update')
          dispatch({ type: 'receive', update: message });
        else if (message.kind === 'presence') setReaders(message.readers);
        else if (message.kind === 'reset') onReset.current?.();
      },
      open,
    });
    client.start();
    // A phone that slept may hold a dead socket for up to 40 s before the
    // server's ping notices; reconnecting on visibility is cheaper.
    const onVisible = () => {
      if (document.visibilityState === 'visible') client.wake();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      client.stop();
    };
  }, [story, live, socketBase, open]);

  const addOlder = useCallback(
    (page: BreakingNewsListing) =>
      dispatch({ type: 'older', items: page.items, total: page.items_total }),
    [],
  );
  const markSeen = useCallback(() => dispatch({ type: 'seen' }), []);

  return {
    items: timeline.items,
    fresh: timeline.fresh,
    total: timeline.total,
    readers,
    state,
    addOlder,
    markSeen,
  };
}
