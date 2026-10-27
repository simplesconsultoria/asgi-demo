import { describe, expect, it } from 'vitest';
import {
  compareUpdates,
  emptyTimeline,
  mergeUpdates,
  timelineReducer,
} from './timeline';
import type { UpdateMessage } from '../types/breakingNews';

const update = (
  uid: string,
  datetime: string,
  created = datetime,
  title = uid,
): UpdateMessage => ({
  v: 1,
  kind: 'update',
  story: 'story',
  uid,
  datetime,
  created,
  title,
  body: '',
});

const a = update('a', '2026-10-04T11:00:00+00:00');
const b = update('b', '2026-10-04T12:00:00+00:00');
const c = update('c', '2026-10-04T13:00:00+00:00');

describe('compareUpdates', () => {
  it('sorts newest first by datetime', () => {
    expect([a, c, b].sort(compareUpdates).map((u) => u.uid)).toEqual([
      'c',
      'b',
      'a',
    ]);
  });

  it('breaks ties on created, then uid, never on arrival order', () => {
    const x = update('x', a.datetime, '2026-10-04T11:00:05+00:00');
    const y = update('y', a.datetime, '2026-10-04T11:00:01+00:00');
    const z = update('z', a.datetime, '2026-10-04T11:00:01+00:00');
    expect([y, x, z].sort(compareUpdates).map((u) => u.uid)).toEqual([
      'x',
      'z',
      'y',
    ]);
  });
});

describe('mergeUpdates', () => {
  it('drops duplicates by uid', () => {
    expect(mergeUpdates([a, b], [b, c]).map((u) => u.uid)).toEqual([
      'c',
      'b',
      'a',
    ]);
  });

  it('keeps the later copy of an update', () => {
    const corrected = { ...b, title: 'Corrected' };
    expect(mergeUpdates([a, b], [corrected])[0].title).toBe('Corrected');
  });
});

describe('timelineReducer', () => {
  it('loads a page and takes its newest created as the cursor', () => {
    const state = timelineReducer(emptyTimeline, {
      type: 'load',
      items: [a, c, b],
      total: 40,
    });
    expect(state.items.map((u) => u.uid)).toEqual(['c', 'b', 'a']);
    expect(state.since).toBe(c.created);
    expect(state.total).toBe(40);
    expect(state.fresh).toEqual([]);
  });

  it('marks a live update as fresh and counts it', () => {
    const loaded = timelineReducer(emptyTimeline, {
      type: 'load',
      items: [a],
      total: 1,
    });
    const state = timelineReducer(loaded, { type: 'receive', update: b });
    expect(state.items.map((u) => u.uid)).toEqual(['b', 'a']);
    expect(state.fresh).toEqual(['b']);
    expect(state.total).toBe(2);
    expect(state.since).toBe(b.created);
  });

  it('does not count or highlight a duplicate', () => {
    const loaded = timelineReducer(emptyTimeline, {
      type: 'load',
      items: [a, b],
      total: 2,
    });
    const state = timelineReducer(loaded, { type: 'receive', update: b });
    expect(state.items).toHaveLength(2);
    expect(state.fresh).toEqual([]);
    expect(state.total).toBe(2);
  });

  it('places a back-dated live update by datetime, not arrival', () => {
    const loaded = timelineReducer(emptyTimeline, {
      type: 'load',
      items: [b, c],
      total: 2,
    });
    const late = update('late', a.datetime, '2026-10-04T14:00:00+00:00');
    const state = timelineReducer(loaded, { type: 'receive', update: late });
    expect(state.items.map((u) => u.uid)).toEqual(['c', 'b', 'late']);
    expect(state.since).toBe(late.created);
  });

  it('appends older pages without losing the cursor', () => {
    const loaded = timelineReducer(emptyTimeline, {
      type: 'load',
      items: [c],
      total: 3,
    });
    const state = timelineReducer(loaded, {
      type: 'older',
      items: [b, a],
      total: 3,
    });
    expect(state.items.map((u) => u.uid)).toEqual(['c', 'b', 'a']);
    expect(state.since).toBe(c.created);
  });

  it('clears highlights once seen', () => {
    const state = timelineReducer(
      { ...emptyTimeline, items: [a], fresh: ['a'] },
      { type: 'seen' },
    );
    expect(state.fresh).toEqual([]);
  });
});
