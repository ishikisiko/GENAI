import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import {
  getComponentChunkLinks,
  getFontFaceStyles,
  getFontLinks,
  getIconLinks,
  getInitialStyles,
} from '@porsche-design-system/components-react/partials';

const appTitle = 'GraphRAG Crisis Strategy Simulation';
const faviconSvg =
  'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%224%22 fill=%22%230E1418%22/%3E%3Cpath d=%22M8 9h16v3H12v3h9v3h-9v5H8V9Z%22 fill=%22%23fff%22/%3E%3C/svg%3E';

const getLocalMetaTagsAndIconLinks = () =>
  [
    '<meta name=theme-color content=#FFF media=(prefers-color-scheme:light)>',
    '<meta name=theme-color content=#0E1418 media=(prefers-color-scheme:dark)>',
    '<meta name=mobile-web-app-capable content=yes>',
    '<meta name=apple-mobile-web-app-status-bar-style content=default>',
    `<meta name=apple-mobile-web-app-title content="${appTitle}">`,
    '<meta name=msapplication-TileColor content=#FFF>',
    `<link rel=icon type=image/svg+xml href="${faviconSvg}">`,
  ].join('');

const transformIndexHtmlPlugin = () => {
  return {
    name: 'html-transform',
    transformIndexHtml(html: string) {
      const headPartials = [
        getInitialStyles(),
        getFontFaceStyles(),
        getFontLinks({ weights: ['regular', 'semi-bold', 'bold'] }),
        getComponentChunkLinks(),
        getIconLinks(),
        getLocalMetaTagsAndIconLinks(),
      ].join('');

      return html.replace(/<\/head>/, `${headPartials}</head>`);
    },
  };
};

export default defineConfig({
  plugins: [react(), tailwindcss(), transformIndexHtmlPlugin()],
});
