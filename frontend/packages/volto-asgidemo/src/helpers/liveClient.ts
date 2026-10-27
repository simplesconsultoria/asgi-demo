import type { ConnectionState, LiveMessage } from '../types/breakingNews';

/** The parts of the browser's `WebSocket` the client uses. */
export interface SocketLike {
  onopen: ((event: unknown) => void) | null;
  onmessage: ((event: { data: string }) => void) | null;
  onclose: ((event: { code: number }) => void) | null;
  close(code?: number): void;
}

export interface LiveClientOptions {
  /** Builds the socket URL for the current cursor. */
  url: (since: string | null) => string;
  /** The newest `created` the page has, read at every (re)connect. */
  since: () => string | null;
  onMessage: (message: LiveMessage) => void;
  onState: (state: ConnectionState) => void;
  /** Opens a socket; defaults to the browser's `WebSocket`. */
  open?: (url: string) => SocketLike;
  /** Longest delay between reconnects, in milliseconds. */
  maxDelay?: number;
  /**
   * Handshakes in a row that never open before the client gives up. A reader
   * who may not see the story is refused before the socket opens, which a
   * browser reports as close code 1006, exactly like a network failure, so
   * the refusal can only be told apart by repetition.
   */
  maxRefusals?: number;
  random?: () => number;
  schedule?: (callback: () => void, delay: number) => unknown;
  cancel?: (handle: unknown) => void;
}

export interface LiveClient {
  start(): void;
  stop(): void;
  /** Reconnect now, e.g. when a sleeping tab becomes visible again. */
  wake(): void;
}

/** Close codes that mean "do not come back". */
const FINAL_CODES = new Set([1008]);

/** Full-jitter backoff: a random delay below a cap that doubles per attempt. */
export function reconnectDelay(
  attempt: number,
  random: () => number,
  maxDelay = 30000,
): number {
  return random() * Math.min(maxDelay, 1000 * 2 ** attempt);
}

export function createLiveClient(options: LiveClientOptions): LiveClient {
  const {
    url,
    since,
    onMessage,
    onState,
    open = (target: string) => new WebSocket(target) as unknown as SocketLike,
    maxDelay = 30000,
    maxRefusals = 3,
    random = Math.random,
    schedule = (callback, delay) => setTimeout(callback, delay),
    cancel = (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
  } = options;

  let socket: SocketLike | null = null;
  let timer: unknown = null;
  let attempt = 0;
  let refusals = 0;
  let running = false;

  const clearTimer = () => {
    if (timer !== null) cancel(timer);
    timer = null;
  };

  const connect = () => {
    clearTimer();
    if (!running) return;
    let opened = false;
    onState(attempt === 0 ? 'connecting' : 'reconnecting');
    const current = open(url(since()));
    socket = current;

    current.onopen = () => {
      opened = true;
      attempt = 0;
      refusals = 0;
      onState('live');
    };
    current.onmessage = (event) => {
      let message: LiveMessage;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (message && message.v === 1) onMessage(message);
    };
    current.onclose = (event) => {
      if (socket !== current) return; // replaced by wake() or stop()
      socket = null;
      if (!running) return;
      refusals = opened ? 0 : refusals + 1;
      if (FINAL_CODES.has(event.code) || refusals >= maxRefusals) {
        running = false;
        onState('refused');
        return;
      }
      onState('reconnecting');
      timer = schedule(connect, reconnectDelay(attempt++, random, maxDelay));
    };
  };

  return {
    start() {
      if (running) return;
      running = true;
      attempt = 0;
      refusals = 0;
      connect();
    },
    stop() {
      running = false;
      clearTimer();
      const current = socket;
      socket = null;
      current?.close(1000);
      onState('stopped');
    },
    wake() {
      if (!running) return;
      const current = socket;
      socket = null;
      current?.close(1000);
      attempt = 0;
      connect();
    },
  };
}
