import type { ReactNode } from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { timeAgo } from '../../helpers/format';
import LiveBadge from './LiveBadge';
import ReaderCount from './ReaderCount';

const messages = defineMessages({
  updated: { id: 'breakingNewsUpdated', defaultMessage: 'Updated {when}' },
});

export interface StoryHeaderProps {
  title: string;
  description?: string;
  live: boolean;
  readers: number | null;
  /** ISO timestamp of the newest update. */
  lastUpdate?: string;
  /** Milliseconds; injectable so the "updated" line is testable. */
  now?: number;
  /** The lead image, rendered by the caller. */
  image?: ReactNode;
}

/** The story's headline block: tag, title, standfirst and lead image. */
export default function StoryHeader({
  title,
  description,
  live,
  readers,
  lastUpdate,
  now = Date.now(),
  image,
}: StoryHeaderProps) {
  const intl = useIntl();
  return (
    <header className="bn-header">
      <div className="bn-header-meta">
        <LiveBadge live={live} />
        {lastUpdate && (
          <span className="bn-updated">
            {intl.formatMessage(messages.updated, {
              when: timeAgo(lastUpdate, now, intl.locale),
            })}
          </span>
        )}
        <ReaderCount readers={readers} />
      </div>
      <h1 className="documentFirstHeading bn-title">{title}</h1>
      {description && <p className="bn-standfirst">{description}</p>}
      {image && <figure className="bn-lead-image">{image}</figure>}
    </header>
  );
}
