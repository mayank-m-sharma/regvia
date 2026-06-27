import { createBrowserRouter } from 'react-router-dom';
import { UploadPage } from '@/components/pages/UploadPage';
import { ChatPage } from '@/components/pages/ChatPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <UploadPage />,
  },
  {
    path: '/chat/:documentId',
    element: <ChatPage />,
  },
]);

export default router;
