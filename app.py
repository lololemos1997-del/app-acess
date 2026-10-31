import streamlit as st
import yfinance as yf
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Análise de Ações Avançado",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Dashboard de Análise de Ações (Técnico + Fundamentalista + IFR + Bollinger)")
st.markdown("Insira o ticker do ativo na barra lateral para ver o diagnóstico completo com múltiplos indicadores.")

# Barra lateral para inputs
st.sidebar.header("Configurações")
ticker_input = st.sidebar.text_input("Ticker do Ativo (ex: PETR4.SA)", value="PETR4.SA").upper()

periodo = st.sidebar.selectbox(
    "Período do Histórico do Gráfico",
    options=["1mo", "6mo", "1y", "5y", "max"],
    index=2
)

if ticker_input:
    try:
        # Busca dados do Yahoo Finance (garantindo histórico suficiente para cálculos)
        acao = yf.Ticker(ticker_input)
        info = acao.info
        hist = acao.history(period="1y") # Corrigido de periodo para period
        
        if not hist.empty and len(hist) > 30:
            # Extração de informações básicas
            nome = info.get("longName", ticker_input)
            preco_atual = info.get("currentPrice", info.get("regularMarketPrice", hist["Close"].iloc[-1]))
            setor = info.get("sector", "Não disponível")
            
            # --- CÁLCULO DOS INDICADORES TÉCNICOS ---
            
            # 1. Média Móvel Aritmética de 21 períodos (MMA 21)
            hist['MMA21'] = hist['Close'].rolling(window=21).mean()
            mma21 = hist['MMA21'].iloc[-1]
            
            # 2. Média Móvel de 200 períodos (MMA 200)
            if len(hist) >= 200:
                mma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            else:
                mma200 = hist['Close'].mean()
                
            # 3. IFR (Índice de Força Relativa - 14 períodos)
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            hist['RSI'] = 100 - (100 / (1 + rs))
            ifr_atual = hist['RSI'].iloc[-1]
            
            # 4. Bandas de Bollinger (20 períodos, 2 desvios padrão)
            hist['BB_Middle'] = hist['Close'].rolling(window=20).mean()
            hist['BB_Std'] = hist['Close'].rolling(window=20).std()
            hist['BB_Upper'] = hist['BB_Middle'] + (2 * hist['BB_Std'])
            hist['BB_Lower'] = hist['BB_Middle'] - (2 * hist['BB_Std'])
            
            bb_upper = hist['BB_Upper'].iloc[-1]
            bb_lower = hist['BB_Lower'].iloc[-1]
            bb_middle = hist['BB_Middle'].iloc[-1]

            # Indicadores Fundamentalistas
            pl = info.get("trailingPE", None)
            dy = info.get("dividendYield", None)
            dy_val = (dy * 100) if dy else 0.0

            # Tape Reading / Momento de Curto Prazo (últimos 5 dias)
            preco_5_dias_atras = hist["Close"].iloc[-5]
            variacao_curto_prazo = ((preco_atual - preco_5_dias_atras) / preco_5_dias_atras) * 100

            # --- SISTEMA DE PONTUAÇÃO E SINALIZAÇÃO ---
            pontos = 0
            razoes = []

            # Fundamentalista
            if pl and 0 < pl < 20:
                pontos += 1
                razoes.append(f"🟢 **Fundamentalista:** P/L atrativo ({pl:.2f}).")
            elif pl and pl >= 20:
                razoes.append(f"🔴 **Fundamentalista:** P/L elevado ({pl:.2f}).")
            else:
                razoes.append("🟡 **Fundamentalista:** P/L neutro ou indisponível.")

            if dy_val > 4.0:
                pontos += 1
                razoes.append(f"🟢 **Dividend Yield:** Saudável ({dy_val:.2f}%).")
            else:
                razoes.append(f"🟡 **Dividend Yield:** Baixo ou nulo ({dy_val:.2f}%).")

            # Técnico: Tendência Longo Prazo (MMA 200) e Curto Prazo (MMA 21)
            if preco_atual > mma200:
                pontos += 1
                razoes.append("🟢 **Técnico (MMA 200):** Preço acima da média de longo prazo (Tendência de alta).")
            else:
                pontos -= 1
                razoes.append("🔴 **Técnico (MMA 200):** Preço abaixo da média de longo prazo.")

            if preco_atual > mma21:
                pontos += 1
                razoes.append(f"🟢 **Técnico (MMA 21):** Preço acima da média de 21 períodos (R$ {mma21:.2f}).")
            else:
                pontos -= 1
                razoes.append(f"🔴 **Técnico (MMA 21):** Preço abaixo da média de 21 períodos (R$ {mma21:.2f}).")

            # IFR (Índice de Força Relativa)
            if 30 <= ifr_atual <= 65:
                pontos += 1
                razoes.append(f"🟢 **IFR (14):** Zona saudável/neutra ({ifr_atual:.1f}), sem sobrecompra extrema.")
            elif ifr_atual < 30:
                pontos += 1
                razoes.append(f"🟢 **IFR (14):** Ativo em região de **Sobrevenda** ({ifr_atual:.1f}) — Oportunidade potencial de repique.")
            else:
                pontos -= 1
                razoes.append(f"🔴 **IFR (14):** Ativo em **Sobrecompra** ({ifr_atual:.1f}), risco de correção técnica.")

            # Bandas de Bollinger
            if preco_atual <= bb_lower:
                pontos += 1
                razoes.append(f"🟢 **Bandas de Bollinger:** Preço testou ou rompeu a **Banda Inferior** (Possível suporte forte).")
            elif preco_atual >= bb_upper:
                pontos -= 1
                razoes.append(f"🔴 **Bandas de Bollinger:** Preço tocou ou rompeu a **Banda Superior** (Esticado para cima).")
            else:
                razoes.append(f"🟡 **Bandas de Bollinger:** Preço oscilando normalmente dentro das bandas.")

            # Fluxo / Curto Prazo
            if variacao_curto_prazo > 0:
                pontos += 1
                razoes.append(f"🟢 **Fluxo Recente:** Alta de {variacao_curto_prazo:.2f}% nos últimos 5 pregões.")
            else:
                pontos -= 1
                razoes.append(f"🔴 **Fluxo Recente:** Queda de {variacao_curto_prazo:.2f}% nos últimos 5 pregões.")

            # Decisão Final
            if pontos >= 3:
                sinal_texto = "VISÃO DE VALORIZAÇÃO (SINAL VERDE)"
                box_color = "success"
            else:
                sinal_texto = "PERCEPÇÃO DE QUEDA / CAUTELA (SINAL VERMELHO)"
                box_color = "error"

            # --- EXIBIÇÃO NA TELA ---
            st.header(f"{nome} ({ticker_input})")
            
            if box_color == "success":
                st.success(f"### 🟢 {sinal_texto} (Pontuação técnica/fundamental: {pontos})")
            else:
                st.error(f"### 🔴 {sinal_texto} (Pontuação técnica/fundamental: {pontos})")

            # Métricas em destaque
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Preço Atual", f"R$ {preco_atual:.2f}")
            with col2:
                st.metric("IFR (14)", f"{ifr_atual:.1f}")
            with col3:
                st.metric("MMA 21", f"R$ {mma21:.2f}" if mma21 else "N/A")
            with col4:
                st.metric("P/L", f"{pl:.2f}" if pl else "N/A")
            with col5:
                st.metric("Dividend Yield", f"{dy_val:.2f}%")

            st.divider()

            # Detalhes do Diagnóstico
            st.subheader("🔍 Diagnóstico Detalhado por Indicador")
            for r in razoes:
                st.markdown(f"- {r}")

            st.divider()

            # Gráficos e Médias
            st.subheader(f"Gráfico de Preços e Médias Móveis ({periodo})")
            hist_periodo = acao.history(period=periodo) # Corrigido de periodo para period
            if not hist_periodo.empty:
                hist_periodo['MMA21'] = hist_periodo['Close'].rolling(window=21).mean()
                st.line_chart(hist_periodo[["Close", "MMA21"]])
            
        else:
            st.warning("Histórico insuficiente para calcular os indicadores técnicos avançados (mínimo de 30 dias necessários).")
            
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os dados: {e}")

else:
    st.info("Insira um ticker na barra lateral para começar.")
