import { defineMessages, useIntl } from 'react-intl';

const messages = defineMessages({
  newUpdates: {
    id: 'breakingNewsNewUpdates',
    defaultMessage: '{count, plural, one {# new update} other {# new updates}}',
  },
});

export interface NewUpdatesBannerProps {
  /** Updates that arrived since the reader last looked at the top. */
  count: number;
  onClick: () => void;
}

/** A floating button that takes the reader back up to what just arrived. */
export default function NewUpdatesBanner({
  count,
  onClick,
}: NewUpdatesBannerProps) {
  const intl = useIntl();
  if (count < 1) return null;
  return (
    <button type="button" className="bn-new-updates" onClick={onClick}>
      <span aria-hidden="true">↑ </span>
      {intl.formatMessage(messages.newUpdates, { count })}
    </button>
  );
}
