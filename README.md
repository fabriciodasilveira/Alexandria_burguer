# Sistema de Automação de Reservas - 13 Mesas

Este projeto implementa a solução técnica proposta para o **Sistema de Automação de Reservas** de um restaurante com operação dual (Almoço e Jantar) e gestão de **13 mesas**.

A solução é baseada em uma arquitetura de microsserviços containerizada, utilizando **Docker Compose** para orquestração.

## 1. Arquitetura da Solução

A arquitetura proposta é robusta e escalável, conforme detalhado na especificação:

| Serviço | Tecnologia | Função |
| :--- | :--- | :--- |
| **`database`** | PostgreSQL | Armazenamento robusto do modelo de dados de 13 mesas e reservas. |
| **`backend`** | Python/FastAPI | Lógica de negócio, gestão de reservas, aplicação das regras críticas (janela de 3h, regra 19:30). |
| **`frontend`** | Nginx/HTML/JS | Interface web para a equipe, visualização do dashboard de 13 mesas em tempo real. |
| **`n8n`** | n8n | Orquestração de workflows (comunicação com WhatsApp, LLM, etc.). |
| **`waha`** | WAHA | Integração com a API do WhatsApp. |
| **`llm`** | LLM Local | Processamento de linguagem natural para extração de dados de reservas via WhatsApp. |

## 2. Estrutura de Containers (`docker-compose.yaml`)

O arquivo `docker-compose.yaml` define todos os serviços e suas configurações:

```yaml
version: '3.8'

services:
  database:
    image: postgres:14-alpine
    container_name: postgres_db
    environment:
      POSTGRES_DB: restaurante_13mesas
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql # Inicializa o DB com schema e dados
    ports:
      - "5432:5432"
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend_api
    environment:
      DATABASE_URL: postgresql://user:password@database:5432/restaurante_13mesas
      MAX_TABLES: 13
      TABLE_CAPACITY: 4
    ports:
      - "8000:8000"
    depends_on:
      - database
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: frontend_web
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
    
  # Serviços de integração (n8n, waha, llm) - Placeholder para arquitetura completa
  # ...
```

## 3. Modelo de Dados (PostgreSQL)

O arquivo `db/init.sql` cria as tabelas `tables` (13 mesas) e `reservations`, e popula com dados iniciais para simulação.

**Tabela `tables`:**
- `id`: 1 a 13
- `capacity`: 4 (padrão)
- `location_zone`: 'Varanda', 'Interno', 'Jardim'
- `status`: 'Livre', 'Reservada', 'Ocupada'
- `priority_order`: Para alocação inteligente.

**Tabela `reservations`:**
- `reservation_code`: Código único (ex: R0001)
- `reservation_date`, `reservation_time`, `window_end`: Gerenciamento da janela de 3 horas.
- `table_number`: Chave estrangeira para a tabela de mesas.
- `status`: 'Confirmada', 'Check-in', 'Cancelada', 'No-show'.

## 4. Lógica de Backend (FastAPI)

O arquivo `backend/main.py` implementa a API com as seguintes funcionalidades críticas:

1.  **`POST /reservations`**: Criação de nova reserva.
    -   Aplica a regra da **janela de 3 horas** para verificar conflitos em todas as 13 mesas.
    -   Utiliza a lógica de alocação inteligente (`priority_order`).
2.  **`POST /reservations/{code}/checkin`**: Atualiza status para 'Check-in' e mesa para 'Ocupada'.
3.  **`POST /simulate/1930_check`**: Simula a execução da regra de negócio crítica:
    -   Verifica reservas noturnas confirmadas com horário <= 19:30 que não fizeram check-in.
    -   Se houver mesas livres, simula a **oferta de alteração de horário**.
    -   Se não houver mesas livres, simula o **cancelamento automático** (status 'No-show').
4.  **`GET /tables`**: Retorna o status de todas as 13 mesas para o dashboard.
5.  **`GET /reservations/today`**: Retorna as reservas ativas para o dia.

## 5. Interface Web (Dashboard)

O arquivo `frontend/dist/index.html` contém o dashboard em HTML/CSS/JavaScript que:

-   Busca dados do `backend` (`/tables` e `/reservations/today`).
-   Apresenta a **visualização em grid das 13 mesas**, agrupadas por GRUPO A, B, C e D.
-   Exibe o status (`Livre`, `Ocupada`, `Reservada`) e informações da reserva.
-   Inclui o **alerta visual** (`⚠️ até 19:30`) para as reservas sob a regra crítica.
-   Calcula e exibe o **resumo de estatísticas** (Livres, Ocupadas, Reservadas).
-   Atualiza o status a cada 10 segundos (simulando tempo real).

## 6. Como Executar (Ambiente Real)

1.  **Pré-requisitos:** Docker e Docker Compose instalados.
2.  **Construção e Inicialização:**
    ```bash
    docker compose up --build -d
    ```
3.  **Acesso:**
    -   **Dashboard Web:** Acesse `http://localhost:80`
    -   **Backend API (Documentação Swagger):** Acesse `http://localhost:8000/docs`
    -   **n8n Orchestrator:** Acesse `http://localhost:5678`

