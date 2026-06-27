import { createBrowserRouter } from 'react-router-dom';

// Placeholder routes — pages are implemented in E9/E10/E11
const router = createBrowserRouter([
  {
    path: '/',
    element: <div className="p-8 text-foreground">RegVia — Upload a document to get started.</div>,
  },
  {
    path: '/chat/:documentId',
    element: <div className="p-8 text-foreground">Chat page — coming in E10.</div>,
  },
]);

export default router;
