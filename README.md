# Melody: agente de atendimento da Empório da Música

A Melody é um agente de atendimento por texto para a Empório da Música, uma loja fictícia de instrumentos musicais em Campo Grande (MS). Ela tira dúvidas sobre produtos, preços, estoque, promoções, pedidos e regras da loja, sempre consultando o banco de dados e o manual de políticas em vez de responder de cabeça.

Tudo roda localmente com Docker: o modelo de linguagem, o de embeddings, o banco e a observabilidade.

## Exemplos de conversa

Para ver a Melody funcionando sem rodar nada, abra a pasta [`examples/`](examples/). Ela tem três conversas completas, geradas com o agente rodando de verdade. Cada arquivo é uma sessão inteira de um cliente simulado, e cada cliente testa um conjunto diferente de comportamentos:

| Arquivo | Cliente | O que a conversa mostra |
|---|---|---|
| [`examples/alice.md`](examples/alice.md) | Iniciante comprando o primeiro violão | Busca por significado, produto específico, políticas e memória |
| [`examples/bob.md`](examples/bob.md) | Cliente consultando pedidos | Verificação por email, encadeamento pedido + política, privacidade e perguntas com até três ferramentas |
| [`examples/tom.md`](examples/tom.md) | Cliente em inglês | Idioma, escopo, produto esgotado, prompt injection e pedido de atendimento humano |

As mensagens de cada cliente estão em `scenarios/cases.py`, com um comentário indicando a ferramenta que cada uma testa. Para gerar as conversas de novo no seu ambiente, veja [Rodar os cenários de exemplo](#rodar-os-cenários-de-exemplo).

---

Working notes do projeto no meu blog pessoal:

https://learning-out-loud.vercel.app/projects/agent-assistant-for-music-store


## Sumário

- [Melody: agente de atendimento da Empório da Música](#melody-agente-de-atendimento-da-empório-da-música)
  - [Exemplos de conversa](#exemplos-de-conversa)
  - [Sumário](#sumário)
  - [Como funciona](#como-funciona)
  - [Como rodar](#como-rodar)
    - [Pré-requisitos](#pré-requisitos)
    - [Passo a passo](#passo-a-passo)
    - [Comandos da CLI](#comandos-da-cli)
    - [Rodar os cenários de exemplo](#rodar-os-cenários-de-exemplo)
    - [Ver o tracing no Phoenix](#ver-o-tracing-no-phoenix)
    - [Regerar os dados vetoriais (opcional)](#regerar-os-dados-vetoriais-opcional)
  - [Arquitetura](#arquitetura)
  - [Como os dados são gerados](#como-os-dados-são-gerados)
    - [A ingestão offline](#a-ingestão-offline)
    - [A carga no PostgreSQL](#a-carga-no-postgresql)
    - [Os dados gerados em tempo de execução](#os-dados-gerados-em-tempo-de-execução)
  - [Decisões técnicas](#decisões-técnicas)
    - [1. Abordagem do agente: ferramentas tipadas + RAG](#1-abordagem-do-agente-ferramentas-tipadas--rag)
    - [2. Sem framework: loop do agente e memória à mão](#2-sem-framework-loop-do-agente-e-memória-à-mão)
    - [3. Modelos: Qwen3 4B (agente) e BGE-M3 (embeddings)](#3-modelos-qwen3-4b-agente-e-bge-m3-embeddings)
      - [O modelo do agente: Qwen3 4B](#o-modelo-do-agente-qwen3-4b)
      - [O modelo de embeddings: BGE-M3](#o-modelo-de-embeddings-bge-m3)
    - [4. Banco: PostgreSQL + pgvector](#4-banco-postgresql--pgvector)
    - [5. Retrieval: o que entra nos vetores e como](#5-retrieval-o-que-entra-nos-vetores-e-como)
    - [6. Tratamento de dados](#6-tratamento-de-dados)
    - [7. Memória: SQLite por sessão](#7-memória-sqlite-por-sessão)
    - [8. Interface: CLI + API HTTP com streaming](#8-interface-cli--api-http-com-streaming)
    - [9. Garantias em código](#9-garantias-em-código)
    - [10. Prompt](#10-prompt)
    - [11. Observabilidade](#11-observabilidade)
  - [O que eu faria se tivesse mais tempo](#o-que-eu-faria-se-tivesse-mais-tempo)
    - [Limitações conhecidas](#limitações-conhecidas)
  - [Uso de assistentes de código](#uso-de-assistentes-de-código)

---

## Como funciona

O cliente conversa com a Melody pela linha de comando. Cada mensagem passa por este caminho:

1. **A CLI envia a mensagem ao agente**, junto com o ID da sessão.
2. **O agente recupera a memória**: as últimas mensagens daquela sessão, guardadas em SQLite.
3. **O modelo (Qwen3 4B, rodando local no Ollama) decide o que fazer**: responder direto ou chamar uma ou mais ferramentas.
4. **As ferramentas consultam o PostgreSQL.** Perguntas sobre dados exatos (preço, estoque, pedidos) vão por SQL; perguntas por significado (um produto "para iniciante", uma regra de troca) vão pela busca vetorial do pgvector, usando embeddings do BGE-M3.
5. **O modelo recebe os resultados** e pode pedir outra ferramenta, até 4 rodadas, ou escrever a resposta.
6. **A resposta é verificada e enviada.** Se o modelo citar um preço sem ter consultado nada, a resposta é barrada antes de chegar ao cliente. O texto vai aparecendo em streaming, e a troca é salva na memória.

Por exemplo, em *"Quanto custa o Takamine GD20? E qual o status do meu pedido 4?"*, o modelo chama `check_product` e `get_orders`, recebe o preço e o status direto do banco, e só então responde.

Cada passo desse caminho aparece como um trace no Phoenix, então dá para ver exatamente o que o agente fez em cada mensagem.

---

## Como rodar

### Pré-requisitos

| O quê | Para quê |
|---|---|
| Docker e Docker Compose | Rodar todos os serviços |
| GPU NVIDIA + drivers + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) | O serviço do modelo (`llm`) reserva a GPU. Sem GPU, veja a nota abaixo |
| Python 3 | Só para a CLI (`main.py`) e os cenários, que usam apenas a biblioteca padrão |
| [uv](https://docs.astral.sh/uv/) | Só para regerar os embeddings (opcional) |
| Internet na primeira execução | Download dos modelos (alguns GB) |

As portas **8000** (agente), **6006** (Phoenix), **5432** (Postgres), **11434** (Ollama) e **8080** (embeddings) precisam estar livres.

> **Sem GPU NVIDIA?** Remova o bloco `deploy:` do serviço `llm` no `docker-compose.yml`. O Ollama passa a rodar na CPU: funciona, mas as respostas ficam bem mais lentas.

### Passo a passo

**1. Variáveis de ambiente: já vêm prontas.**

Os arquivos `.env` (na raiz, em `agent/`, `db/` e `llm/`) guardam a configuração que cada serviço lê ao subir: senhas do banco, nome do modelo, endereços dos outros serviços e parâmetros do Ollama. Eles estão **versionados de propósito**, com valores de desenvolvimento local, para que o projeto rode com um único `docker compose up`, sem nenhuma configuração manual. Não é preciso alterar nada.

O `.env` da raiz define `MODEL`, o modelo do Ollama usado pelo agente.

> As senhas desses arquivos são só para este ambiente local. Em produção, viriam de um gerenciador de segredos e nunca seriam versionadas.

**2. Suba os serviços.**

```bash
docker compose up -d --build
```

O primeiro build demora: o modelo de linguagem (Qwen3 4B, cerca de 2,5 GB) é baixado **durante o build da imagem** do serviço `llm`. Os builds seguintes reaproveitam o cache.

**3. Espere tudo ficar pronto.**

```bash
docker compose ps
```

Todos os serviços devem estar `running`, e os que têm healthcheck, `healthy`. O serviço `embedding` baixa o BGE-M3 **na primeira vez que sobe**, então pode levar alguns minutos a mais. Para acompanhar:

```bash
docker compose logs -f embedding
```

Quando o log indicar que o servidor está ouvindo na porta 8080, o agente está pronto para responder perguntas que usam busca. O modelo fica salvo num volume, então isso só acontece na primeira vez.

**4. Converse com o agente pela CLI.**

```bash
python main.py                 # sessão anônima
python main.py --user alice    # sessão salva para um usuário simulado (alice, bob, tom...)
```

Com `--user`, a sessão fica salva em `sessions.json`: ao fechar e abrir a CLI de novo com o mesmo usuário, a conversa continua de onde parou. No Windows, se `python` não funcionar, use `py`.

| Serviço | Endereço |
|---|---|
| Agente (API) | `POST http://localhost:8000/chat` |
| Phoenix (traces) | http://localhost:6006 |

**5. Para parar.**

```bash
docker compose down        # para os serviços e mantém os dados e os modelos baixados
```

Evite `docker compose down -v`: o `-v` apaga **todos** os volumes, incluindo os modelos baixados, e a próxima execução baixa tudo de novo.

### Comandos da CLI

- `/new`: começa uma sessão nova
- `/help`: mostra os comandos
- `/exit`: sai

### Rodar os cenários de exemplo

```bash
python scenarios/run.py            # roda alice, bob e tom
python scenarios/run.py alice      # roda só um
```

As conversas são salvas em `examples/<nome>.md`.

### Ver o tracing no Phoenix

Todo o tracing é automático: com os serviços no ar, cada mensagem enviada ao agente já gera um trace. Um exemplo do começo ao fim:

**1. Envie uma pergunta que usa mais de uma ferramenta**

```bash
python main.py --user alice
```

```text
you> Quanto custa o Takamine GD20? E qual o status do meu pedido 4? Meu email é lucas.mendes@jmail.com
```


**2. Abra o Phoenix**

Acesse http://localhost:6006, entre no projeto **`emporio-agent`** e abra a aba **Traces**. A mensagem aparece como um trace `chat`. Ao abrir, a árvore mostra cada passo que o agente deu:

```text
chat                          AGENT      a mensagem do cliente e a resposta final
├── ChatCompletion            LLM        o modelo decide quais ferramentas chamar
├── tool check_product        TOOL       {"name": "Takamine GD20"} → preço, estoque, promoção
├── tool get_orders           TOOL       {"email": "...", "order_id": 4} → status, rastreio
└── ChatCompletion            LLM        o modelo escreve a resposta com os resultados
```

Em perguntas sobre produtos por significado ou sobre regras da loja, aparece também um span `CreateEmbeddings` (EMBEDDING) dentro da ferramenta, que é a pergunta sendo convertida em vetor para a busca no pgvector.

**3. Acompanhar uma conversa inteira**

Na aba **Sessions**, cada sessão da CLI aparece com todos os turnos em ordem (pelo `session.id`). Para ver só as conversas de um usuário simulado, filtre os traces por `user.id`, por exemplo `alice`.

O mesmo histórico também fica em `logs/<sessão>.jsonl`, com uma linha por mensagem: o que o cliente pediu, o que o modelo fez e o que respondeu.

### Regerar os dados vetoriais (opcional)

Os embeddings já estão gerados em `data/generated/` e são carregados pelo Postgres na inicialização. Só é preciso regerar se o PDF, os produtos ou o modelo de embeddings mudarem:

Com o serviço `embedding` no ar (a ingestão usa ele em `localhost:8080`):

```bash
cd ingestion
uv run python build_csv.py
```

Os scripts de inicialização do Postgres só rodam com o volume vazio. Para recarregar os dados, recrie apenas o volume do banco, sem apagar os volumes dos modelos:

```bash
docker compose stop pg-database
docker compose rm -f pg-database
docker volume ls                       # o volume do banco termina em _pg_data
docker volume rm <projeto>_pg_data     # use o nome mostrado acima
docker compose up -d --build pg-database
```

---

## Arquitetura

```text
                 ┌──────────────────────────────────────────────┐
CLI (main.py) ──▶│ Agente (Python, http.server)                 │
 session UUID    │  loop de ferramentas + checagem de preço     │──▶ Phoenix (traces)
                 │  memória: SQLite por sessão                  │
                 └───────┬───────────────┬──────────────────────┘
                         │               │
              chat/tools │               │ ferramentas
                         ▼               ▼
              Ollama (Qwen3 4B, GPU)   PostgreSQL + pgvector ◀── embeddings da pergunta
                                         ├─ dados da loja (CSV)        BGE-M3 (llama.cpp, CPU)
                                         ├─ policy_chunks (vetores)
                                         └─ product_embeddings (vetores)

Ingestão offline (ingestion/): PDF + CSV ──▶ chunks + embeddings ──▶ data/generated/*.csv ──▶ carregado no Postgres
```

| Serviço | O que faz |
|---|---|
| `llm` | Ollama com `qwen3:4b-instruct-2507-q4_K_M`, na GPU |
| `embedding` | llama.cpp servindo BGE-M3 (GGUF Q8_0), na CPU, com API compatível com OpenAI |
| `pg-database` | PostgreSQL 17 com pgvector: dados transacionais e dados semânticos |
| `agent` | O agente: loop, ferramentas, memória e servidor HTTP |
| `phoenix` | Observabilidade: traces de cada mensagem |

---

## Como os dados são gerados

O projeto tem dois tipos de dado, e cada um chega ao banco por um caminho:

| Tipo | O que é | Onde fica | Como é usado |
|---|---|---|---|
| **Dados da loja** | Produtos, categorias, clientes, pedidos e promoções (`data/*.csv`) | Tabelas normais do PostgreSQL | Consultas SQL nas ferramentas `check_product` e `get_orders` |
| **Dados semânticos** | Trechos do manual de políticas e descrições dos produtos, com seus embeddings | Tabelas com vetores (pgvector) | Busca por significado em `search_policies` e `search_products` |

Os dados da loja vêm prontos nos CSVs. Os dados semânticos são **gerados por uma ingestão offline**, que roda antes e fora do agente.

### A ingestão offline

O código fica em `ingestion/`, com dependências próprias (Docling, cliente de embeddings), separadas das do agente. Ele faz:

```text
data/políticas_da_loja.pdf ──▶ Docling (PDF → documento estruturado)
                           ──▶ HybridChunker (um chunk por seção, até 512 tokens)
                           ──▶ título da seção + conteúdo ──┐
                                                            ├──▶ BGE-M3 ──▶ data/generated/policy_chunks.csv
data/products.csv          ──▶ um texto por produto        ──┘           ──▶ data/generated/product_embeddings.csv
+ data/categories.csv          (categoria, nome, descrição, especificações)
```

**Políticas.** O Docling converte o PDF num documento estruturado, preservando títulos e tabelas. O `HybridChunker` divide esse documento seguindo as seções numeradas do manual, contando tokens com o tokenizador do próprio BGE-M3, para nenhum chunk passar de 512 tokens. A capa é descartada: só seções numeradas viram chunks. Cada chunk é embedado junto com o título da sua seção, para que um trecho solto continue sendo encontrado pelo assunto certo. Como subproduto, a conversão também gera `data/generated/politicas_da_loja.md`, útil para conferir o que o Docling extraiu.

**Produtos.** Cada produto vira um texto com categoria, nome, descrição e especificações. Preço, estoque e status ficam de fora de propósito: mudam com frequência e são filtrados por SQL na hora da pergunta, então uma mudança de estoque não exige gerar embeddings de novo.

**Embeddings.** Os textos são enviados ao serviço `embedding` (BGE-M3 no llama.cpp), que devolve um vetor de 1.024 dimensões para cada um. O resultado é gravado em CSV, com o vetor no formato de texto que o pgvector entende (`[0.01, -0.02, ...]`).

Os CSVs gerados ficam **versionados no repositório**. Por isso quem roda o projeto não precisa executar a ingestão: ela só é necessária quando o PDF, os produtos ou o modelo de embeddings mudam (ver [Regerar os dados vetoriais](#regerar-os-dados-vetoriais-opcional)).

### A carga no PostgreSQL

Na primeira vez que o banco sobe, a imagem do Postgres executa, em ordem, os scripts da pasta `db/`:

| Script | O que faz |
|---|---|
| `01-schema.sql` | Cria as tabelas da loja, com tipos e `CHECK` constraints |
| `02-load.sql` | Carrega os CSVs da loja com `COPY` |
| `03-readonly-role.sh` | Cria o usuário somente leitura (`agent_ro`) usado pelo agente |
| `04-vector-schema.sql` | Ativa o pgvector e cria as tabelas de vetores |
| `05-vector-load.sql` | Carrega os CSVs gerados pela ingestão |

O banco já sobe com tudo pronto, sem depender do modelo de embeddings estar no ar. Esses scripts só rodam com o volume do banco vazio; para recarregar, é preciso recriar o volume (o passo a passo está em "Como rodar").

### Os dados gerados em tempo de execução

Enquanto o agente roda, ele também gera dados próprios, que não fazem parte da loja:

- **Memória das conversas:** um banco SQLite no volume `agent_memory`, criado quando o agente inicia, com as mensagens de cada sessão;
- **Logs por sessão:** `logs/<sessão>.jsonl`, com o que o cliente pediu, o que o modelo fez e o que respondeu;
- **Traces:** enviados ao Phoenix a cada mensagem.

---

## Decisões técnicas

Antes dos detalhes, um resumo de cada escolha. Clique no nome para ir direto à explicação.

| Decisão | Escolha | Motivo principal |
|---|---|---|
| [Abordagem do agente](#1-abordagem-do-agente-ferramentas-tipadas--rag) | Function calling com 4 ferramentas: 2 tipadas (SQL) e 2 de RAG | Dados exatos via SQL, texto livre via busca semântica |
| [Framework](#2-sem-framework-loop-do-agente-e-memória-à-mão) | Nenhum: loop e memória implementados à mão | Mostrar domínio dos fundamentos e controle total do fluxo |
| [Modelos](#3-modelos-qwen3-4b-agente-e-bge-m3-embeddings) | Agente: Qwen3 4B local (Ollama, GPU). Embeddings: BGE-M3 (llama.cpp, CPU) | Cabe numa RTX 3050 de 6 GB, com a GPU só para o agente; projeto 100% reproduzível com Docker |
| [Banco](#4-banco-postgresql--pgvector) | PostgreSQL + pgvector | Dados relacionais e vetores no mesmo banco, na mesma query |
| [Embeddings e ingestão](#5-retrieval-o-que-entra-nos-vetores-e-como) | BGE-M3 local (llama.cpp, CPU); Docling + HybridChunker, offline, versionado em CSV | Multilíngue, deixa a GPU para o modelo; banco sobe pronto |
| [Tratamento de dados](#6-tratamento-de-dados) | CSVs carregados como vieram, validados pelo schema | Dados já estruturados; esforço concentrado no agente |
| [Memória](#7-memória-sqlite-por-sessão) | SQLite por sessão, separado do Postgres | Escopo e ciclo de vida diferentes dos dados da loja |
| [Interface](#8-interface-cli--api-http-com-streaming) | CLI + API HTTP com streaming | Simples de rodar; cliente desacoplado do agente |
| [Garantias](#9-garantias-em-código) | Checagens em código, não só no prompt | Um prompt é um pedido; o código garante |
| [Prompt](#10-prompt) | Seções, mapa de ferramentas e data atual injetada | Modelo pequeno segue melhor instruções estruturadas |
| [Observabilidade](#11-observabilidade) | Phoenix (OpenInference) + logs por sessão | Ver cada decisão do agente, não só a resposta final |

### 1. Abordagem do agente: ferramentas tipadas + RAG

A Melody precisa responder dois tipos de pergunta bem diferentes. Uns são sobre dados exatos e que mudam o tempo todo: quanto custa um violão, se ainda tem em estoque, onde está um pedido. Outros são sobre regras escritas em texto livre: posso trocar, quanto tempo demora a entrega, dá pra parcelar.

Por isso o agente usa *function calling* com quatro ferramentas, separadas pela natureza do dado:

| Ferramenta | Tipo | Fonte | Para quê |
|---|---|---|---|
| `check_product` | Tipada (SQL) | Tabelas da loja | Preço, estoque, promoção e detalhes de um produto específico |
| `get_orders` | Tipada (SQL) | Tabelas da loja | Status e rastreio de um pedido (exige email + número) |
| `search_products` | RAG (pgvector) | `product_embeddings` | Busca por significado no catálogo ("violão para iniciante"), com filtros de categoria e preço |
| `search_policies` | RAG (pgvector) | `policy_chunks` | Regras do manual de políticas |

A lógica é simples: busca por similaridade não sabe fazer "preço até R$ 700" nem "estoque maior que zero", e preço errado é o pior erro que um atendimento pode cometer. Então tudo que é dado transacional vai por SQL, consultado na hora da pergunta. Já o manual e as descrições dos produtos são texto, e o cliente pergunta por significado ("um violão bom pra começar"). Esses vão para a busca vetorial.

Considerei duas alternativas. **Colocar tudo num RAG** não funcionaria para filtros e números, e os vetores ficariam desatualizados a cada mudança de estoque. **Deixar o modelo escrever SQL** seria mais flexível, mas com um modelo pequeno a query sai errada com frequência, e um modelo escrevendo queries livres poderia acabar consultando pedidos de outros clientes. Com ferramentas tipadas, quem escreve e testa as queries sou eu; o modelo só escolhe os parâmetros.

O preço disso é que a Melody só sabe responder o que as ferramentas cobrem. Uma pergunta analítica inesperada, como "quantos modelos de cada marca vocês têm?", fica sem resposta.

Alguns cuidados no desenho das ferramentas:

- **Cada ferramenta é um contrato em Pydantic.** O mesmo modelo gera o JSON Schema que o LLM recebe e valida os argumentos que ele manda de volta, antes de qualquer acesso ao banco. Campos inventados são rejeitados (`extra="forbid"`), e o erro volta para o modelo como resultado da ferramenta, para ele corrigir a chamada.
- **Conta é no banco, linguagem é no modelo.** `check_product` já devolve o preço com a promoção aplicada (`final_price_brl`) e um campo `available` explícito. O modelo nunca calcula desconto nem precisa entender o que significa `stock_quantity = 0`.
- **`check_product` busca pelo nome, não por ID.** Assim, "quanto custa o Takamine GD20?" se resolve em uma chamada só. Ela também encontra produtos esgotados, em breve ou descontinuados, para a Melody poder avisar o cliente e sugerir outro.
- **As queries devolvem só as colunas necessárias.** Forma de pagamento e observações internas dos pedidos nunca chegam ao modelo.

### 2. Sem framework: loop do agente e memória à mão

Não usar LangChain, LangGraph ou outro framework de agentes foi uma **decisão técnica deliberada**: eu queria mostrar que penso nos fundamentos da engenharia, e não só em uma ferramenta. Fazer tudo na mão me fez enfrentar vários problemas que frameworks mais complexos escondem: quando tentar uma chamada de novo, como as mensagens e os resultados das ferramentas chegam ao modelo, como juntar uma chamada de ferramenta que chega em pedaços durante o streaming, e coisas assim. O loop do agente (chamar o modelo, executar as ferramentas que ele pedir, devolver os resultados e repetir) foi escrito em Python puro, usando o SDK da OpenAI só como cliente HTTP para a API compatível com OpenAI do Ollama (nenhum modelo da OpenAI é usado). A memória usa o `sqlite3` da biblioteca padrão do Python.

Com o loop explícito, cada decisão fica visível no código:

- o modelo pode fazer até 4 rodadas de ferramentas por mensagem, o que permite encadear, por exemplo, consultar um pedido e depois a regra de devolução. Na última rodada as ferramentas são desligadas, para forçar uma resposta;
- a primeira resposta é verificada antes de chegar ao cliente (ver [Garantias em código](#9-garantias-em-código));
- cada etapa gera um span no tracing.

Um framework como o LangGraph traria estado, checkpointing e retries prontos. Para um agente com um loop só e quatro ferramentas, isso seria mais abstração do que o problema pede, e esconderia justamente as partes que eu queria mostrar. O custo é mais código para manter; se o projeto crescesse para vários agentes ou fluxos com estados, eu reavaliaria.

### 3. Modelos: Qwen3 4B (agente) e BGE-M3 (embeddings)

O projeto usa dois modelos, com papéis diferentes, e cada um roda num lugar escolhido de propósito:

| Papel | Modelo | Onde roda |
|---|---|---|
| **Agente Melody**: entende a mensagem, decide quais ferramentas chamar e escreve a resposta | Qwen3 4B Instruct (`qwen3:4b-instruct-2507-q4_K_M`) | GPU, no Ollama |
| **Embeddings**: transforma textos em vetores para a busca semântica | BGE-M3 (GGUF `Q8_0`) | CPU, no llama.cpp |

#### O modelo do agente: Qwen3 4B

O cérebro da Melody é o `qwen3:4b-instruct-2507-q4_K_M` (Qwen3 4B Instruct, quantizado em 4 bits), rodando localmente no Ollama, na GPU. É ele que lê a conversa, escolhe as ferramentas e redige cada resposta.

A escolha foi guiada por duas coisas. A primeira é o **hardware**: minha máquina tem uma **NVIDIA RTX 3050 com 6 GB de VRAM**, e o modelo inteiro precisa caber nela junto com o cache de contexto. Se não couber, parte dele vai para a CPU e as respostas ficam várias vezes mais lentas. Um modelo de 4B em 4 bits ocupa cerca de 2,5 GB e deixa espaço para o contexto. Escolhi a versão *instruct*, sem o modo de raciocínio, para reduzir a latência.

A segunda é **reprodutibilidade**: eu queria que o projeto rodasse inteiro com Docker. Um `docker compose up` sobe tudo, sem chave de API, sem conta em provedor e sem custo para quem for avaliar. O modelo é baixado no build da imagem. De quebra, os dados dos clientes não saem da máquina.

Um modelo maior em cloud melhoraria bastante a performance do agente, principalmente na escolha e no encadeamento de ferramentas. Mas aí o projeto passaria a depender de uma chave, de um provedor externo e de custo por chamada, e eu preferi a reprodutibilidade. Como o agente fala com o Ollama pela API compatível com OpenAI, trocar para um modelo em cloud é configuração, não código.

Configurei o Ollama pensando nos 6 GB:

| Parâmetro | Valor | Por quê |
|---|---|---|
| `OLLAMA_CONTEXT_LENGTH` | 16.384 tokens | Espaço para o prompt, as 4 ferramentas, o histórico de 20 mensagens e os resultados de várias rodadas de ferramentas |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` | O cache de contexto em 8 bits usa metade da memória do padrão de 16 bits, com pouca perda de qualidade. É o que permite 16K de contexto em 6 GB |
| `OLLAMA_FLASH_ATTENTION` | `1` | Necessário para quantizar o cache, e reduz memória e tempo da atenção |
| `OLLAMA_KEEP_ALIVE` | `24h` | O modelo fica carregado na GPU, sem o tempo de carga depois de uma pausa |

Com isso, o modelo com 16K de contexto ocupa cerca de 4 GB e roda 100% na GPU (dá para conferir com `ollama ps`).

Mesmo na GPU, a inferência local tem uma latência que dá para sentir. Por isso a resposta vai em **streaming**: o texto aparece enquanto o modelo escreve, e o cliente não fica olhando para a tela esperando a resposta inteira (mais detalhes na [seção 8](#8-interface-cli--api-http-com-streaming)).

O lado ruim é real: um modelo de 4B às vezes não chama a ferramenta certa, raramente encadeia ferramentas por conta própria e pode copiar exemplos do prompt ao pé da letra. Boa parte das [garantias em código](#9-garantias-em-código) existe para compensar isso.

#### O modelo de embeddings: BGE-M3

Para a busca semântica, uso o **BGE-M3**, servido pelo llama.cpp em formato GGUF (`Q8_0`). Ele transforma cada texto num vetor de 1.024 dimensões: os chunks do manual e as descrições dos produtos, uma vez só na ingestão, e a pergunta do cliente, a cada busca.

Escolhi o BGE-M3 porque é **multilíngue**: o manual e a maioria dos clientes estão em português, e alguns escrevem em inglês. Ele também é pequeno o bastante para rodar bem sem GPU, e é servido localmente, seguindo o mesmo princípio do agente: nada sai da máquina e tudo sobe com o Docker.

Ele roda **na CPU de propósito, para que toda a GPU fique dedicada ao Qwen**. Com 6 GB de VRAM, cada megabyte conta: colocar o BGE-M3 na GPU tiraria espaço do modelo do agente e do cache de contexto, e poderia empurrar parte do Qwen para a CPU, o que deixaria todas as respostas mais lentas. Já o embedding pesa pouco na CPU: na ingestão ele roda uma vez, offline, e em tempo de execução só converte uma frase curta por busca. A CPU dá conta disso sem atrasar a conversa de forma perceptível.

### 4. Banco: PostgreSQL + pgvector

Os dados da loja e os vetores ficam num único PostgreSQL 17, com a extensão pgvector.

Ter os dois no mesmo banco permite misturar filtros exatos e similaridade numa query só. Em `search_products`, por exemplo, categoria, preço máximo e status ficam no `WHERE`, e a similaridade no `ORDER BY`. Também é um serviço a menos para subir. Um vector DB dedicado, como Qdrant ou Weaviate, teria mais recursos de busca, mas exigiria juntar resultados de dois bancos para aplicar filtros de preço e estoque.

Criei um usuário no banco só para a Melody, o `agent_ro`, com permissão apenas de leitura. A ideia é simples: o agente precisa consultar preços, estoque e pedidos, mas nunca alterar nada. Mesmo que o modelo se confunda ou alguém tente induzi-lo a apagar ou mudar algum dado, o banco simplesmente não deixa. Por garantia, cada conexão do agente também é aberta em modo `read_only`.

Além disso, as queries são todas parametrizadas, então nada que o modelo mande vira SQL; o `get_orders` só mostra um pedido se o email informado for do dono dele; e o schema tem `CHECK` constraints que barram dados inválidos já na carga.

### 5. Retrieval: o que entra nos vetores e como

Nem tudo vira vetor. O que entra e como entra:

| | Políticas | Produtos |
|---|---|---|
| Fonte | PDF do manual | `products.csv` + `categories.csv` |
| Unidade | Chunks por seção (Docling + `HybridChunker`) | Um documento por produto |
| Texto embedado | Título da seção + conteúdo | Categoria, nome, descrição e especificações |
| Fica de fora | A capa do documento | Preço, estoque e status |
| Busca | 4 chunks mais próximos (distância de cosseno) | 5 mais próximos, com filtros de categoria, preço máximo e status |

O manual já vem dividido em seções numeradas, e cada uma é uma regra completa. Cortar por tamanho fixo partiria regras e tabelas no meio, então usei o `HybridChunker` do Docling, que respeita a estrutura do documento. Ele conta tokens com o tokenizador do próprio BGE-M3, com limite de 512 por chunk, que é o máximo que o servidor de embeddings aceita por texto. Cada chunk é embedado junto com o título da seção: um trecho como "o produto deve estar na embalagem original" não diz sozinho que é sobre devolução, mas com o título na frente é encontrado por perguntas sobre devolução.

Os produtos não passam por chunking, porque cada um já é uma unidade pequena e completa. E deixei preço, estoque e status fora do texto embedado de propósito: números não carregam significado num embedding, e esses valores mudam o tempo todo. Eles ficam no SQL e são filtrados na hora da pergunta, então uma mudança de estoque não exige refazer nenhum embedding.

Os embeddings são gerados pelo BGE-M3, rodando na CPU (o porquê está na [seção 3](#3-modelos-qwen3-4b-agente-e-bge-m3-embeddings)).

A **ingestão é offline**. Ela roda separada do agente, na pasta `ingestion/`, com dependências próprias, e grava o resultado em CSV em `data/generated/`, que o Postgres carrega ao iniciar. Assim o banco sobe com os dados prontos, sem depender do modelo de embeddings estar no ar, e os arquivos gerados ficam no repositório, onde dá para revisar exatamente o que o agente sabe. A contrapartida é que, se o PDF, os produtos ou o modelo de embeddings mudarem, alguém precisa rodar a ingestão de novo.

Uma limitação da busca só semântica: nomes de modelo como "GD20" e "GD30" ficam muito próximos num embedding. Por isso, quando o cliente pergunta de um produto específico, a ferramenta certa é `check_product`, que busca pelo nome com SQL.

### 6. Tratamento de dados

Os CSVs foram carregados como vieram, com os tipos e as `CHECK` constraints do schema validando a carga. O PDF foi convertido com Docling, e a única limpeza foi descartar a capa. [CONFIRMAR] Os CSVs já estavam estruturados o bastante para um protótipo, então concentrei o esforço no agente.

Ficou de fora uma limpeza e anonimização dos textos antes de gerar os embeddings, e as inconsistências do manual foram documentadas em vez de corrigidas (ver [Suposições sobre os dados](#suposições-sobre-os-dados)).

### 7. Memória: SQLite por sessão

A API do modelo não tem estado: a cada chamada, ele só sabe o que está nas mensagens enviadas. Sem memória, uma pergunta como "e o pedido 19?" não faz sentido. A solução é guardar a conversa e reenviá-la.

A memória fica em SQLite, separada por sessão. A CLI gera um UUID para cada sessão, simulando a sessão de um cliente, e o agente carrega as últimas 20 mensagens dessa sessão a cada chamada.

Usei SQLite em vez de uma tabela no Postgres porque memória de conversa e dados da loja têm escopos diferentes: uma é estado da aplicação, por sessão; o outro é o dado do negócio, que o agente só lê. Mantendo separado, o banco da loja continua somente leitura para o agente. E para um protótipo, SQLite é só um arquivo, sem serviço a mais.

Alguns detalhes:

- a tabela tem índice em `(session_id, id)`, que é exatamente o padrão da consulta: as mensagens de uma sessão, em ordem;
- só a mensagem do cliente e a resposta final são guardadas, não os resultados das ferramentas. O histórico fica curto, mas numa pergunta de acompanhamento o modelo só tem o texto da resposta anterior;
- o limite de 20 mensagens mantém o histórico dentro da janela de 16.384 tokens.

O SQLite tem um limite claro: é um arquivo local ao container. Com várias réplicas do agente, cada uma teria sua própria memória. Nesse cenário, eu levaria a memória para o Redis, que é compartilhado e expira sessões sozinho.

### 8. Interface: CLI + API HTTP com streaming

O agente expõe um endpoint HTTP (`POST /chat`) que responde em streaming de texto, e uma CLI (`main.py`) conversa com ele. Como o foco do case é o agente, a interface é a mais simples que funciona. Separar a CLI do agente por HTTP também permite trocar a interface, por uma página web ou um WhatsApp, sem mexer no agente. [CONFIRMAR: por que `http.server` e não FastAPI] Com um endpoint só, o servidor da biblioteca padrão dá conta.

Sobre o streaming: a resposta vai sendo enviada enquanto o modelo escreve, com uma exceção. A primeira resposta de cada mensagem não vai em streaming, porque ela precisa existir inteira para ser verificada. Depois que uma ferramenta roda, a resposta se apoia nos dados retornados, e o resto segue em streaming.

Com `--user`, a CLI salva a sessão em `sessions.json`, e a conversa continua de onde parou quando a CLI é aberta de novo. Os cenários de Alice, Bob e Tom não usam esse arquivo: o `scenarios/run.py` cria uma sessão nova a cada execução, para que uma rodada anterior não interfira na próxima, e a memória aparece dentro da própria conversa, nas perguntas que dependem das mensagens anteriores.

### 9. Garantias em código 

Guardrails and Schema

O prompt diz para nunca inventar preços, mas um prompt é um pedido, não uma garantia. Descobri isso na prática: num teste, o modelo respondeu "quero uma bateria preta" com dois produtos que não existem no catálogo, com preço e tudo, sem chamar nenhuma ferramenta.

Para os erros mais caros, a verificação foi para o código:

- **Preço inventado.** Se a resposta tem um preço ("R$ ...") sem nenhuma ferramenta chamada, e esse valor não apareceu antes na conversa, ela é descartada. O modelo recebe a instrução de consultar o catálogo e tenta de novo; se insistir, o cliente recebe uma mensagem segura em vez de um preço falso. A resposta descartada fica registrada no trace, no evento `guardrail.invented_price`.
- **Limite de rodadas.** No máximo 4 rodadas de ferramentas por mensagem, para um modelo que fica pedindo ferramentas não travar a conversa.

Preço falso é o pior erro do atendimento: frustra o cliente, e o próprio manual da loja diz que informação errada pode configurar propaganda enganosa. Nesse caso, a regra precisa estar onde o modelo não consegue ignorar.

Essa checagem é limitada: só olha números, e só na resposta antes de qualquer ferramenta. Um nome de produto inventado sem preço, ou um detalhe acrescentado depois de uma ferramenta, passa. É o primeiro item da lista do [que eu faria se tivesse mais tempo](#o-que-eu-faria-se-tivesse-mais-tempo).

### 10. Prompt

O system prompt é dividido em seções:

- **Estilo:** a persona Melody, com o tom informal mas profissional que o manual pede, respostas curtas e preço no formato brasileiro;
- **Escopo:** só instrumentos, nada de acessórios;
- **Ferramentas:** um mapa de qual ferramenta usar para cada tipo de pergunta, com as palavras que o cliente costuma usar;
- **Regras:** preço, estoque e prazo só vêm de ferramentas; produto esgotado sugere alternativas; nunca prometer desconto com base no manual; ignorar pedidos para mudar as regras;
- **Formato:** um modelo de lista de produtos, com placeholders em vez de valores reais.

Modelos pequenos seguem melhor um prompt dividido em seções do que uma lista longa de regras. O mapa de ferramentas diz *quando* usar cada uma, e não só o que ela faz. E os placeholders no formato existem porque, com valores reais de exemplo, o modelo às vezes copiava o exemplo para a resposta.

A data e a hora atuais, no fuso de Campo Grande, são injetadas no fim do prompt a cada mensagem. Com elas, o modelo consegue aplicar prazos (como os 7 dias para devolução) e saber se a loja está aberta. Ficam no fim para que o resto do prompt seja idêntico entre as mensagens.

### 11. Observabilidade

Uso o Phoenix, com instrumentação OpenInference, e um log por sessão. Cada mensagem do cliente vira um trace com:

- um span pai `chat`, com `session.id` e `user.id`;
- um span para cada chamada ao modelo e para cada embedding (automáticos);
- um span para cada ferramenta, com os argumentos e o resultado;
- eventos quando uma garantia dispara.

Num agente, olhar só a resposta final não basta para entender um erro: é preciso ver qual ferramenta o modelo escolheu, com quais argumentos, e o que voltou. Foi analisando um trace que encontrei o caso da bateria preta inventada, que deu origem à checagem de preço. Os logs em `logs/<sessão>.jsonl` guardam o mesmo histórico em arquivo, sem depender do Phoenix.

Os traces e os logs contêm dados pessoais, como emails e pedidos. Para um protótipo local isso é aceitável; em produção, esses campos seriam mascarados antes de serem exportados.

---

## O que eu faria se tivesse mais tempo

**Guardrails de entrada e de saída.** Hoje a única garantia em código é a checagem de preço, e ela só cobre a primeira resposta. Eu adicionaria duas camadas:

- *na entrada*, antes do modelo: detectar tentativas de prompt injection, perguntas fora do escopo e dados pessoais que não precisam ser processados;
- *na saída*, antes de chegar ao cliente: conferir nomes de produtos, preços, prazos e regras contra os resultados das ferramentas, inclusive nas respostas que vão em streaming.

**Um sistema de avaliação.** Hoje eu avalio o agente rodando cenários e lendo as respostas, o que não escala e depende de mim. Eu montaria um conjunto de perguntas com a ferramenta esperada e os fatos que a resposta precisa conter, e mediria a cada mudança de prompt ou de modelo: se o modelo chamou a ferramenta certa, se os números batem com o banco, se ele recusou o que devia recusar. Os cenários em `scenarios/` são o ponto de partida. Com isso, dá para comparar o Qwen 4B com um modelo em cloud com números, e não com impressões.

**Uma camada de observabilidade mais robusta.** Pensei em usar o **Langfuse**, que junta tracing, versionamento de prompts, datasets de avaliação e métricas de custo e qualidade num lugar só, e se encaixaria bem com o sistema de avaliação acima. Mas, rodando localmente, ele traria vários serviços novos para o Docker Compose, e a complexidade do projeto aumentaria bastante para um protótipo. O Phoenix cobre o essencial com um container só.

**Tratamento e normalizacao dos dados.** Trataria os dados devidamente considerando que estão com inconsistências e dados sensíveis


Vale reforçar: ficar sem frameworks, tanto para o agente quanto para essas camadas, foi uma decisão consciente para mostrar os fundamentos. Com mais tempo, e com o projeto indo para produção, eu adotaria ferramentas prontas onde elas economizam trabalho de verdade, como o Langfuse para observabilidade e avaliação.

### Limitações conhecidas

| Limitação | Como eu resolveria |
|---|---|
| O modelo de 4B às vezes não chama a ferramenta certa e raramente encadeia ferramentas sozinho | Comparar com um modelo maior em cloud usando o sistema de avaliação; a troca é só configuração |
| Os textos não passaram por limpeza nem anonimização antes de gerar os embeddings | Limpar e anonimizar na ingestão |
| Dados pessoais (emails, pedidos) aparecem nos traces e nos logs | Mascarar esses campos antes de exportar |
| `search_products` mostra o preço de tabela; só `check_product` aplica promoções | Reaproveitar o cálculo da promoção nas duas ferramentas |
| Busca só semântica, sem busca por palavra-chave | Busca híbrida com o full-text search do Postgres |
| Sem autenticação na API | Chave de API ou autenticação na frente do agente |
| Os `.env` estão versionados com senhas de desenvolvimento, para facilitar a reprodução | Segredos fora do repositório, com `.env.example` e um gerenciador de segredos |
| Histórico limitado às últimas 20 mensagens | Resumir as conversas longas |
| Os scripts de inicialização do Postgres só rodam com o volume vazio | Uma ferramenta de migrations |


Um exemplo legal para tratar os dados sensiveis aparecendo nos traces, é oque chamam de **anonimização de logs**

---

## Uso de assistentes de código

Usei o **Claude** como mentor técnico ao longo do projeto. Ele me ajudou a:

- **discutir arquitetura e alternativas**, comparando os prós e contras de cada caminho;
- **revisar e escrever código**;
- **trazer ideias e feedbacks** sobre o que eu estava construindo.

As decisões de arquitetura, a lógica e a forma de resolver os problemas foram minhas. Entre elas: usar um modelo local, escrever o loop do agente e a memória sem framework, colocar o pgvector no mesmo banco dos dados da loja, fazer a ingestão offline e pensar nos guardrails e nos *structured outputs* (os contratos das ferramentas) para tornar o agente mais confiável.

Nenhum codigo gerado por ele foi commitado sem o devido supervisionamento. Nada foi empurrado com a barriga. 


