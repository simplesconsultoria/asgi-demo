import { defineMessages, useIntl } from 'react-intl';

const messages = defineMessages({
  older: {
    id: 'breakingNewsLoadOlder',
    defaultMessage:
      'Show {count, plural, one {# earlier update} other {# earlier updates}}',
  },
  loading: { id: 'breakingNewsLoading', defaultMessage: 'Loading…' },
});

export interface LoadOlderProps {
  /** Updates not shown yet. */
  remaining: number;
  loading: boolean;
  onClick: () => void;
}

/** Fetches the next page of older updates. */
export default function LoadOlder({
  remaining,
  loading,
  onClick,
}: LoadOlderProps) {
  const intl = useIntl();
  if (remaining < 1) return null;
  return (
    <div className="bn-load-older">
      <button type="button" onClick={onClick} disabled={loading}>
        {loading
          ? intl.formatMessage(messages.loading)
          : intl.formatMessage(messages.older, { count: remaining })}
      </button>
    </div>
  );
}
