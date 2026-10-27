/**
 * Shapes shared by the `@breaking-news` service and the story's websocket.
 * The backend sends both in the same shape, so the page renders one shape
 * from both sources.
 */

/** One update, as the listing and the websocket send it. */
export interface UpdateMessage {
  v: 1;
  kind: 'update';
  /** UID of the story. */
  story: string;
  /** UID of the update; the de-duplication key. */
  uid: string;
  /** ISO 8601, UTC: where the update sits on the timeline. */
  datetime: string;
  /** ISO 8601, UTC: when the server created it; the catch-up cursor. */
  created: string;
  title: string;
  /** Safe HTML, produced by Plone's transforms. */
  body: string;
}

/** How many readers the story has, across every backend. */
export interface PresenceMessage {
  v: 1;
  kind: 'presence';
  story: string;
  readers: number;
}

/** The reader fell too far behind: reload the listing instead. */
export interface ResetMessage {
  v: 1;
  kind: 'reset';
  story: string;
}

export type LiveMessage = UpdateMessage | PresenceMessage | ResetMessage;

/** A page of `@breaking-news`. */
export interface BreakingNewsListing {
  '@id': string;
  story: string;
  live: boolean;
  items_total: number;
  b_start: number;
  b_size: number;
  items: UpdateMessage[];
}

/** Where the live connection stands, as the reader sees it. */
export type ConnectionState =
  | 'connecting'
  | 'live'
  | 'reconnecting'
  | 'refused'
  | 'stopped';
