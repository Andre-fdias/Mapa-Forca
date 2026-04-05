import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const Layout: React.FC = () => {
  return (
    <div className="flex bg-[#09090b] min-h-screen font-sans selection:bg-red-900/30 text-zinc-100">
      <Sidebar />
      <main className="flex-1 overflow-y-auto border-l border-zinc-800/80">
        <div className="p-8 max-w-[1400px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
