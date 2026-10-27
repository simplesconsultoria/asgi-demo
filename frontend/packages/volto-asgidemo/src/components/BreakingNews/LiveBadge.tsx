import { defineMessages, useIntl } from 'react-intl';

const messages = defineMessages({
  live: { id: 'breakingNewsLive', defaultMessage: 'Live' },
  ended: { id: 'breakingNewsEnded', defaultMessage: 'Coverage ended' },
});

export interface LiveBadgeProps {
  /** Whether the story is still being updated. */
  live: boolean;
}

/** The red "Live" tag of a running story, or a quiet one once it has ended. */
export default function LiveBadge({ live }: LiveBadgeProps) {
  const intl = useIntl();
  return (
    <span className={`bn-live-badge${live ? ' is-live' : ''}`}>
      {live && <span className="bn-live-dot" aria-hidden="true" />}
      {intl.formatMessage(live ? messages.live : messages.ended)}
    </span>
  );
}
