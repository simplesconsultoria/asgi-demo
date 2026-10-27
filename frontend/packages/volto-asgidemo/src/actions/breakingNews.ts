import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

export const GET_BREAKING_NEWS = 'GET_BREAKING_NEWS';

/**
 * Fetch a page of a story's updates from `@breaking-news`.
 *
 * @param url - The story's URL.
 * @param bStart - Updates to skip.
 * @param bSize - Updates per page.
 */
export function getBreakingNews(url: string, bStart = 0, bSize = 20) {
  return {
    type: GET_BREAKING_NEWS,
    request: {
      op: 'get',
      path: `${flattenToAppURL(url)}/@breaking-news?b_start=${bStart}&b_size=${bSize}`,
    },
  };
}
