import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { 
  X, 
  UserPlus, 
  Truck, 
  Trash2, 
  CheckCircle2, 
  UserCheck,
  ShieldCheck,
  PlusCircle
} from 'lucide-react';

interface Props {
  mapaId: number;
  postoId: number;
  postoNome: string;
  onClose: () => void;
  alocacoesFunc: any[];
  alocacoesViat: any[];
}

const AlocacaoModal: React.FC<Props> = ({ 
  mapaId, postoId, postoNome, onClose, alocacoesFunc, alocacoesViat 
}) => {
  const queryClient = useQueryClient();
  const [funcao, setFuncao] = useState('AUXILIAR');
  const [statusViat, setStatusViat] = useState('OPERANDO');

  // Buscar todos os funcionários para filtrar os disponíveis
  const { data: todosFuncionarios } = useQuery<any[]>({
    queryKey: ['funcionarios'],
    queryFn: async () => (await api.get('funcionarios/')).data
  });

  // Buscar todas as viaturas para filtrar as disponíveis
  const { data: todasViaturas } = useQuery<any[]>({
    queryKey: ['viaturas'],
    queryFn: async () => (await api.get('viaturas/')).data
  });

  // Mutação: Adicionar Funcionário
  const addFuncMutation = useMutation({
    mutationFn: (funcionarioRe: string) => api.post('alocacoes-funcionarios/', {
      mapa: mapaId,
      posto: postoId,
      funcionario: funcionarioRe,
      funcao: funcao
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mapa'] })
  });

  // Mutação: Adicionar Viatura
  const addViatMutation = useMutation({
    mutationFn: (viaturaPrefixo: string) => api.post('alocacoes-viaturas/', {
      mapa: mapaId,
      posto: postoId,
      viatura: viaturaPrefixo,
      status_no_dia: statusViat
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mapa'] })
  });

  // Mutação: Remover Alocação
  const removeAlocMutation = useMutation({
    mutationFn: (params: { type: 'func' | 'viat', id: number }) => 
      api.delete(`alocacoes-${params.type === 'func' ? 'funcionarios' : 'viaturas'}/${params.id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mapa'] })
  });

  const disponiveisFunc = todosFuncionarios?.filter(f => 
    !alocacoesFunc.some(a => a.funcionario === f.re)
  ) || [];

  const disponiveisViat = todasViaturas?.filter(v => 
    !alocacoesViat.some(a => a.viatura === v.prefixo)
  ) || [];

  return (
    <div className="fixed inset-0 bg-[#09090b]/90 backdrop-blur-sm flex items-center justify-center z-50 p-4 font-sans">
      <div className="bg-[#121214] rounded-[3px] shadow-[0_0_50px_rgba(0,0,0,0.8)] w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden border border-zinc-800">
        
        {/* Header */}
        <div className="p-6 border-b border-zinc-800 bg-[#0c0c0e] flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="bg-red-950/40 border border-red-900/50 p-3 rounded flex-shrink-0">
              <ShieldCheck className="h-6 w-6 text-red-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-zinc-100 uppercase tracking-tight">{postoNome}</h2>
              <p className="text-[10px] uppercase text-zinc-500 font-mono tracking-widest mt-1">Gestão de Escala e Prontidão</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-[3px] transition-all text-zinc-500 hover:text-red-500 border border-transparent hover:border-zinc-700">
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-8 grid grid-cols-1 lg:grid-cols-2 gap-10">
          
          {/* Coluna Efetivo */}
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-2">
                <UserCheck className="h-5 w-5 text-zinc-400" />
                <h3 className="font-bold text-zinc-300 uppercase text-xs tracking-widest">Efetivo Escalado</h3>
              </div>
              <span className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-2.5 py-1 rounded-sm text-[10px] font-bold tracking-wider">{alocacoesFunc.length} MILITARES</span>
            </div>

            <div className="space-y-2 min-h-[150px]">
              {alocacoesFunc.map(a => (
                <div key={a.id} className="flex items-center justify-between p-3 bg-[#0c0c0e] border border-zinc-800/80 rounded-[3px] group hover:border-zinc-500 transition-all">
                  <div>
                    <p className="text-sm font-mono text-zinc-100">{a.identidade_militar}</p>
                    <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider mt-1">{a.funcao}</p>
                  </div>
                  <button 
                    onClick={() => removeAlocMutation.mutate({ type: 'func', id: a.id })}
                    className="p-2 text-zinc-600 hover:text-red-500 hover:bg-red-950/30 border border-transparent hover:border-red-900/50 rounded-[3px] transition-all opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {alocacoesFunc.length === 0 && (
                <div className="h-32 flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded-[3px] bg-[#0c0c0e]/50 text-zinc-600">
                   <p className="text-[11px] uppercase font-mono tracking-widest">Nenhum militar escalado</p>
                </div>
              )}
            </div>

            <div className="pt-4 space-y-3">
              <div className="flex gap-2">
                <select 
                  className="flex-1 p-2.5 bg-[#0c0c0e] border border-zinc-800 rounded-[3px] text-xs font-bold text-zinc-300 uppercase tracking-wider outline-none focus:ring-1 focus:ring-red-900/50 focus:border-red-800 transition-all font-mono"
                  value={funcao}
                  onChange={(e) => setFuncao(e.target.value)}
                >
                  <option value="COMANDANTE">COMANDANTE</option>
                  <option value="MOTORISTA">MOTORISTA</option>
                  <option value="AUXILIAR">AUXILIAR</option>
                  <option value="SENTINELA">SENTINELA</option>
                </select>
              </div>
              <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                {disponiveisFunc.map(f => (
                  <button
                    key={f.re}
                    onClick={() => addFuncMutation.mutate(f.re)}
                    className="flex items-center justify-between p-3 text-left border border-zinc-800 bg-[#0c0c0e] rounded-[3px] hover:bg-zinc-900 hover:border-zinc-600 transition-all group"
                  >
                    <span className="text-xs font-mono text-zinc-400 group-hover:text-zinc-100 transition-colors">{f.identidade_militar}</span>
                    <UserPlus className="h-4 w-4 text-zinc-600 group-hover:text-red-500 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Coluna Viaturas */}
          <div className="space-y-6">
             <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-2">
                <Truck className="h-5 w-5 text-red-600" />
                <h3 className="font-bold text-zinc-300 uppercase text-xs tracking-widest">Frota Alocada</h3>
              </div>
              <span className="bg-red-950/40 border border-red-900/50 text-red-500 px-2.5 py-1 rounded-sm text-[10px] font-bold tracking-wider">{alocacoesViat.length} VEÍCULOS</span>
            </div>

            <div className="space-y-2 min-h-[150px]">
              {alocacoesViat.map(a => (
                <div key={a.id} className="flex items-center justify-between p-3 bg-red-950/10 border border-red-900/20 rounded-[3px] group hover:border-red-900/60 transition-all">
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                    <div>
                      <p className="text-sm font-mono text-zinc-100">{a.viatura_prefixo}</p>
                      <p className="text-[10px] text-red-500 font-bold uppercase tracking-wider mt-1">{a.status_no_dia}</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => removeAlocMutation.mutate({ type: 'viat', id: a.id })}
                    className="p-2 text-zinc-600 hover:text-red-500 hover:bg-red-950/30 border border-transparent hover:border-red-900/50 rounded-[3px] transition-all opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {alocacoesViat.length === 0 && (
                <div className="h-32 flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded-[3px] bg-[#0c0c0e]/50 text-zinc-600">
                   <p className="text-[11px] uppercase font-mono tracking-widest">Nenhuma viatura alocada</p>
                </div>
              )}
            </div>

            <div className="pt-4 space-y-3">
              <div className="flex gap-2">
                <select 
                  className="flex-1 p-2.5 bg-[#0c0c0e] border border-zinc-800 rounded-[3px] text-xs font-bold text-zinc-300 uppercase tracking-wider outline-none focus:ring-1 focus:ring-red-900/50 focus:border-red-800 transition-all font-mono"
                  value={statusViat}
                  onChange={(e) => setStatusViat(e.target.value)}
                >
                  <option value="OPERANDO">OPERANDO</option>
                  <option value="BAIXADO">BAIXADO</option>
                  <option value="RESERVA">RESERVA</option>
                </select>
              </div>
              <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                {disponiveisViat.map(v => (
                  <button
                    key={v.prefixo}
                    onClick={() => addViatMutation.mutate(v.prefixo)}
                    className="flex items-center justify-between p-3 text-left border border-zinc-800 bg-[#0c0c0e] rounded-[3px] hover:bg-zinc-900 hover:border-red-900/50 transition-all group"
                  >
                    <span className="text-xs font-mono text-zinc-400 group-hover:text-red-400 transition-colors">{v.prefixo} ({v.placa})</span>
                    <PlusCircle className="h-4 w-4 text-zinc-600 group-hover:text-red-500 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 bg-[#0c0c0e] border-t border-zinc-800 flex justify-end">
          <button 
            onClick={onClose}
            className="bg-zinc-100 text-zinc-900 hover:bg-white px-8 py-2.5 rounded-[3px] text-[13px] font-bold shadow-[0_1px_2px_rgba(0,0,0,0.5)] transition-all flex items-center gap-2 active:translate-y-[1px]"
          >
            <CheckCircle2 className="h-4 w-4" />
            <span className="uppercase tracking-widest">Confirmar Alocação</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AlocacaoModal;
