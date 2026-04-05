import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { Search, Plus, Trash2, Edit2, X, Check, MapPin, Building2 } from 'lucide-react';

interface Dictionary {
  id: number;
  tipo: string;
  codigo: string;
  nome: string;
}

interface Posto {
  id: number;
  nome: string;
  mapa_sgb: string;
  codigo_secao: string;
  descricao: string;
  tipo: number | null;
  ativo: boolean;
}

const Quarteis: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPosto, setEditingPosto] = useState<Posto | null>(null);
  
  const [formData, setFormData] = useState({
    nome: '',
    mapa_sgb: '',
    codigo_secao: '',
    descricao: '',
    tipo: '' as string | number,
    ativo: true
  });

  const { data: postos, isLoading } = useQuery<Posto[]>({
    queryKey: ['postos', searchTerm],
    queryFn: async () => {
      const response = await api.get(`postos/?search=${searchTerm}`);
      return response.data;
    }
  });

  const { data: dictTipos } = useQuery<Dictionary[]>({
    queryKey: ['dictionaries', 'TIPO_POSTO'],
    queryFn: async () => {
      const response = await api.get('dictionaries/?tipo=TIPO_POSTO');
      return response.data;
    }
  });

  const createMutation = useMutation({
    mutationFn: (newPosto: any) => api.post('postos/', newPosto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['postos'] });
      closeModal();
    }
  });

  const updateMutation = useMutation({
    mutationFn: (updatedPosto: any) => api.put(`postos/${updatedPosto.id}/`, updatedPosto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['postos'] });
      closeModal();
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`postos/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['postos'] });
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const dataToSend = { ...formData, tipo: formData.tipo === "" ? null : formData.tipo };
    if (editingPosto) {
      updateMutation.mutate({ ...dataToSend, id: editingPosto.id });
    } else {
      createMutation.mutate(dataToSend);
    }
  };

  const handleEdit = (posto: Posto) => {
    setEditingPosto(posto);
    setFormData({
      nome: posto.nome,
      mapa_sgb: posto.mapa_sgb || '',
      codigo_secao: posto.codigo_secao || '',
      descricao: posto.descricao || '',
      tipo: posto.tipo || '',
      ativo: posto.ativo
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingPosto(null);
    setFormData({ nome: '', mapa_sgb: '', codigo_secao: '', descricao: '', tipo: '', ativo: true });
  };

  const getTipoNome = (tipoId: number | null) => {
    if (!tipoId) return 'NÃO CLASSIFICADO';
    return dictTipos?.find(d => d.id === tipoId)?.nome || `INDEF (${tipoId})`;
  };

  return (
    <div className="font-sans">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <div className="bg-red-950/40 border border-red-900/50 p-2.5 rounded flex-shrink-0">
            <Building2 className="h-6 w-6 text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-zinc-100 uppercase tracking-tight">Quartéis e Postos</h1>
            <p className="text-xs text-zinc-500 font-mono tracking-wider uppercase mt-1">Sessões e Unidades Operacionais</p>
          </div>
        </div>
        
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center justify-center gap-2 bg-red-700 hover:bg-red-600 text-white px-5 py-2.5 rounded-[3px] transition-transform active:translate-y-[1px] font-bold shadow-[0_1px_2px_rgba(0,0,0,0.5)] text-xs uppercase tracking-wider"
        >
          <Plus className="h-4 w-4" />
          Registrar Base
        </button>
      </header>

      <div className="bg-[#121214] rounded-[3px] border border-zinc-800 shadow-[0_2px_15px_rgba(0,0,0,0.4)] mb-6 overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-[#0c0c0e]">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input 
              type="text" 
              placeholder="Buscar unidade pelo nome ou seção..."
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
                <th className="px-6 py-4">SGB / Subgrupo</th>
                <th className="px-6 py-4">Nominação Oficial</th>
                <th className="px-6 py-4">Classificação (Tipo)</th>
                <th className="px-6 py-4">Código Seção</th>
                <th className="px-6 py-4 text-center">Status</th>
                <th className="px-6 py-4 text-center">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/80">
              {isLoading ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">Inspecionando Regiões...</td></tr>
              ) : postos?.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-12 text-center text-zinc-600 font-mono text-xs uppercase tracking-widest">Nenhuma base localizada.</td></tr>
              ) : (
                postos?.map((posto) => (
                  <tr key={posto.id} className="hover:bg-zinc-900/50 transition-colors group">
                    <td className="px-6 py-4 text-zinc-400 font-mono text-xs tracking-widest">
                      {posto.mapa_sgb || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-bold text-zinc-100 uppercase text-sm tracking-wide">{posto.nome}</span>
                        <span className="text-[10px] text-zinc-500 font-mono uppercase mt-0.5">{posto.descricao || 'SEM DESCRITIVO'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-zinc-300 text-sm">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-3.5 w-3.5 text-zinc-500" />
                        <span className="text-xs uppercase font-bold text-zinc-400">{getTipoNome(posto.tipo)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono font-medium text-emerald-500 bg-emerald-950/20 px-2 py-1 rounded-sm border border-emerald-900/30 text-xs">
                        {posto.codigo_secao || 'S/N'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`px-2.5 py-1.5 rounded-sm text-[10px] font-bold border uppercase tracking-wider ${posto.ativo ? 'bg-zinc-800 text-zinc-300 border-zinc-700' : 'bg-red-950/30 text-red-500 border-red-900/50'}`}>
                        {posto.ativo ? 'ATIVA' : 'INATIVA'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => handleEdit(posto)}
                          className="p-1 hover:text-blue-400 text-zinc-500 transition-colors"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => deleteMutation.mutate(posto.id)}
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
          <div className="bg-[#121214] rounded-[3px] border border-zinc-800 shadow-[0_0_50px_rgba(0,0,0,0.8)] w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-zinc-800 flex justify-between items-center bg-[#0c0c0e]">
              <h2 className="text-lg font-bold text-zinc-100 uppercase tracking-tight">
                {editingPosto ? 'Modificar Base Operacional' : 'Nova Base Operacional'}
              </h2>
              <button onClick={closeModal} className="p-2 hover:bg-zinc-800 rounded-[3px] transition-colors">
                <X className="h-5 w-5 text-zinc-500 hover:text-red-500" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Denominação (Pública)</label>
                <input 
                  required
                  placeholder="EX: ZONA NORTE"
                  className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all placeholder:text-zinc-700 uppercase"
                  value={formData.nome}
                  onChange={(e) => setFormData({...formData, nome: e.target.value.toUpperCase()})}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">SGB Matriz</label>
                  <input 
                    placeholder="1º SGB"
                    className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all placeholder:text-zinc-700 uppercase"
                    value={formData.mapa_sgb}
                    onChange={(e) => setFormData({...formData, mapa_sgb: e.target.value.toUpperCase()})}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Código Único (Seção)</label>
                  <input 
                    placeholder="703151000"
                    className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all placeholder:text-zinc-700 uppercase"
                    value={formData.codigo_secao}
                    onChange={(e) => setFormData({...formData, codigo_secao: e.target.value})}
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Definição Operacional</label>
                <input 
                  placeholder="DESCRIÇÃO COMPLETA DA BASE"
                  className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-100 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all placeholder:text-zinc-700 uppercase"
                  value={formData.descricao}
                  onChange={(e) => setFormData({...formData, descricao: e.target.value.toUpperCase()})}
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Classificação Dicionário (Tipo)</label>
                <select 
                  className="w-full px-3 py-2.5 bg-[#09090b] border border-zinc-800 rounded-[3px] text-xs font-mono font-bold text-zinc-300 focus:ring-1 focus:ring-red-900/50 focus:border-red-800 outline-none transition-all uppercase"
                  value={formData.tipo}
                  onChange={(e) => setFormData({...formData, tipo: e.target.value})}
                >
                  <option value="">INDEFINIDO</option>
                  {dictTipos?.map(d => <option key={d.id} value={d.id}>{d.nome} ({d.codigo})</option>)}
                </select>
              </div>
              
              <div className="pt-2 flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="ativo"
                  className="w-4 h-4 bg-zinc-900 border-zinc-700 rounded-sm text-red-600 focus:ring-red-600 focus:ring-2"
                  checked={formData.ativo}
                  onChange={(e) => setFormData({...formData, ativo: e.target.checked})}
                />
                <label htmlFor="ativo" className="text-xs uppercase font-bold text-zinc-400">Posto Ativo</label>
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

export default Quarteis;
