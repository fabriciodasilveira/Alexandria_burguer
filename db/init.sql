-- Criação da Tabela de Configuração das 13 Mesas
CREATE TABLE tables (
    id INTEGER PRIMARY KEY CHECK (id BETWEEN 1 AND 13),
    capacity INTEGER DEFAULT 4,
    location_zone VARCHAR(20), -- 'Varanda', 'Interno', 'Jardim'
    status VARCHAR(20) DEFAULT 'Livre',
    current_reservation_id INTEGER NULL,
    notes TEXT,
    priority_order INTEGER -- Para alocação inteligente
);

-- Inicialização das 13 Mesas (Conforme especificação)
INSERT INTO tables (id, capacity, location_zone, priority_order) VALUES
(1, 4, 'Varanda', 1), (2, 4, 'Varanda', 2), (3, 4, 'Varanda', 3), (4, 4, 'Varanda', 4),
(5, 4, 'Interno', 5), (6, 4, 'Interno', 6), (7, 4, 'Interno', 7), (8, 4, 'Interno', 8),
(9, 4, 'Jardim', 9), (10, 4, 'Jardim', 10), (11, 4, 'Jardim', 11), (12, 4, 'Jardim', 12),
(13, 4, 'Jardim', 13)
ON CONFLICT (id) DO NOTHING;

-- Criação da Tabela Principal de Reservas
CREATE TABLE reservations (
    id SERIAL PRIMARY KEY,
    reservation_code VARCHAR(10) UNIQUE,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    reservation_date DATE NOT NULL,
    reservation_time TIME NOT NULL,
    period VARCHAR(10) NOT NULL, -- 'Almoço' ou 'Jantar'
    table_number INTEGER NOT NULL REFERENCES tables(id), -- 1 a 13
    party_size INTEGER DEFAULT 1 CHECK (party_size <= 4),
    status VARCHAR(20) DEFAULT 'Confirmada', -- 'Confirmada', 'Check-in', 'Cancelada', 'No-show'
    window_end TIME NOT NULL, -- Horário de liberação da mesa (reserva + 3h)
    check_in_status BOOLEAN DEFAULT FALSE,
    check_in_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_reservations_date_time ON reservations(reservation_date, reservation_time);
CREATE INDEX idx_reservations_table_status ON reservations(table_number, status);

-- Trigger para atualizar `updated_at`
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_reservations_updated_at
BEFORE UPDATE ON reservations
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_tables_updated_at
BEFORE UPDATE ON tables
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

-- Inserindo algumas reservas de exemplo para teste
-- Reserva 1: Ocupada (Mesa 2, 19:00 - 22:00)
INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status, check_in_time) VALUES
('R0001', 'João', '5511988887777', CURRENT_DATE, '19:00:00', 'Jantar', 2, 4, 'Check-in', '22:00:00', TRUE, CURRENT_TIMESTAMP);

UPDATE tables SET status = 'Ocupada', current_reservation_id = 1 WHERE id = 2;

-- Reserva 2: Reservada (Mesa 3, 19:00 - 22:00, Limite 19:30)
INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status) VALUES
('R0002', 'Maria', '5511988886666', CURRENT_DATE, '19:00:00', 'Jantar', 3, 2, 'Confirmada', '22:00:00', FALSE);

UPDATE tables SET status = 'Reservada', current_reservation_id = 2 WHERE id = 3;

-- Reserva 3: Ocupada (Mesa 5, 18:30 - 21:30)
INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status, check_in_time) VALUES
('R0003', 'Ana', '5511988885555', CURRENT_DATE, '18:30:00', 'Jantar', 5, 4, 'Check-in', '21:30:00', TRUE, CURRENT_TIMESTAMP);

UPDATE tables SET status = 'Ocupada', current_reservation_id = 3 WHERE id = 5;

-- Reserva 4: Reservada (Mesa 7, 20:30 - 23:30)
INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status) VALUES
('R0004', 'Carlos', '5511988884444', CURRENT_DATE, '20:30:00', 'Jantar', 7, 4, 'Confirmada', '23:30:00', FALSE);

UPDATE tables SET status = 'Reservada', current_reservation_id = 4 WHERE id = 7;

-- Reserva 5: Reservada (Mesa 9, 19:30 - 22:30)
INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status) VALUES
('R0005', 'Paula', '5511988883333', CURRENT_DATE, '19:30:00', 'Jantar', 9, 3, 'Confirmada', '22:30:00', FALSE);

UPDATE tables SET status = 'Reservada', current_reservation_id = 5 WHERE id = 9;

-- Reserva 6: Ocupada (Mesa 10, 19:00 - 22:00)
INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status, check_in_time) VALUES
('R0006', 'Marcos', '5511988882222', CURRENT_DATE, '19:00:00', 'Jantar', 10, 4, 'Check-in', '22:00:00', TRUE, CURRENT_TIMESTAMP);

UPDATE tables SET status = 'Ocupada', current_reservation_id = 6 WHERE id = 10;

-- Reserva 7: Reservada (Mesa 12, 21:00 - 00:00)
INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status) VALUES
('R0007', 'Lucia', '5511988881111', CURRENT_DATE, '21:00:00', 'Jantar', 12, 2, 'Confirmada', '00:00:00', FALSE);

UPDATE tables SET status = 'Reservada', current_reservation_id = 7 WHERE id = 12;

-- Mesas Livres: 1, 4, 6, 8, 11, 13 (6 mesas)
-- Mesas Ocupadas (Check-in): 2, 5, 10 (3 mesas)
-- Mesas Reservadas (Aguardando Check-in): 3, 7, 9, 12 (4 mesas)

-- A Mesa 3 (Maria, 19:00) está sob a regra das 19:30.

