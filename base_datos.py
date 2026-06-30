import sqlite3

def inicializar_db():
    # Esto crea el archivo 'contabilidad.db' automáticamente
    conn = sqlite3.connect("contabilidad.db")
    cursor = conn.cursor()
    
    # Creamos la tabla de Terceros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Terceros (
            NIT TEXT PRIMARY KEY,
            Razon_Social TEXT,
            Direccion TEXT,
            Ciudad TEXT,
            Telefono TEXT,
            Email TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Base de datos y tabla de Terceros creadas con éxito.")

if __name__ == "__main__":
    inicializar_db()
