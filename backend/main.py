from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, Boolean, TIMESTAMP, text
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import List
import os
import pendulum
from fastapi.middleware.cors import CORSMiddleware


# --- Configuração do Banco de Dados ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///test_reservas.db")

# Lógica condicional para argumentos de conexão (Correção SQLite vs Postgres)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Modelos SQLAlchemy ---
class Table(Base):
    __tablename__ = "tables"
    id = Column(Integer, primary_key=True, index=True)
    capacity = Column(Integer, default=4)
    location_zone = Column(String)
    status = Column(String, default="Livre")
    current_reservation_id = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    priority_order = Column(Integer)

class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True, index=True)
    reservation_code = Column(String, unique=True)
    customer_name = Column(String)
    customer_phone = Column(String)
    reservation_date = Column(Date)
    reservation_time = Column(Time)
    period = Column(String)
    table_number = Column(Integer)
    party_size = Column(Integer)
    status = Column(String, default="Confirmada")
    window_end = Column(Time)
    check_in_status = Column(Boolean, default=False)
    check_in_time = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

# --- Schemas Pydantic ---
class TableBase(BaseModel):
    id: int
    capacity: int
    location_zone: str
    status: str
    current_reservation_id: int | None = None
    notes: str | None = None
    priority_order: int

    class Config:
        from_attributes = True # Atualizado de orm_mode

class ReservationBase(BaseModel):
    customer_name: str
    customer_phone: str
    reservation_date: str # Usar string para simplificar a entrada via API
    reservation_time: str
    party_size: int

class ReservationCreate(ReservationBase):
    table_number: int | None = None # <-- MODIFICAÇÃO: Permite ao frontend sugerir uma mesa

class ReservationResponse(ReservationBase):
    id: int
    reservation_code: str
    period: str
    table_number: int
    status: str
    window_end: str
    check_in_status: bool
    
    class Config:
        from_attributes = True # Atualizado de orm_mode

# --- Dependência de Sessão ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Aplicação FastAPI ---
app = FastAPI(title="Sistema de Automação de Reservas - 13 Mesas")

# Configuração de CORS para permitir acesso do frontend 
origins = [
    "*", # Permite qualquer origem (para fins de desenvolvimento/teste )
] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/tables", response_model=List[TableBase], summary="Visualizar o Dashboard de 13 Mesas")
def get_all_tables(db: SessionLocal = Depends(get_db)):
    """
    Retorna o status atual de todas as 13 mesas para o dashboard.
    """
    tables = db.query(Table).all()
    return tables

@app.get("/reservations/today", response_model=List[ReservationResponse], summary="Reservas para Hoje")
def get_todays_reservations(db: SessionLocal = Depends(get_db)):
    """
    Retorna todas as reservas confirmadas ou em check-in para a data de hoje.
    """
    today = pendulum.now().date()
    
    # 1. Busca as reservas
    reservations_db = db.query(Reservation).filter(
        Reservation.reservation_date == today,
        Reservation.status.in_(['Confirmada', 'Check-in'])
    ).all()
    
    # 2. Converte os objetos de data/hora para string antes de retornar
    reservations_list = []
    for res in reservations_db:
        reservations_list.append(ReservationResponse(
            id=res.id,
            reservation_code=res.reservation_code,
            customer_name=res.customer_name,
            customer_phone=res.customer_phone,
            reservation_date=str(res.reservation_date), # Conversão
            reservation_time=str(res.reservation_time), # Conversão
            period=res.period,
            table_number=res.table_number,
            party_size=res.party_size,
            status=res.status,
            window_end=str(res.window_end), # Conversão
            check_in_status=res.check_in_status
        ))
        
    return reservations_list

# --- Lógica de Negócio Principal ---

def calculate_window_end(reservation_time_str: str) -> str:
    """Calcula o horário de liberação da mesa (reserva + 3 horas)."""
    try:
        start_time = pendulum.parse(reservation_time_str) # Removido exact=True
        end_time = start_time.add(hours=3)
        return end_time.format("HH:mm:ss")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido.")

def determine_period(reservation_time_str: str) -> str:
    """Determina se é 'Almoço' (11h-14h) ou 'Jantar' (18h-23h)."""
    try:
        time_obj = pendulum.parse(reservation_time_str) # Removido exact=True
        hour = time_obj.hour
        if 11 <= hour < 14:
            return "Almoço"
        elif 18 <= hour < 23:
            return "Jantar"
        else:
            # Permite horários fora da janela para walk-in, mas classifica como Jantar
            if hour >= 14:
                return "Jantar"
            else:
                return "Almoço"
            # raise HTTPException(status_code=400, detail="Horário fora da janela de operação (11h-14h ou 18h-23h).")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de hora inválido.")

# --- NOVA FUNÇÃO AUXILIAR ---
def is_table_free(db: SessionLocal, table_id: int, reservation_date_str: str, reservation_time_str: str) -> bool:
    """Verifica se uma mesa específica está livre num horário específico."""
    reservation_date = pendulum.parse(reservation_date_str).date()
    reservation_start = pendulum.parse(reservation_time_str)
    reservation_end = reservation_start.add(hours=3)

    # Verifica conflitos de horário para a mesa
    conflicting_reservations = db.query(Reservation).filter(
        Reservation.table_number == table_id,
        Reservation.reservation_date == reservation_date,
        Reservation.status.in_(['Confirmada', 'Check-in']),
        (Reservation.reservation_time.cast(String) < reservation_end.format('HH:mm:ss')) & (Reservation.window_end.cast(String) > reservation_start.format('HH:mm:ss'))
    ).first()

    return not conflicting_reservations
# --- FIM DA NOVA FUNÇÃO ---


def find_available_table(db: SessionLocal, reservation_date_str: str, reservation_time_str: str, party_size: int) -> int | None:
    """
    Encontra a melhor mesa disponível, verificando conflitos de 3 horas.
    """
    # 1. Busca todas as mesas com capacidade suficiente
    available_tables = db.query(Table).filter(Table.capacity >= party_size).order_by(Table.priority_order).all()

    for table in available_tables:
        # 2. Verifica conflitos de horário para a mesa específica
        if is_table_free(db, table.id, reservation_date_str, reservation_time_str):
            return table.id # Mesa encontrada

    return None # Nenhuma mesa disponível

@app.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED, summary="Criar Nova Reserva")
def create_reservation(reservation: ReservationCreate, db: SessionLocal = Depends(get_db)):
    """
    Cria uma nova reserva, aplicando a lógica de disponibilidade e janela de 3 horas.
    Pode receber um 'table_number' específico (para walk-ins) ou encontrar a próxima livre.
    """
    # 1. Validação e Cálculo
    period = determine_period(reservation.reservation_time)
    window_end_time = calculate_window_end(reservation.reservation_time)
    
    # --- LÓGICA DE ALOCAÇÃO DE MESA MODIFICADA ---
    table_to_assign: int | None = None

    if reservation.table_number is not None:
        # Caso 1: O frontend ESPECIFICOU uma mesa (ex: "Ocupar Mesa 5")
        table_is_available = is_table_free(db, reservation.table_number, reservation.reservation_date, reservation.reservation_time)
        
        if table_is_available:
            table_to_assign = reservation.table_number
        else:
            # Se a mesa específica pedida não estiver livre, falha.
            raise HTTPException(status_code=409, detail=f"A Mesa {reservation.table_number} não está disponível nesse horário.")
    else:
        # Caso 2: O frontend NÃO especificou (ex: WhatsApp)
        # Encontra a melhor mesa disponível automaticamente.
        table_to_assign = find_available_table(db, reservation.reservation_date, reservation.reservation_time, reservation.party_size)

    if table_to_assign is None:
        raise HTTPException(status_code=409, detail="Nenhuma mesa disponível para este horário e data.")
    # --- FIM DA MODIFICAÇÃO ---

    # 3. Gerar Código de Reserva (Simplificado)
    last_reservation = db.query(Reservation).order_by(Reservation.id.desc()).first()
    new_id = (last_reservation.id if last_reservation else 0) + 1
    reservation_code = f"R{new_id:04d}"

    # 4. Criar Objeto de Reserva
    db_reservation = Reservation(
        reservation_code=reservation_code,
        customer_name=reservation.customer_name,
        customer_phone=reservation.customer_phone,
        reservation_date=pendulum.parse(reservation.reservation_date).date(),
        reservation_time=pendulum.parse(reservation.reservation_time).time(),
        period=period,
        table_number=table_to_assign, # <-- Usa a mesa decidida
        party_size=reservation.party_size,
        window_end=pendulum.parse(window_end_time).time(),
        created_at=pendulum.now(),
        updated_at=pendulum.now()
    )

    # 5. Salvar no DB
    db.add(db_reservation)
    db.commit()
    db.refresh(db_reservation)
    
    # 6. Atualizar Status da Mesa (Simplificado: Apenas para reservas do dia)
    today = pendulum.now().date()
    if db_reservation.reservation_date == today:
        db.query(Table).filter(Table.id == table_to_assign).update({
            Table.status: "Reservada",
            Table.current_reservation_id: db_reservation.id
        })
        db.commit()

    # Retorno
    return ReservationResponse(
        id=db_reservation.id,
        reservation_code=db_reservation.reservation_code,
        customer_name=db_reservation.customer_name,
        customer_phone=db_reservation.customer_phone,
        reservation_date=str(db_reservation.reservation_date),
        reservation_time=str(db_reservation.reservation_time),
        period=db_reservation.period,
        table_number=db_reservation.table_number,
        party_size=db_reservation.party_size,
        status=db_reservation.status,
        window_end=str(db_reservation.window_end),
        check_in_status=db_reservation.check_in_status
    )

@app.post("/reservations/{reservation_code}/checkin", response_model=ReservationResponse, summary="Realizar Check-in")
def check_in_reservation(reservation_code: str, db: SessionLocal = Depends(get_db)):
    """
    Realiza o check-in de uma reserva e atualiza o status da mesa para 'Ocupada'.
    """
    db_reservation = db.query(Reservation).filter(Reservation.reservation_code == reservation_code).first()

    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")
    
    if db_reservation.status == 'Check-in':
        raise HTTPException(status_code=400, detail="Check-in já realizado.")

    # 1. Atualizar Reserva
    db_reservation.status = 'Check-in'
    db_reservation.check_in_status = True
    db_reservation.check_in_time = pendulum.now()
    db.commit()
    db.refresh(db_reservation)

    # 2. Atualizar Status da Mesa
    db.query(Table).filter(Table.id == db_reservation.table_number).update({
        Table.status: "Ocupada",
        Table.current_reservation_id: db_reservation.id
    })
    db.commit()
    
    # Retorno
    return ReservationResponse(
        id=db_reservation.id,
        reservation_code=db_reservation.reservation_code,
        customer_name=db_reservation.customer_name,
        customer_phone=db_reservation.customer_phone,
        reservation_date=str(db_reservation.reservation_date),
        reservation_time=str(db_reservation.reservation_time),
        period=db_reservation.period,
        table_number=db_reservation.table_number,
        party_size=db_reservation.party_size,
        status=db_reservation.status,
        window_end=str(db_reservation.window_end),
        check_in_status=db_reservation.check_in_status
    )

@app.post("/reservations/{reservation_code}/cancel", response_model=ReservationResponse, summary="Cancelar Reserva")
def cancel_reservation(reservation_code: str, db: SessionLocal = Depends(get_db)):
    """
    Cancela uma reserva e libera a mesa.
    """
    db_reservation = db.query(Reservation).filter(Reservation.reservation_code == reservation_code).first()

    if not db_reservation:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")
    
    if db_reservation.status in ['Cancelada', 'No-show']:
        raise HTTPException(status_code=400, detail=f"Reserva já está com status: {db_reservation.status}.")

    table_number = db_reservation.table_number

    # 1. Atualizar Reserva
    db_reservation.status = 'Cancelada'
    db.commit()
    db.refresh(db_reservation)

    # 2. Liberar Mesa (apenas se a reserva cancelada for a atual da mesa)
    db.query(Table).filter(
        Table.id == table_number,
        Table.current_reservation_id == db_reservation.id
    ).update({
        Table.status: "Livre",
        Table.current_reservation_id: None
    })
    db.commit()
    
    # Retorno
    return ReservationResponse(
        id=db_reservation.id,
        reservation_code=db_reservation.reservation_code,
        customer_name=db_reservation.customer_name,
        customer_phone=db_reservation.customer_phone,
        reservation_date=str(db_reservation.reservation_date),
        reservation_time=str(db_reservation.reservation_time),
        period=db_reservation.period,
        table_number=db_reservation.table_number,
        party_size=db_reservation.party_size,
        status=db_reservation.status,
        window_end=str(db_reservation.window_end),
        check_in_status=db_reservation.check_in_status
    )

# --- Endpoint de Simulação de Regra de Negócio (19:30) ---

@app.post("/simulate/1930_check", summary="Simular Verificação de No-Show às 19:30")
def simulate_1930_check(db: SessionLocal = Depends(get_db)):
    """
    Simula a execução diária automática que verifica reservas noturnas (Jantar)
    com horário de reserva <= 19:30 que não fizeram check-in.
    """
    today = pendulum.now().date()
    limit_time = pendulum.time(19, 30)
    
    # 1. Buscar reservas noturnas que se enquadram na regra e não fizeram check-in
    reservations_to_check = db.query(Reservation).filter(
        Reservation.reservation_date == today,
        Reservation.period == 'Jantar',
        Reservation.reservation_time <= limit_time,
        Reservation.status == 'Confirmada',
        Reservation.check_in_status == False
    ).all()

    results = []
    
    # 2. Contar mesas livres (sem nenhuma reserva ativa para o dia)
    free_tables_count = db.query(Table).filter(Table.status == 'Livre').count()

    for res in reservations_to_check:
        
        # Ação: Cancelar Automaticamente
        if free_tables_count == 0:
            res.status = 'No-show' # Novo status para cancelamento automático
            db.query(Table).filter(
                Table.id == res.table_number,
                Table.current_reservation_id == res.id
            ).update({
                Table.status: "Livre",
                Table.current_reservation_id: None
            })
            
            results.append({
                "reservation_code": res.reservation_code,
                "action": "Cancelamento Automático",
                "reason": "Limite de 19:30 excedido e 0 mesas livres para alteração."
            })
            
        # Ação: Oferecer Alteração de Horário (Simulação de comunicação proativa)
        else:
            # Na implementação real, aqui seria o envio do WhatsApp e espera por 15min.
            # Para a simulação, apenas registramos a ação.
            results.append({
                "reservation_code": res.reservation_code,
                "action": "Oferta de Alteração de Horário",
                "reason": f"Limite de 19:30 excedido, {free_tables_count} mesas livres para alteração."
            })
            
    db.commit()
    
    return {"status": "Simulação de verificação concluída", "results": results}

# --- Endpoint de Teste ---
@app.get("/")
def read_root():
    return {"message": "Sistema de Automação de Reservas (13 Mesas) - API Online"}