import { createBrowserRouter } from 'react-router-dom';
import { UnifiedChatPage } from '@/components/pages/UnifiedChatPage';

interface RouterContext {
  dark: boolean;
  setDark: (d: boolean) => void;
}

export function createRouter(ctx: RouterContext) {
  return createBrowserRouter([
    {
      path: '/',
      element: <UnifiedChatPage dark={ctx.dark} setDark={ctx.setDark} />,
    },
    {
      path: '/chat/:documentId',
      element: <UnifiedChatPage dark={ctx.dark} setDark={ctx.setDark} />,
    },
  ]);
}
