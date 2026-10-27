import type { ComponentType, PropsWithChildren, ReactElement } from 'react';
import { IntlProvider as BaseIntlProvider } from 'react-intl';
import { render } from '@testing-library/react';
import type { UpdateMessage } from '../../types/breakingNews';

// react-intl 3, which Volto ships, types its provider for React before 18,
// when components received children implicitly.
const IntlProvider = BaseIntlProvider as unknown as ComponentType<
  PropsWithChildren<{ locale: string; messages: Record<string, string> }>
>;

/** Render inside the providers the components need. */
export function renderWithIntl(ui: ReactElement) {
  return render(
    <IntlProvider locale="en" messages={{}}>
      {ui}
    </IntlProvider>,
  );
}

/** An update with sensible defaults. */
export function makeUpdate(
  overrides: Partial<UpdateMessage> = {},
): UpdateMessage {
  return {
    v: 1,
    kind: 'update',
    story: 'story-uid',
    uid: 'update-uid',
    datetime: '2026-10-04T17:00:00+00:00',
    created: '2026-10-04T17:00:05+00:00',
    title: 'Polls close',
    body: '<p>Counting begins now.</p>',
    ...overrides,
  };
}
