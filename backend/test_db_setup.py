import sqlite3
import os

DB_PATH = "test_reservas.db"

def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela tables
    cursor.execute("""
        CREATE TABLE tables (
            id INTEGER PRIMARY KEY CHECK (id BETWEEN 1 AND 13),
            capacity INTEGER DEFAULT 4,
            location_zone TEXT,
            status TEXT DEFAULT 'Livre',
            current_reservation_id INTEGER NULL,
            notes TEXT,
            priority_order INTEGER
        );
    """)

    # Inicialização das 13 Mesas
    tables_data = [
        (1, 4, 'Varanda', 1), (2, 4, 'Varanda', 2), (3, 4, 'Varanda', 3), (4, 4, 'Varanda', 4),
        (5, 4, 'Interno', 5), (6, 4, 'Interno', 6), (7, 4, 'Interno', 7), (8, 4, 'Interno', 8),
        (9, 4, 'Jardim', 9), (10, 4, 'Jardim', 10), (11, 4, 'Jardim', 11), (12, 4, 'Jardim', 12),
        (13, 4, 'Jardim', 13)
    ]
    cursor.executemany("INSERT INTO tables (id, capacity, location_zone, priority_order) VALUES (?, ?, ?, ?)", tables_data)

    # Tabela reservations
    cursor.execute("""
        CREATE TABLE reservations (
            id INTEGER PRIMARY KEY,
            reservation_code TEXT UNIQUE,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            reservation_date TEXT NOT NULL,
            reservation_time TEXT NOT NULL,
            period TEXT NOT NULL,
            table_number INTEGER NOT NULL,
            party_size INTEGER DEFAULT 1,
            status TEXT DEFAULT 'Confirmada',
            window_end TEXT NOT NULL,
            check_in_status INTEGER DEFAULT 0,
            check_in_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Inserindo dados iniciais (simulando a lógica do init.sql)
    import datetime
    today = datetime.date.today().isoformat()
    
    initial_reservations = [
        # Reserva 1: Ocupada (Mesa 2, 19:00 - 22:00)
        ('R0001', 'João', '5511988887777', today, '19:00:00', 'Jantar', 2, 4, 'Check-in', '22:00:00', 1, datetime.datetime.now().isoformat()),
        # Reserva 2: Reservada (Mesa 3, 19:00 - 22:00, Limite 19:30)
        ('R0002', 'Maria', '5511988886666', today, '19:00:00', 'Jantar', 3, 2, 'Confirmada', '22:00:00', 0, None),
        # Reserva 3: Ocupada (Mesa 5, 18:30 - 21:30)
        ('R0003', 'Ana', '5511988885555', today, '18:30:00', 'Jantar', 5, 4, 'Check-in', '21:30:00', 1, datetime.datetime.now().isoformat()),
        # Reserva 4: Reservada (Mesa 7, 20:30 - 23:30)
        ('R0004', 'Carlos', '5511988884444', today, '20:30:00', 'Jantar', 7, 4, 'Confirmada', '23:30:00', 0, None),
        # Reserva 5: Reservada (Mesa 9, 19:30 - 22:30)
        ('R0005', 'Paula', '5511988883333', today, '19:30:00', 'Jantar', 9, 3, 'Confirmada', '22:30:00', 0, None),
        # Reserva 6: Ocupada (Mesa 10, 19:00 - 22:00)
        ('R0006', 'Marcos', '5511988882222', today, '19:00:00', 'Jantar', 10, 4, 'Check-in', '22:00:00', 1, datetime.datetime.now().isoformat()),
        # Reserva 7: Reservada (Mesa 12, 21:00 - 00:00)
        ('R0007', 'Lucia', '5511988881111', today, '21:00:00', 'Jantar', 12, 2, 'Confirmada', '00:00:00', 0, None),
    ]
    
    for res in initial_reservations:
        cursor.execute("""
            INSERT INTO reservations (reservation_code, customer_name, customer_phone, reservation_date, reservation_time, period, table_number, party_size, status, window_end, check_in_status, check_in_time) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, res)

    # Atualizar status das mesas
    cursor.execute("UPDATE tables SET status = 'Ocupada', current_reservation_id = 1 WHERE id = 2")
    cursor.execute("UPDATE tables SET status = 'Reservada', current_reservation_id = 2 WHERE id = 3")
    cursor.execute("UPDATE tables SET status = 'Ocupada', current_reservation_id = 3 WHERE id = 5")
    cursor.execute("UPDATE tables SET status = 'Reservada', current_reservation_id = 4 WHERE id = 7")
    cursor.execute("UPDATE tables SET status = 'Reservada', current_reservation_id = 5 WHERE id = 9")
    cursor.execute("UPDATE tables SET status = 'Ocupada', current_reservation_id = 6 WHERE id = 10")
    cursor.execute("UPDATE tables SET status = 'Reservada', current_reservation_id = 7 WHERE id = 12")

    conn.commit()
    conn.close()
    print(f"Banco de dados SQLite '{DB_PATH}' configurado com sucesso e dados iniciais inseridos.")

if __name__ == "__main__":
    setup_db()
