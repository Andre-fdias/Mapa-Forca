import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { Users, Search, Plus, Trash2, Edit2, X, Check } from 'lucide-react';

interface Dictionary {
  id: number;
  tipo: string;
  codigo: string;
  nome: string;
}

interface Funcionario {
  re: string;
  nome_completo: string;
  nome_guerra: string;
  posto_graduacao: number | null;
  identidade_militar: string;
}

const Funcionarios: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingFunc, setEditingFunc] = useState<Funcionario | null>(null);
  
  const [formData, setFormData] = useState({
    re: '',
    nome_completo: '',
    nome_guerra: '',
    posto_graduacao: '' as string | number
  });

  const { data: funcionarios, isLoading } = useQuery<Funcionario[]>({
    queryKey: ['funcionarios', searchTerm],
    queryFn: async () => {
      const response = await api.get(`funcionarios/?search=${searchTerm}`);
      return response.data;
    }
  });

  const { data: dictPostos } = useQuery<Dictionary[]>({
    queryKey: ['dictionaries', 'POSTO_GRADUACAO'],
    queryFn: async () => {
      const response = await api.get('dictionaries/?tipo=POSTO_GRADUACAO');
      return response.data;
    }
  });

  const createMutation = useMutation({
    mutationFn: (newFunc: any) => api.post('funcionarios/', newFunc),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['funcionarios'] });
      closeModal();
    }
  });

  const updateMutation = useMutation({
    mutationFn: (updatedFunc: any) => api.put(`funcionarios/${updatedFunc.re}/`, updatedFunc),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['funcionarios'] });
      closeModal();
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (re: string) => api.delete(`funcionarios/${re}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['funcionarios'] });
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const dataToSend = { 
      ...formData, 
      posto_graduacao: formData.posto_graduacao === "" ? null : formData.posto_graduacao 
    };
    if (editingFunc) {
      updateMutation.mutate(dataToSend);
    } else {
      createMutation.mutate(dataToSend);
    }
  };

  const handleEdit = (func: Funcionario) => {
    setEditingFunc(func);
    setFormData({
      re: func.re,
      nome_completo: func.nome_completo,
      nome_guerra: func.nome_guerra,
      posto_graduacao: func.posto_graduacao || ''
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingFunc(null);
    setFormData({ re: '', nome_completo: '', nome_guerra: '', posto_graduacao: '' });
  };

  return (
    <div className="font-sans">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <div className="bg-red-950/40 border border-red-900/50 p-2.5 rounded flex-shrink-0">
            <Users className="h-6 w-6 text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-zinc-100 uppercase tracking-tight">Efetivo</h1>
            <p className="text-xs text-zinc-500 font-mono tracking-wider uppercase mt-1">Gerenciamento de Funcionários</p>
          </div>
        </div>
        
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center justify-center gap-2 bg-zinc-100 hover:bg-white text-zinc-900 px-5 py-2.5 rounded-[3px] transition-transform active:translate-y-[1px] font-bold shadow-[0_1px_2px_rgba(0,0,0,0.5)] text-xs uppercase tracking-wider"
        >
          <Plus className="h-4 w-4" />
          Incluir Militar
        </button>
      </header>

      <div className="bg-[#121214] rounded-[3px] border border-zinc-800 shadow-[0_2px_15px_rgba(0,0,0,0.4)] mb-6 overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-[#0c0c0e]">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input 
              type="text" 
              placeholder="Buscar por nome, RE ou nome de guerra..."
              className="w-full pl-10 pr-4 py-2 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none text-zinc-100 placeholder:text-zinc-600 transition-all font-medium"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#09090b] text-zinc-500 text-[10px] uppercase font-bold tracking-[0.15em] border-b border-zinc-800">
                <th className="px-6 py-4">Identidade Militar</th>
                <th className="px-6 py-4">Nome Completo</th>
                <th className="px-6 py-4 text-center">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/80">
              {isLoading ? (
                <tr><td colSpan={3} className="px-6 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">Localizando Efetivo...</td></tr>
              ) : funcionarios?.length === 0 ? (
                <tr><td colSpan={3} className="px-6 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">Nenhum registro encontrado.</td></tr>
              ) : (
                funcionarios?.map((func) => (
                  <tr key={func.re} className="hover:bg-zinc-900/50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="bg-zinc-900 border border-zinc-800 text-zinc-400 px-2.5 py-1.5 rounded-sm text-[10px] font-bold uppercase tracking-wider">
                          {func.identidade_militar.split(' ')[0]} {/* Grab prefixo posto */}
                        </span>
                        <span className="font-mono font-medium text-zinc-300 text-sm tracking-wide">{func.re}</span>
                        <span className="font-bold text-zinc-100 uppercase text-sm ml-2">{func.nome_guerra}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-zinc-400 text-sm">{func.nome_completo}</td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => handleEdit(func)}
                          className="p-1 hover:text-blue-400 text-zinc-500 transition-colors"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => deleteMutation.mutate(func.re)}
                          className="p-1 hover:text-red-500 text-zinc-500 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-[#09090b]/90 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#121214] rounded-[3px] border border-zinc-800 shadow-[0_0_50px_rgba(0,0,0,0.8)] w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-[#0c0c0e]">
              <h2 className="text-lg font-bold text-zinc-100 uppercase tracking-tight">
                {editingFunc ? 'Editar Oficial' : 'Registrar Novo Oficial'}
              </h2>
              <button onClick={closeModal} className="p-2 hover:bg-zinc-800 rounded-[3px] transition-colors">
                <X className="h-5 w-5 text-zinc-500 hover:text-red-500" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Registro (RE)</label>
                <input 
                  required
                  disabled={!!editingFunc}
                  placeholder="000000-0"
                  className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all placeholder:text-zinc-700 disabled:opacity-50"
                  value={formData.re}
                  onChange={(e) => setFormData({...formData, re: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Nome Completo</label>
                <input 
                  required
                  className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-sans font-medium text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all"
                  value={formData.nome_completo}
                  onChange={(e) => setFormData({...formData, nome_completo: e.target.value.toUpperCase()})}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Nome de Guerra</label>
                  <input 
                    required
                    className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-sans font-bold uppercase text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all"
                    value={formData.nome_guerra}
                    onChange={(e) => setFormData({...formData, nome_guerra: e.target.value.toUpperCase()})}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Posto/Graduação</label>
                  <select 
                    className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all uppercase"
                    value={formData.posto_graduacao}
                    onChange={(e) => setFormData({...formData, posto_graduacao: e.target.value})}
                  >
                    <option value="">INDEFINIDO</option>
                    {dictPostos?.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}
                  </select>
                </div>
              </div>

              <div className="pt-6 flex gap-3">
                <button 
                  type="button"
                  onClick={closeModal}
                  className="flex-1 bg-transparent border border-zinc-700 hover:bg-zinc-800 text-zinc-300 py-2.5 rounded-[3px] text-xs font-bold uppercase tracking-wider transition-all"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="flex-1 bg-zinc-100 text-zinc-900 py-2.5 rounded-[3px] hover:bg-white text-xs font-bold uppercase tracking-wider shadow-[0_1px_2px_rgba(0,0,0,0.5)] transition-all flex items-center justify-center gap-2 active:translate-y-[1px]"
                >
                  <Check className="h-4 w-4" />
                  Salvar Ficha
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Funcionarios;
