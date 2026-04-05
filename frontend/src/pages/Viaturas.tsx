import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { Truck, Search, Plus, Trash2, Edit2, X, Check, MapPin } from 'lucide-react';

interface Dictionary {
  id: number;
  tipo: string;
  codigo: string;
  nome: string;
}

interface Posto {
  id: number;
  nome: string;
}

interface Viatura {
  prefixo: string;
  placa: string;
  posto_base: number | null;
  posto_base_nome?: string;
  status_base: number | null;
  status_base_nome?: string;
  status_base_codigo?: string;
}

const Viaturas: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingViat, setEditingViat] = useState<Viatura | null>(null);
  
  const [formData, setFormData] = useState({
    prefixo: '',
    placa: '',
    posto_base: '' as string | number,
    status_base: '' as string | number
  });

  const { data: viaturas, isLoading } = useQuery<Viatura[]>({
    queryKey: ['viaturas', searchTerm],
    queryFn: async () => {
      const response = await api.get(`viaturas/?search=${searchTerm}`);
      return response.data;
    }
  });

  const { data: postos } = useQuery<Posto[]>({
    queryKey: ['postos'],
    queryFn: async () => {
      const response = await api.get('postos/');
      return response.data;
    }
  });

  const { data: dictStatus } = useQuery<Dictionary[]>({
    queryKey: ['dictionaries', 'STATUS_VIATURA'],
    queryFn: async () => {
      const response = await api.get('dictionaries/?tipo=STATUS_VIATURA');
      return response.data;
    }
  });

  const createMutation = useMutation({
    mutationFn: (newViat: any) => api.post('viaturas/', newViat),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['viaturas'] });
      closeModal();
    }
  });

  const updateMutation = useMutation({
    mutationFn: (updatedViat: any) => api.put(`viaturas/${updatedViat.prefixo}/`, updatedViat),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['viaturas'] });
      closeModal();
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (prefixo: string) => api.delete(`viaturas/${prefixo}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['viaturas'] });
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const dataToSend = { 
      ...formData, 
      posto_base: formData.posto_base === "" ? null : formData.posto_base,
      status_base: formData.status_base === "" ? null : formData.status_base
    };
    if (editingViat) {
      updateMutation.mutate(dataToSend);
    } else {
      createMutation.mutate(dataToSend);
    }
  };

  const handleEdit = (viat: Viatura) => {
    setEditingViat(viat);
    setFormData({
      prefixo: viat.prefixo,
      placa: viat.placa || '',
      posto_base: viat.posto_base || '',
      status_base: viat.status_base || ''
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingViat(null);
    setFormData({ prefixo: '', placa: '', posto_base: '', status_base: '' });
  };

  const getStatusColor = (codigo: string = '') => {
    switch (codigo) {
      case 'OPERANDO': return 'bg-emerald-950/30 text-emerald-500 border-emerald-900/50';
      case 'BAIXADO': return 'bg-red-950/30 text-red-500 border-red-900/50';
      case 'MANUTENCAO': return 'bg-orange-950/30 text-orange-500 border-orange-900/50';
      case 'RESERVA': return 'bg-zinc-900 text-zinc-400 border-zinc-800';
      default: return 'bg-zinc-900 text-zinc-400 border-zinc-800';
    }
  };

  return (
    <div className="font-sans">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <div className="bg-red-950/40 border border-red-900/50 p-2.5 rounded flex-shrink-0">
            <Truck className="h-6 w-6 text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-zinc-100 uppercase tracking-tight">Frota</h1>
            <p className="text-xs text-zinc-500 font-mono tracking-wider uppercase mt-1">Controle de Viaturas</p>
          </div>
        </div>
        
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center justify-center gap-2 bg-red-700 hover:bg-red-600 text-white px-5 py-2.5 rounded-[3px] transition-transform active:translate-y-[1px] font-bold shadow-[0_1px_2px_rgba(0,0,0,0.5)] text-xs uppercase tracking-wider"
        >
          <Plus className="h-4 w-4" />
          Registrar Viatura
        </button>
      </header>

      <div className="bg-[#121214] rounded-[3px] border border-zinc-800 shadow-[0_2px_15px_rgba(0,0,0,0.4)] mb-6 overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-[#0c0c0e]">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input 
              type="text" 
              placeholder="Buscar por prefixo ou placa..."
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
                <th className="px-6 py-4">Prefixo</th>
                <th className="px-6 py-4">Placa</th>
                <th className="px-6 py-4">Posto Base</th>
                <th className="px-6 py-4">Status Base</th>
                <th className="px-6 py-4 text-center">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/80">
              {isLoading ? (
                <tr><td colSpan={5} className="px-6 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">Inspecionando Frota...</td></tr>
              ) : viaturas?.length === 0 ? (
                <tr><td colSpan={5} className="px-6 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">Nenhuma viatura localizada.</td></tr>
              ) : (
                viaturas?.map((viat) => (
                  <tr key={viat.prefixo} className="hover:bg-zinc-900/50 transition-colors group">
                    <td className="px-6 py-4 font-bold text-zinc-100 uppercase text-sm tracking-wide">{viat.prefixo}</td>
                    <td className="px-6 py-4 font-mono font-medium text-zinc-400 text-sm">{viat.placa || '-'}</td>
                    <td className="px-6 py-4 text-zinc-300 text-sm">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-3.5 w-3.5 text-zinc-500" />
                        {viat.posto_base_nome || <span className="italic text-zinc-600">Não alocado</span>}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1.5 rounded-sm text-[10px] font-bold border uppercase tracking-wider ${getStatusColor(viat.status_base_codigo)}`}>
                        {viat.status_base_nome || 'EM ATRIBUIÇÃO'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => handleEdit(viat)}
                          className="p-1 hover:text-blue-400 text-zinc-500 transition-colors"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => deleteMutation.mutate(viat.prefixo)}
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
                {editingViat ? 'Modificar Viatura' : 'Nova Viatura'}
              </h2>
              <button onClick={closeModal} className="p-2 hover:bg-zinc-800 rounded-[3px] transition-colors">
                <X className="h-5 w-5 text-zinc-500 hover:text-red-500" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Prefixo Patrulha (PK)</label>
                  <input 
                    required
                    disabled={!!editingViat}
                    placeholder="L-10"
                    className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all placeholder:text-zinc-700 disabled:opacity-50 uppercase"
                    value={formData.prefixo}
                    onChange={(e) => setFormData({...formData, prefixo: e.target.value.toUpperCase()})}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Placa de Identificação</label>
                  <input 
                    placeholder="ABC-1234"
                    className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all placeholder:text-zinc-700 uppercase"
                    value={formData.placa}
                    onChange={(e) => setFormData({...formData, placa: e.target.value.toUpperCase()})}
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Ancoragem (Posto Base)</label>
                <select 
                  className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-300 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all uppercase"
                  value={formData.posto_base}
                  onChange={(e) => setFormData({...formData, posto_base: e.target.value})}
                >
                  <option value="">NÃO ATRIBUÍDO</option>
                  {postos?.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2 mt-2">Status da Frota (Dicionário)</label>
                <div className="grid grid-cols-2 gap-2">
                  {dictStatus?.map(status => (
                    <button
                      key={status.id}
                      type="button"
                      onClick={() => setFormData({...formData, status_base: status.id})}
                      className={`px-3 py-2.5 rounded-[3px] text-[10px] font-bold uppercase tracking-wider border transition-all ${
                        formData.status_base === status.id 
                        ? 'bg-red-950/40 border-red-800 text-red-500 shadow-[0_0_10px_rgba(220,38,38,0.2)]' 
                        : 'bg-[#09090b] border-zinc-800 text-zinc-500 hover:border-zinc-600'
                      }`}
                    >
                      {status.nome}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-6 flex gap-3">
                <button 
                  type="button"
                  onClick={closeModal}
                  className="flex-1 bg-transparent border border-zinc-700 hover:bg-zinc-800 text-zinc-300 py-2.5 rounded-[3px] text-xs font-bold uppercase tracking-wider transition-all"
                >
                  Regressar
                </button>
                <button 
                  type="submit"
                  className="flex-1 bg-red-700 text-white px-4 py-2.5 rounded-[3px] hover:bg-red-600 font-bold uppercase text-xs tracking-wider shadow-[0_1px_2px_rgba(0,0,0,0.5)] transition-all flex items-center justify-center gap-2 active:translate-y-[1px]"
                >
                  <Check className="h-4 w-4" />
                  Consolidar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Viaturas;
