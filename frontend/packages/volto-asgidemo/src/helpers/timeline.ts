import type { UpdateMessage } from '../types/breakingNews';

/** The updates a reader has, newest first, with what arrived live. */
export interface TimelineState {
  items: UpdateMessage[];
  /** UIDs of updates that arrived over the websocket, for highlighting. */
  fresh: string[];
  /** Newest `created` seen: the cursor for the next (re)connect. */
  since: string | null;
  total: number;
}

export type TimelineAction =
  | { type: 'load'; items: UpdateMessage[]; total: number }
  | { type: 'older'; items: UpdateMessage[]; total: number }
  | { type: 'receive'; update: UpdateMessage }
  | { type: 'seen' };

export const emptyTimeline: TimelineState = {
  items: [],
  fresh: [],
  since: null,
  total: 0,
};

/**
 * Newest first, by `datetime`; ties broken by `created`, then UID, so the
 * order never depends on arrival order.
 */
export function compareUpdates(a: UpdateMessage, b: UpdateMessage): number {
  if (a.datetime !== b.datetime) return a.datetime < b.datetime ? 1 : -1;
  if (a.created !== b.created) return a.created < b.created ? 1 : -1;
  if (a.uid === b.uid) return 0;
  return a.uid < b.uid ? 1 : -1;
}

function newestCreated(
  items: UpdateMessage[],
  since: string | null,
): string | null {
  return items.reduce<string | null>(
    (newest, item) =>
      newest === null || item.created > newest ? item.created : newest,
    since,
  );
}

/**
 * Merge updates into the timeline, dropping duplicates by UID.
 *
 * Duplicates are expected: the server joins the reader to the live feed
 * before it replays what they missed, so an update can arrive both ways.
 * A later copy replaces an earlier one, which also covers corrections.
 */
export function mergeUpdates(
  items: UpdateMessage[],
  incoming: UpdateMessage[],
): UpdateMessage[] {
  const byUid = new Map(items.map((item) => [item.uid, item]));
  incoming.forEach((item) => byUid.set(item.uid, item));
  return [...byUid.values()].sort(compareUpdates);
}

export function timelineReducer(
  state: TimelineState,
  action: TimelineAction,
): TimelineState {
  switch (action.type) {
    case 'load':
      return {
        items: mergeUpdates([], action.items),
        fresh: [],
        since: newestCreated(action.items, null),
        total: action.total,
      };
    case 'older':
      return {
        ...state,
        items: mergeUpdates(state.items, action.items),
        since: newestCreated(action.items, state.since),
        total: Math.max(state.total, action.total),
      };
    case 'receive': {
      const known = state.items.some((item) => item.uid === action.update.uid);
      return {
        items: mergeUpdates(state.items, [action.update]),
        fresh: known ? state.fresh : [...state.fresh, action.update.uid],
        since: newestCreated([action.update], state.since),
        total: known ? state.total : state.total + 1,
      };
    }
    case 'seen':
      return state.fresh.length ? { ...state, fresh: [] } : state;
    default:
      return state;
  }
}
