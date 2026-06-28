import { createBrowserRouter } from 'react-router-dom';
import { LandingPage } from '@/components/pages/LandingPage';
import { AuthCallbackPage } from '@/components/pages/AuthCallbackPage';
import { UnifiedChatPage } from '@/components/pages/UnifiedChatPage';
import { ProtectedRoute } from '@/components/templates/ProtectedRoute';

interface RouterContext {
  dark: boolean;
  setDark: (d: boolean) => void;
}

export function createRouter(ctx: RouterContext) {
  return createBrowserRouter([
    {
      path: '/',
      element: <LandingPage dark={ctx.dark} setDark={ctx.setDark} />,
    },
    {
      path: '/auth/callback',
      element: <AuthCallbackPage />,
    },
    {
      path: '/chat',
      element: (
        <ProtectedRoute>
          <UnifiedChatPage dark={ctx.dark} setDark={ctx.setDark} />
        </ProtectedRoute>
      ),
    },
    {
      path: '/chat/:sessionId',
      element: (
        <ProtectedRoute>
          <UnifiedChatPage dark={ctx.dark} setDark={ctx.setDark} />
        </ProtectedRoute>
      ),
    },
  ]);
}
