import React, { useState } from 'react';
import { useGoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import useAuthStore from '../store/authStore';
import { 
  ShieldAlert, 
  Loader2, 
  Eye, 
  EyeOff, 
  AlertTriangle
} from 'lucide-react';
import heroImg from '../assets/hero.png';

const LoginForm: React.FC<{ 
  onLogin: (e: React.FormEvent, email: string, pass: string) => void,
  onGoogleLogin: () => void,
  isLoading: boolean,
  error: string | null
}> = ({ onLogin, onGoogleLogin, isLoading, error }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="w-full max-w-[340px] flex flex-col animate-in fade-in zoom-in-95 duration-300">
      <div className="lg:hidden flex items-center gap-3 mb-10 border-b border-zinc-800 pb-6">
        <div className="bg-red-950/40 p-2 border border-red-900/50 rounded">
          <ShieldAlert className="h-6 w-6 text-red-600" />
        </div>
        <div>
          <span className="block text-lg font-bold tracking-tight uppercase text-zinc-100">Mapa de Força</span>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-xl font-semibold text-zinc-100 tracking-tight">Acesso Operacional</h2>
      </div>

      {error && (
        <div className="mb-6 p-3 bg-[#1c0f0f] border-l-2 border-red-600 text-red-400 text-sm animate-in slide-in-from-top-2 duration-200">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <span className="font-medium">{error}</span>
          </div>
        </div>
      )}

      <form onSubmit={(e) => onLogin(e, email, password)} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">E-mail Institucional</label>
          <input 
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2.5 bg-[#121214] border border-zinc-700/80 rounded-[3px] text-[13px] text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-red-800 focus:bg-[#18181b] focus:ring-1 focus:ring-red-900/50 transition-colors font-sans"
            placeholder="usuario@instituicao.gov"
          />
        </div>

        <div className="space-y-1.5 pt-1">
          <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Senha</label>
          <div className="relative">
            <input 
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-3 pr-10 py-2.5 bg-[#121214] border border-zinc-700/80 rounded-[3px] text-[13px] text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-red-800 focus:bg-[#18181b] focus:ring-1 focus:ring-red-900/50 transition-colors font-sans font-mono"
              placeholder="••••••••"
            />
            <button 
              type="button" 
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full mt-6 bg-zinc-100 hover:bg-white text-zinc-900 shadow-[0_1px_2px_rgba(0,0,0,0.5)] text-[13px] font-bold py-2.5 rounded-[3px] flex items-center justify-center gap-2 transition-transform active:translate-y-[1px] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
             <Loader2 className="h-4 w-4 animate-spin text-zinc-600" />
          ) : (
             <span>Acessar Sistema</span>
          )}
        </button>
      </form>

      <div className="mt-8 flex items-center gap-4">
        <div className="h-px flex-1 bg-zinc-800"></div>
        <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Credencial Alternativa</span>
        <div className="h-px flex-1 bg-zinc-800"></div>
      </div>

      <button
        type="button"
        onClick={onGoogleLogin}
        disabled={isLoading}
        className="w-full mt-6 flex items-center justify-center gap-2.5 bg-transparent border border-zinc-700/60 hover:border-zinc-500 hover:bg-zinc-800/30 text-zinc-300 text-[13px] font-semibold py-2.5 rounded-[3px] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        Entrar com Google Institucional
      </button>

      <div className="mt-8 pt-6 border-t border-zinc-800/80">
        <p className="text-center text-[10px] text-zinc-500 font-bold uppercase tracking-[0.1em] flex items-center justify-center gap-2">
          <ShieldAlert className="h-3 w-3 text-zinc-600" />
          <span className="inline-block pt-0.5">Acesso Restrito ao Comando Geral</span>
        </p>
      </div>
    </div>
  );
};

const Login: React.FC = () => {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleSuccess = async (tokenResponse: any) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post('auth/social/google/', {
        access_token: tokenResponse.access_token,
      });
      const { access, user } = response.data;
      login(access, user);
      navigate('/');
    } catch (err: any) {
      console.error('Erro na autenticação social:', err);
      setError('Falha ao autenticar com o sistema central.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailLogin = async (e: React.FormEvent, email: string, pass: string) => {
    e.preventDefault();
    if (!email || !pass) {
      setError('Aviso: Credenciais incompletas.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post('auth/token/', {
        email,
        password: pass,
      });
      
      const { access, user } = response.data;
      login(access, user || { email });
      navigate('/');
    } catch (err: any) {
      console.error('Erro no login:', err);
      setError('Acesso negado. Credenciais operacionais inválidas.');
    } finally {
      setIsLoading(false);
    }
  };

  const loginGoogle = useGoogleLogin({
    onSuccess: handleGoogleSuccess,
    onError: () => setError('Autenticação cancelada pelo operador.'),
  });

  return (
    <div className="min-h-screen bg-[#09090b] flex font-sans selection:bg-red-900/30">
      
      {/* Coluna Esquerda - Imagem Institucional */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-zinc-950 border-r border-zinc-800/80">
        <img 
          src={heroImg} 
          alt="Mapa Força Hero background" 
          className="absolute inset-0 w-full h-full object-cover opacity-25 mix-blend-luminosity grayscale"
        />
        {/* Overlay Dark Escuro */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#09090b]/90 via-[#09090b]/70 to-transparent"></div>
        
        {/* Conteúdo Institucional em cima da imagem */}
        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div className="flex items-center gap-4">
            <div className="bg-red-950/40 p-3 border border-red-900/50 rounded flex-shrink-0 backdrop-blur-sm">
              <ShieldAlert className="h-8 w-8 text-red-600" />
            </div>
            <div>
              <span className="block text-3xl font-bold tracking-tight uppercase text-zinc-100 font-sans">Mapa de Força</span>
              <span className="text-xs font-semibold tracking-widest text-zinc-400 uppercase mt-0.5">Sistema Operacional Prontidão</span>
            </div>
          </div>

          <div className="max-w-base mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-zinc-900/80 border border-zinc-800/80 rounded-full mb-6 backdrop-blur-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse opacity-80"></span>
              <span className="text-[10px] font-bold text-zinc-300 uppercase tracking-widest">Acesso Governamental Restrito</span>
            </div>
            <h2 className="text-4xl max-w-md font-bold mb-6 leading-[1.15] text-zinc-100 pt-1 tracking-tight">
              Gestão diária de efetivo e viaturas
            </h2>
            <p className="text-sm max-w-sm text-zinc-400 font-medium leading-relaxed border-l-2 border-red-800 pl-4 pt-1">
              Painel de visão unificada do teatro de operações. Alocação dinâmica de Prontidão e visualização em tempo real.
            </p>
          </div>

          <div className="text-[10px] text-zinc-600 font-mono font-bold tracking-[0.2em] uppercase">
            &copy; {new Date().getFullYear()} Segurança e Defesa
          </div>
        </div>
      </div>

      {/* Coluna Direita - AuthCard */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 bg-[#09090b] relative">
        <LoginForm 
          onLogin={handleEmailLogin} 
          onGoogleLogin={loginGoogle}
          isLoading={isLoading}
          error={error}
        />
      </div>
    </div>
  );
};

export default Login;
