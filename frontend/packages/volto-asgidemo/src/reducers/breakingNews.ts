import { GET_BREAKING_NEWS } from '../actions/breakingNews';
import type { BreakingNewsListing } from '../types/breakingNews';

export interface BreakingNewsRequestState {
  loading: boolean;
  loaded: boolean;
  error: unknown;
  /** The last page fetched. */
  data: BreakingNewsListing | null;
}

const initialState: BreakingNewsRequestState = {
  loading: false,
  loaded: false,
  error: null,
  data: null,
};

interface Action {
  type: string;
  result?: BreakingNewsListing;
  error?: unknown;
}

/** Request state of the last `@breaking-news` page fetched. */
export default function breakingNews(
  state: BreakingNewsRequestState = initialState,
  action: Action = { type: '' },
): BreakingNewsRequestState {
  switch (action.type) {
    case `${GET_BREAKING_NEWS}_PENDING`:
      return { ...state, loading: true, loaded: false, error: null };
    case `${GET_BREAKING_NEWS}_SUCCESS`:
      return {
        loading: false,
        loaded: true,
        error: null,
        data: action.result ?? null,
      };
    case `${GET_BREAKING_NEWS}_FAIL`:
      return { ...state, loading: false, loaded: false, error: action.error };
    default:
      return state;
  }
}
