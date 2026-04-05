import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { 
  LayoutDashboard, 
  Users, 
  Truck, 
  Calendar, 
  ChevronLeft, 
  ChevronRight,
  Copy,
  PlusCircle,
  AlertCircle,
  Edit3
} from 'lucide-react';
import { format, addDays, subDays } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import AlocacaoModal from '../components/AlocacaoModal';

interface Posto {
  id: number;
  nome: string;
}

interface AlocacaoFuncionario {
  id: number;
  posto: number;
  funcionario: string;
  identidade_militar: string;
  funcao: string;
}

interface AlocacaoViatura {
  id: number;
  posto: number;
  viatura: string;
  viatura_prefixo: string;
  viatura_municipio?: string;
  viatura_garagem?: string;
  viatura_tipo_nome?: string;
  status_no_dia_codigo?: string;
  status_no_dia_nome?: string;
}

interface MapaDiario {
  id: number;
  data: string;
  alocacoes_funcionarios: AlocacaoFuncionario[];
  alocacoes_viaturas: AlocacaoViatura[];
}

const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [selectedPosto, setSelectedPosto] = useState<Posto | null>(null);
  const dateStr = format(selectedDate, 'yyyy-MM-dd');

  // Buscar Postos
  const { data: postos } = useQuery<Posto[]>({
    queryKey: ['postos'],
    queryFn: async () => (await api.get('postos/')).data
  });

  // Buscar Mapa do Dia
  const { data: mapa, isLoading: isLoadingMapa } = useQuery<MapaDiario>({
    queryKey: ['mapa', dateStr],
    queryFn: async () => {
      const response = await api.get(`mapas/?data=${dateStr}`);
      return response.data[0] || null;
    }
  });

  // Mutação para criar novo mapa
  const createMapaMutation = useMutation({
    mutationFn: async () => (await api.post('mapas/', { data: dateStr })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mapa', dateStr] })
  });

  // Mutação para clonar mapa
  const cloneMapaMutation = useMutation({
    mutationFn: async () => {
      const prevDate = format(subDays(selectedDate, 1), 'yyyy-MM-dd');
      return (await api.post('mapas/clone/', { 
        data_origem: prevDate, 
        data_destino: dateStr 
      })).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mapa', dateStr] })
  });

  const handlePrevDay = () => setSelectedDate(subDays(selectedDate, 1));
  const handleNextDay = () => setSelectedDate(addDays(selectedDate, 1));
  const handleToday = () => setSelectedDate(new Date());

  const getFuncsByPosto = (postoId: number) => 
    mapa?.alocacoes_funcionarios.filter(a => a.posto === postoId) || [];

  const getViatsByPosto = (postoId: number) => 
    mapa?.alocacoes_viaturas.filter(a => a.posto === postoId) || [];

  return (
    <div className="space-y-6 font-sans">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="bg-red-950/40 p-2.5 border border-red-900/50 rounded flex-shrink-0">
            <LayoutDashboard className="h-6 w-6 text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-zinc-100 tracking-tight uppercase">Painel de Comando</h1>
            <p className="text-xs text-zinc-500 font-mono tracking-wider uppercase mt-1">Gestão de Efetivo e Viaturas</p>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-[#121214] p-1.5 rounded-[3px] border border-zinc-800/80 shadow-[0_2px_10px_rgba(0,0,0,0.5)]">
          <button onClick={handlePrevDay} className="p-2 hover:bg-zinc-800 rounded-sm transition-colors text-zinc-400 hover:text-zinc-100">
            <ChevronLeft className="h-5 w-5" />
          </button>
          
          <div className="flex items-center gap-2 px-4 py-2 bg-[#09090b] rounded-sm border border-zinc-800">
            <Calendar className="h-4 w-4 text-zinc-500" />
            <span className="font-mono text-sm text-zinc-200 min-w-[140px] text-center capitalize tracking-wide">
              {format(selectedDate, "dd MMM yyyy", { locale: ptBR })}
            </span>
          </div>

          <button onClick={handleNextDay} className="p-2 hover:bg-zinc-800 rounded-sm transition-colors text-zinc-400 hover:text-zinc-100">
            <ChevronRight className="h-5 w-5" />
          </button>
          
          <div className="h-6 w-[1px] bg-zinc-800 mx-1"></div>
          
          <button 
            onClick={handleToday}
            className="px-3 py-2 text-[11px] font-bold text-red-500 hover:text-red-400 hover:bg-red-950/30 rounded-sm transition-colors uppercase tracking-widest"
          >
            HOJE
          </button>
        </div>
      </header>

      {!mapa && !isLoadingMapa ? (
        <div className="bg-[#121214] rounded-[3px] p-12 border-2 border-dashed border-zinc-800 flex flex-col items-center justify-center text-center space-y-5 shadow-sm mt-8">
          <div className="bg-zinc-900 p-4 border border-zinc-800 rounded">
            <AlertCircle className="h-10 w-10 text-zinc-600" />
          </div>
          <div className="max-w-md">
            <h2 className="text-lg font-bold text-zinc-100 uppercase tracking-wide">Ausência de Tabela Operacional</h2>
            <p className="text-zinc-500 text-sm mt-2 font-mono">Defina a alocação do dia baseada em um mapa em branco ou clone o arranjo anterior.</p>
          </div>
          <div className="flex gap-4 pt-4">
            <button 
              onClick={() => createMapaMutation.mutate()}
              className="flex items-center gap-2 bg-red-700 hover:bg-red-600 text-white px-6 py-2.5 rounded-[3px] text-xs font-bold uppercase tracking-wider transition-colors"
            >
              <PlusCircle className="h-4 w-4" />
              Inicializar Prontidão
            </button>
            <button 
              onClick={() => cloneMapaMutation.mutate()}
              className="flex items-center gap-2 bg-transparent border border-zinc-700 hover:bg-zinc-800 text-zinc-300 px-6 py-2.5 rounded-[3px] text-xs font-bold uppercase tracking-wider transition-colors"
            >
              <Copy className="h-4 w-4" />
              Importar Dia Anterior
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-8">
          {postos?.map((posto) => {
            const funcs = getFuncsByPosto(posto.id);
            const viats = getViatsByPosto(posto.id);
            const isEmpty = funcs.length === 0 && viats.length === 0;

            return (
              <div 
                key={posto.id} 
                onClick={() => setSelectedPosto(posto)}
                className={`group cursor-pointer bg-[#121214] rounded-[3px] border transition-all duration-200 overflow-hidden flex flex-col
                  ${isEmpty ? 'border-zinc-800/80 hover:border-zinc-600' : 'border-zinc-700 hover:border-red-800'}
                `}
              >
                <div className="p-4 flex-1">
                  <div className="flex justify-between items-start mb-5">
                    <h3 className="text-[13px] font-bold text-zinc-100 uppercase tracking-wide line-clamp-1 group-hover:text-red-400 transition-colors">
                      {posto.nome}
                    </h3>
                    <div className="flex items-center gap-2">
                       <Edit3 className="h-3 w-3 text-zinc-600 group-hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all" />
                       <span className="text-[9px] font-mono font-bold bg-zinc-900 border border-zinc-800 text-zinc-500 px-1.5 py-0.5 rounded-sm uppercase">
                         ID:{posto.id}
                       </span>
                    </div>
                  </div>
                  
                  <div className="space-y-5">
                    <section>
                      <div className="flex items-center gap-2 text-[9px] font-bold text-zinc-600 uppercase tracking-[0.2em] mb-2">
                        <Users className="h-3 w-3" />
                        <span>Efetivo Alocado</span>
                      </div>
                      <div className="space-y-1.5 min-h-[40px]">
                        {funcs.length > 0 ? funcs.map(f => (
                          <div key={f.id} className="flex items-center justify-between text-xs bg-[#0c0c0e] py-1.5 px-2 rounded-sm border border-zinc-800/50">
                            <span className="font-mono text-zinc-300 font-medium">{f.identidade_militar}</span>
                            <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider">{f.funcao}</span>
                          </div>
                        )) : (
                          <p className="text-[10px] text-zinc-600 font-mono italic px-1">Ninguém alocado</p>
                        )}
                      </div>
                    </section>

                    <section>
                      <div className="flex items-center gap-2 text-[9px] font-bold text-zinc-600 uppercase tracking-[0.2em] mb-2">
                        <Truck className="h-3 w-3" />
                        <span>Viatura Restrita</span>
                      </div>
                      <div className="flex flex-col gap-1.5 min-h-[30px]">
                        {viats.length > 0 ? viats.map(v => {
                           let bgCol = "bg-zinc-950/20";
                           let borderCol = "border-zinc-800";
                           let textCol = "text-zinc-400";
                           
                           if (v.status_no_dia_codigo === 'OPERANDO') {
                             bgCol = "bg-emerald-950/20"; borderCol = "border-emerald-900/40"; textCol = "text-emerald-400";
                           } else if (v.status_no_dia_codigo === 'BAIXADO' || v.status_no_dia_codigo === 'MANUTENCAO') {
                             bgCol = "bg-red-950/20"; borderCol = "border-red-900/40"; textCol = "text-red-400";
                           } else if (v.status_no_dia_codigo === 'RESERVA') {
                             bgCol = "bg-yellow-950/20"; borderCol = "border-yellow-900/40"; textCol = "text-yellow-400";
                           }
                           
                           return (
                             <div key={v.id} className={`group/tooltip relative flex items-center justify-between px-2.5 py-1.5 ${bgCol} rounded-[3px] border ${borderCol} cursor-default`}>
                               <div className="flex items-center gap-2">
                                 <span className={`font-mono text-[11px] font-bold ${textCol}`}>{v.viatura_prefixo}</span>
                                 <span className="text-zinc-600/50 text-[10px]">|</span>
                                 <span className={`text-[9px] font-bold uppercase tracking-wider ${textCol}`}>{v.status_no_dia_nome || 'OPERANDO'}</span>
                               </div>
                               
                               {/* Tooltip Hover (Realístico) */}
                               <div className="absolute left-1/2 top-[110%] -translate-x-1/2 mt-1 w-[180px] bg-[#0c0c0e] border border-zinc-700/80 p-3 rounded-[3px] opacity-0 invisible group-hover/tooltip:opacity-100 group-hover/tooltip:visible transition-all z-[99] shadow-[0_5px_20px_rgba(0,0,0,0.8)] before:content-[''] before:absolute before:-top-1.5 before:left-1/2 before:-translate-x-1/2 before:border-4 before:border-transparent before:border-b-zinc-700">
                                  <div className="text-[10px] font-bold text-zinc-100 uppercase tracking-widest mb-2 border-b border-zinc-800 pb-1">{v.viatura_tipo_nome || 'Veículo Base'}</div>
                                  <table className="w-full text-left font-mono text-[9px] text-zinc-400">
                                    <tbody>
                                      <tr>
                                        <td className="py-0.5 text-zinc-600">MUNICÍPIO</td>
                                        <td className="py-0.5 text-right font-medium text-zinc-300">{v.viatura_municipio || 'SEDE'}</td>
                                      </tr>
                                      <tr>
                                        <td className="py-0.5 text-zinc-600">GARAGEM</td>
                                        <td className="py-0.5 text-right font-medium text-zinc-300">{v.viatura_garagem || 'PRINCIPAL'}</td>
                                      </tr>
                                    </tbody>
                                  </table>
                               </div>
                             </div>
                           );
                        }) : (
                          <p className="text-[10px] text-zinc-600 font-mono italic px-1">Sem viaturas</p>
                        )}
                      </div>
                    </section>
                  </div>
                </div>
                
                <div className="bg-[#09090b] px-4 py-2 border-t border-zinc-800/80 flex justify-between items-center group-hover:bg-red-950/10 transition-colors mt-auto">
                  <span className={`text-[9px] font-bold uppercase tracking-widest ${isEmpty ? 'text-zinc-600' : 'text-emerald-500'}`}>
                    {isEmpty ? 'Aguardando Escala' : 'Posto Operacional'}
                  </span>
                  {!isEmpty && <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse outline outline-2 outline-emerald-500/20"></div>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal de Alocação */}
      {selectedPosto && mapa && (
        <AlocacaoModal 
          mapaId={mapa.id}
          postoId={selectedPosto.id}
          postoNome={selectedPosto.nome}
          onClose={() => setSelectedPosto(null)}
          alocacoesFunc={getFuncsByPosto(selectedPosto.id)}
          alocacoesViat={getViatsByPosto(selectedPosto.id)}
        />
      )}
    </div>
  );
};

export default Dashboard;
