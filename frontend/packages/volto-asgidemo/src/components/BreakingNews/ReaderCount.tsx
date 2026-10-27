import { defineMessages, useIntl } from 'react-intl';
import { roundReaders } from '../../helpers/format';

const messages = defineMessages({
  readers: {
    id: 'breakingNewsReaders',
    defaultMessage:
      '{readers, plural, one {# person reading} other {About # people reading}}',
  },
});

export interface ReaderCountProps {
  /** Readers across every backend; `null` until the first count arrives. */
  readers: number | null;
}

/** "About 1,200 people reading": approximate by design. */
export default function ReaderCount({ readers }: ReaderCountProps) {
  const intl = useIntl();
  if (readers === null || readers < 1) return null;
  return (
    <span className="bn-readers">
      {intl.formatMessage(messages.readers, { readers: roundReaders(readers) })}
    </span>
  );
}
