import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  Truck, 
  LogOut,
  ChevronRight,
  UserCircle,
  Building2
} from 'lucide-react';
import useAuthStore from '../store/authStore';

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/funcionarios', icon: Users, label: 'Efetivo' },
    { path: '/viaturas', icon: Truck, label: 'Frota' },
    { path: '/quarteis', icon: Building2, label: 'Quartéis' },
  ];

  return (
    <aside className="w-[260px] bg-[#0c0c0e] flex flex-col h-screen sticky top-0 font-sans">
      <div className="p-6 border-b border-zinc-800/80">
        <div className="flex items-center gap-3">
          <div className="bg-red-950/40 p-2 border border-red-900/50 rounded flex-shrink-0">
            <LayoutDashboard className="h-5 w-5 text-red-600" />
          </div>
          <span className="font-bold text-lg tracking-tight uppercase text-zinc-100">Mapa de Força</span>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-bold text-zinc-600 uppercase tracking-[0.15em] mb-2 mt-4">
          Navegação Operacional
        </div>
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) => `
              flex items-center justify-between px-3 py-2.5 rounded-[3px] transition-colors duration-200 group relative
              ${isActive 
                ? 'bg-zinc-900 border border-zinc-800' 
                : 'border border-transparent hover:bg-zinc-900/50 hover:border-zinc-800'}
            `}
          >
            {({ isActive }) => (
              <>
                {/* Linha vermelha no item ativo lado esquerdo */}
                {isActive && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-3/4 bg-red-600 rounded-r-sm shadow-[0_0_8px_rgba(220,38,38,0.5)]"></div>}
                
                <div className="flex items-center gap-3 w-full pl-2">
                  <item.icon className={`h-[18px] w-[18px] transition-colors ${
                    isActive ? 'text-zinc-100' : 'text-zinc-500 group-hover:text-zinc-300'
                  }`} />
                  <span className={`text-[13px] font-semibold tracking-wide ${isActive ? 'text-white' : 'text-zinc-400 group-hover:text-zinc-200'}`}>
                    {item.label}
                  </span>
                </div>
                <ChevronRight className={`h-4 w-4 transition-colors ${isActive ? 'text-zinc-700' : 'text-zinc-700 opacity-0 group-hover:opacity-100'}`} />
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-zinc-800/80 bg-[#09090b] flex flex-col gap-4 shadow-[inset_0_5px_15px_-10px_rgba(0,0,0,0.5)]">
        {user && (
          <div className="flex items-center gap-3 px-2 mb-2">
            <UserCircle className="h-8 w-8 text-zinc-600" />
            <div className="flex flex-col">
              <span className="text-[13px] font-bold text-zinc-200 leading-tight">
                {user.first_name?.toUpperCase() || user.username?.toUpperCase() || 'OPERADOR'}
              </span>
              <span className="text-[10px] text-zinc-500 font-mono tracking-wider truncate w-36">
                {user.email}
              </span>
            </div>
          </div>
        )}
        
        <button 
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-transparent border border-zinc-800 text-zinc-400 hover:text-red-400 hover:border-red-900/50 hover:bg-red-950/20 rounded-[3px] transition-all duration-200"
        >
          <LogOut className="h-4 w-4" />
          <span className="font-semibold text-[13px] uppercase tracking-wider">Encerrar Sessão</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
