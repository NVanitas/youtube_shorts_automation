# YouTube Shorts Automation Pipeline (em Inglês)

Este projeto automatiza a criação de vídeos curtos (Shorts, Reels, TikToks) em inglês focados no mercado internacional para maximizar ganhos de monetização.

O pipeline é capaz de:
1. Gerar um roteiro dinâmico e otimizado para retenção usando o **Gemini API**.
2. Gerar voz neural de altíssima qualidade (realista) usando **Edge-TTS** (grátis e sem chaves).
3. Transcrever o áudio palavra por palavra e gerar legendas estilizadas de karaokê (com preenchimento de cor dinâmico) usando **Stable-TS (Whisper)**.
4. Juntar áudio de voz, música de fundo e vídeo de fundo (cortando para 9:16 vertical), aplicando as legendas automaticamente via **FFmpeg**.

---

## 🛠️ Pré-requisitos

1. **Python 3.9 a 3.11** (Recomendado) instalado e adicionado ao PATH do Windows.
2. **FFmpeg**: O script usa a biblioteca `static-ffmpeg` que baixa e configura o FFmpeg automaticamente no primeiro uso. Você não precisa configurar o FFmpeg manualmente!

---

## 🚀 Instalação e Configuração

### 1. Criar um Ambiente Virtual (Recomendado)
Abra o PowerShell ou Prompt de Comando na pasta do projeto e execute:
```powershell
python -m venv venv
venv\Scripts\activate
```

### 2. Instalar Dependências
Com o ambiente virtual ativado, instale as bibliotecas necessárias:
```powershell
pip install -r requirements.txt
```

### 3. Configurar Chaves de API
Abra o arquivo `.env` e configure:
*   `GEMINI_API_KEY`: Insira sua chave obtida gratuitamente no [Google AI Studio](https://aistudio.google.com/).
*   `PEXELS_API_KEY` (Opcional): Insira sua chave obtida gratuitamente no [Pexels API](https://www.pexels.com/api/) para que o script baixe automaticamente novos vídeos de fundo de acordo com o nicho.
    *   *Nota:* Se não configurar a chave do Pexels, o pipeline usará vídeos de exemplo padrão ou qualquer vídeo `.mp4` colocado na pasta `assets/backgrounds/<nicho>/`.

---

## 📦 Estrutura de Pastas e Mídia Customizada

Você pode colocar seus próprios arquivos de mídia para criar vídeos mais exclusivos:
*   **Vídeos de Fundo:** Coloque vídeos verticais ou horizontais `.mp4` em `assets/backgrounds/facts/` ou `assets/backgrounds/stoicism/`. O script escolherá um arquivo aleatório dessa pasta. (Se a pasta estiver vazia e você não tiver chave Pexels, um vídeo de amostra será baixado).
*   **Músicas de Fundo:** Coloque trilhas sonoras `.mp3` em `assets/music/`. O script procura por `facts_bg_music.mp3` e `stoicism_bg_music.mp3` nessa pasta.

---

## 🎬 Como Executar

Execute o script principal:
```powershell
python main.py
```
Isso iniciará o modo interativo no terminal, onde você poderá escolher o nicho, digitar um tema opcional (ex: "Albert Einstein" ou "Marcus Aurelius on discipline") e a precisão do Whisper.

### Execução via Argumentos (CLI)
Você também pode rodar diretamente definindo argumentos:
```powershell
# Gerar vídeo sobre fatos do espaço
python main.py --niche facts --topic "space travel"

# Gerar vídeo estoico sobre controle de emoções
python main.py --niche stoicism --topic "controlling anger"
```

O vídeo final renderizado será salvo na pasta `output/` como `facts_shorts_final.mp4` ou `stoicism_shorts_final.mp4`.

---

## 📈 Dicas para Monetização e Crescimento Rápido

1. **Frequência de Postagem:** Publique de 1 a 2 Shorts por dia. A consistência treina o algoritmo do YouTube para entender seu público.
2. **SEO de Shorts:** Use títulos chamativos e curiosos. 
   *   *Fatos:* "3 Space Facts That Will Terrify You 🤯"
   *   *Estoicismo:* "How To Master Self-Control (Stoicism) 🏛️"
3. **Tags estratégicas:** Adicione na descrição ou tags do vídeo: `#shorts`, `#viral`, `#fyp`, `#facts`, `#stoicism`, `#ancientwisdom`, `#motivation`.
4. **Agendamento automático:** No YouTube Studio, use o agendamento de postagens para manter os uploads acontecendo no mesmo horário todos os dias (ex: 12:00 e 18:00).
