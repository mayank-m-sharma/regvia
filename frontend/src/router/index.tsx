import { createBrowserRouter } from 'react-router-dom';
import { UploadPage } from '@/components/pages/UploadPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <UploadPage />,
  },
  {
    path: '/chat/:documentId',
    element: <div className="p-8 text-foreground">Chat page — coming in E10.</div>,
  },
]);

export default router;
