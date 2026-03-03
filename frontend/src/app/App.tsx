import React from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import Workbench from './pages/Workbench';

function WorkbenchRoot() {
  return (
    <div className="h-screen overflow-hidden">
      <Workbench />
    </div>
  );
}

const router = createBrowserRouter([
  { path: "/",     Component: WorkbenchRoot },
  { path: "/chat", Component: WorkbenchRoot },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
