import { useCallback, useEffect, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import config from '@plone/volto/registry';
import Image from '@plone/volto/components/theme/Image/Image';
import { getBreakingNews } from '../../actions/breakingNews';
import { useLiveStory } from '../../hooks/useLiveStory';
import type { BreakingNewsListing } from '../../types/breakingNews';
import ConnectionStatus from './ConnectionStatus';
import LoadOlder from './LoadOlder';
import NewUpdatesBanner from './NewUpdatesBanner';
import StoryHeader from './StoryHeader';
import Timeline from './Timeline';
import './BreakingNews.scss';

const PAGE_SIZE = 20;

export interface BreakingNewsContent {
  '@id': string;
  title: string;
  description?: string;
  live?: boolean;
  image?: unknown;
  '@components'?: { 'breaking-news'?: BreakingNewsListing };
}

export interface BreakingNewsViewProps {
  content: BreakingNewsContent;
}

/**
 * The page of a Breaking News story.
 *
 * The first page of updates comes with the content (the `breaking-news`
 * component, expanded by the API), so the server renders it. In the browser
 * the page then opens one websocket and keeps the timeline current.
 */
export default function BreakingNewsView({ content }: BreakingNewsViewProps) {
  const dispatch = useDispatch();
  const initial = content['@components']?.['breaking-news'];
  const live = Boolean(content.live ?? initial?.live);
  const top = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [atTop, setAtTop] = useState(true);

  const reload = useCallback(() => window.location.reload(), []);
  const story = useLiveStory(initial, live, {
    socketBase: config.settings.breakingNews?.socketBase,
    onReset: reload,
  });
  const { items, fresh, total, markSeen, addOlder } = story;

  // Highlights fade once the reader is at the top of the timeline.
  useEffect(() => {
    if (!top.current || typeof IntersectionObserver === 'undefined')
      return undefined;
    const observer = new IntersectionObserver(([entry]) =>
      setAtTop(entry.isIntersecting),
    );
    observer.observe(top.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!atTop || !fresh.length) return undefined;
    const timer = setTimeout(markSeen, 4000);
    return () => clearTimeout(timer);
  }, [atTop, fresh.length, markSeen]);

  const scrollToTop = useCallback(() => {
    top.current?.scrollIntoView({ behavior: 'smooth' });
    markSeen();
  }, [markSeen]);

  const loadOlder = useCallback(async () => {
    setLoading(true);
    try {
      const page = (await dispatch(
        getBreakingNews(content['@id'], items.length, PAGE_SIZE) as any,
      )) as unknown as BreakingNewsListing;
      addOlder(page);
    } finally {
      setLoading(false);
    }
  }, [dispatch, content, items.length, addOlder]);

  return (
    <div id="page-document" className="view-wrapper breaking-news-view">
      <StoryHeader
        title={content.title}
        description={content.description}
        live={live}
        readers={story.readers}
        lastUpdate={items[0]?.datetime}
        image={
          content.image ? (
            <Image item={content} imageField="image" alt="" responsive={true} />
          ) : undefined
        }
      />
      {live && <ConnectionStatus state={story.state} />}
      <div ref={top} className="bn-timeline-top" />
      {!atTop && (
        <NewUpdatesBanner count={fresh.length} onClick={scrollToTop} />
      )}
      <Timeline items={items} fresh={fresh} />
      <LoadOlder
        remaining={total - items.length}
        loading={loading}
        onClick={loadOlder}
      />
    </div>
  );
}
