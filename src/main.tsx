import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react';
import App from './App';
import './index.css';

/**
 * Theme Configuration
 * -------------------
 * The Porsche Design System supports two themes: "light" (default) and "dark".
 *
 * To switch themes, change the `theme` prop below:
 *   - theme="light"  (default — white background, dark text)
 *   - theme="dark"   (dark background, light text)
 *
 * Individual components can also override the theme via their own `theme` prop.
 *
 * For Tailwind CSS theme-aware color tokens, add a class to <html>:
 *   document.documentElement.classList.add('dark');  // enables dark theme tokens
 *   document.documentElement.classList.add('auto');  // follows system preference
 */
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PorscheDesignSystemProvider theme="light">
      <App />
    </PorscheDesignSystemProvider>
  </StrictMode>
);
