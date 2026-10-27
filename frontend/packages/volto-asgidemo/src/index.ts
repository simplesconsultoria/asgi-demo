import type { ConfigType } from '@plone/registry';
import installBreakingNews from './config/breakingNews';
import installSettings from './config/settings';

function applyConfig(config: ConfigType) {
  installSettings(config);
  installBreakingNews(config);

  return config;
}

export default applyConfig;
