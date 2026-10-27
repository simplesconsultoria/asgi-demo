import { useIntl } from 'react-intl';
import { formatTime } from '../../helpers/format';
import type { UpdateMessage } from '../../types/breakingNews';

export interface UpdateCardProps {
  update: UpdateMessage;
  /** Arrived over the websocket since the reader last looked. */
  fresh?: boolean;
  /** IANA time zone for the time stamp; the reader's own when omitted. */
  timeZone?: string;
}

/**
 * One update on the timeline: when, a headline, and the body.
 *
 * The title is rendered as text. The body is the safe HTML Plone's
 * transforms produced, so it is rendered as markup.
 */
export default function UpdateCard({
  update,
  fresh = false,
  timeZone,
}: UpdateCardProps) {
  const intl = useIntl();
  return (
    <article
      className={`bn-update${fresh ? ' is-fresh' : ''}`}
      aria-labelledby={`bn-update-${update.uid}`}
    >
      <time className="bn-update-time" dateTime={update.datetime}>
        {formatTime(update.datetime, intl.locale, timeZone)}
      </time>
      <div className="bn-update-content">
        <h2 className="bn-update-title" id={`bn-update-${update.uid}`}>
          {update.title}
        </h2>
        {update.body && (
          <div
            className="bn-update-body"
            // Safe HTML from Plone's text/x-html-safe transform.
            dangerouslySetInnerHTML={{ __html: update.body }}
          />
        )}
      </div>
    </article>
  );
}
