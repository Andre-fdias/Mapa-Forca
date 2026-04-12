# 🎨 Interface (Frontend)

O frontend do **Mapa-Força** prioriza a performance e a simplicidade, utilizando uma abordagem **HTML-first**.

## 🚀 Tecnologias Core

### 🌊 Tailwind CSS
- **Propósito**: Estilização moderna e rápida via classes utilitárias.
- **Configuração**: O projeto utiliza o app `theme` (Django-Tailwind). O arquivo `tailwind.config.js` está configurado para monitorar todos os templates Django e arquivos Python em busca de classes.
- **Build**: As classes são processadas pelo PostCSS para gerar um arquivo `dist/styles.css` minificado contendo apenas o CSS utilizado.

### ⚡ HTMX
- **Propósito**: Transformar o HTML estático em uma interface dinâmica sem escrever JavaScript customizado.
- **Uso**:
    - `hx-post`: Envio de dados de alocação de guarnição.
    - `hx-target`: Define qual elemento do DOM será atualizado com a resposta do servidor.
    - `hx-swap`: Define como a substituição será feita (ex: `innerHTML`, `outerHTML`).
    - `hx-trigger`: Gatilhos para disparar ações (ex: `keyup changed delay:500ms` para busca em tempo real).

### 🏔️ Alpine.js (Opcional)
- **Propósito**: Gerenciar pequenos estados locais no navegador que não requerem ida ao servidor (ex: abrir modais, dropdowns de menu).

---

## 🏗️ Estrutura de Templates

O sistema utiliza a herança de templates do Django de forma extensiva:

1. **`base.html`**: O "esqueleto" do sistema. Carrega o CSS do Tailwind, o JS do HTMX e a estrutura da Navbar e Sidebar.
2. **`layout/`**: Define o posicionamento das áreas de conteúdo.
3. **`partials/`**: Fragmentos de interface que representam componentes reutilizáveis ou áreas de atualização do HTMX.

### 🧩 Exemplo de Componentização (HTMX)
O card de uma viatura é um partial: `templates/escalas/partials/card_viatura_alocada.html`. 

Quando um militar é adicionado, o HTMX chama a view do Django, que processa a lógica e retorna **apenas este arquivo partial** renderizado. O HTMX então substitui o card antigo pelo novo na tela.

---

## 💅 Temas e Cores
O sistema utiliza uma paleta de cores institucional:
- **Cor Primária**: Vermelho (`bg-red-600`) para elementos de destaque e botões de ação operacional.
- **Cor Secundária**: Tons de cinza (`bg-slate-900`) para a barra lateral e fundos de página, garantindo contraste e legibilidade.
- **Status**:
    - ✅ **Verde**: Viatura com guarnição completa.
    - ⚠️ **Laranja**: Viatura em manutenção ou incompleta.
    - 🛑 **Vermelho**: Viatura baixada.

---

## 📱 Responsividade
O sistema é **Mobile-First**. Tabelas longas são convertidas em cards empilhados em telas menores para facilitar o preenchimento da escala via tablets ou smartphones por oficiais em campo.
