import { defineMessages, useIntl } from 'react-intl';
import type { ConnectionState } from '../../types/breakingNews';

const messages = defineMessages({
  connecting: {
    id: 'breakingNewsConnecting',
    defaultMessage: 'Connecting to live updates…',
  },
  live: {
    id: 'breakingNewsReceiving',
    defaultMessage: 'Updates appear automatically',
  },
  reconnecting: {
    id: 'breakingNewsReconnecting',
    defaultMessage: 'Connection lost, reconnecting…',
  },
  refused: {
    id: 'breakingNewsRefused',
    defaultMessage:
      'Live updates are unavailable. Reload the page for the latest.',
  },
});

export interface ConnectionStatusProps {
  state: ConnectionState;
}

/** One line telling the reader whether new updates will appear on their own. */
export default function ConnectionStatus({ state }: ConnectionStatusProps) {
  const intl = useIntl();
  if (state === 'stopped') return null;
  return (
    <p className={`bn-connection is-${state}`} role="status" aria-live="polite">
      {intl.formatMessage(messages[state])}
    </p>
  );
}
