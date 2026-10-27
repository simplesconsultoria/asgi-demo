import type { ConfigType } from '@plone/registry';
import BreakingNewsView from '../components/BreakingNews/BreakingNewsView';
import breakingNews from '../reducers/breakingNews';

declare module '@plone/types' {
  export interface SettingsConfig {
    breakingNews: {
      /**
       * Base URL of the stories' websockets. Empty: the page's own host,
       * under the API rule (`/++api++/++asgi++`). Set it to reach a backend
       * directly, as in development, where Volto's proxy does not forward
       * websocket upgrades.
       */
      socketBase?: string;
    };
  }
}

export default function install(config: ConfigType) {
  config.views.contentTypesViews.BreakingNews = BreakingNewsView;

  config.addonReducers = {
    ...config.addonReducers,
    breakingNews,
  };

  // Ask for the first page of updates with the content itself, so the
  // story is rendered on the server in one request.
  config.settings.apiExpanders = [
    ...config.settings.apiExpanders,
    { match: '', GET_CONTENT: ['breaking-news'] },
  ];

  config.settings.breakingNews = {
    socketBase: process.env.RAZZLE_BREAKING_NEWS_SOCKET_BASE || '',
  };

  return config;
}
