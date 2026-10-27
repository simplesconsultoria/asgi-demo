import { Fragment } from 'react';
import { useIntl } from 'react-intl';
import { formatDay } from '../../helpers/format';
import type { UpdateMessage } from '../../types/breakingNews';
import UpdateCard from './UpdateCard';

export interface TimelineProps {
  /** Updates, newest first. */
  items: UpdateMessage[];
  /** UIDs of updates to highlight. */
  fresh?: string[];
  timeZone?: string;
}

/** The story's updates, newest first, with a heading wherever the day changes. */
export default function Timeline({
  items,
  fresh = [],
  timeZone,
}: TimelineProps) {
  const intl = useIntl();
  let previousDay: string | null = null;
  return (
    <ol className="bn-timeline">
      {items.map((update) => {
        const day = formatDay(update.datetime, intl.locale, timeZone);
        const showDay = day !== previousDay;
        previousDay = day;
        return (
          <Fragment key={update.uid}>
            {showDay && (
              <li className="bn-timeline-day" aria-hidden="true">
                {day}
              </li>
            )}
            <li className="bn-timeline-item">
              <UpdateCard
                update={update}
                fresh={fresh.includes(update.uid)}
                timeZone={timeZone}
              />
            </li>
          </Fragment>
        );
      })}
    </ol>
  );
}
