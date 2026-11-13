import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import '../../../../packages/design/tokens.css';
import './app.css';
import { App } from './App';

try {
  if (localStorage.getItem('ansimon-theme') === 'dark') document.documentElement.dataset.theme = 'dark';
} catch {
  /* 저장소를 못 쓰면 밝은 화면 */
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
