import sqlite3

def guardar_tercero(datos):
    # La conexión se abre y se cierra en cada llamada, esto evita bloqueos
    conn = sqlite3.connect("contabilidad.db")
    cursor = conn.cursor()
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
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO Terceros (NIT, Razon_Social, Direccion, Ciudad, Telefono, Email)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datos.get('NIT_Proveedor'),
            datos.get('Razon_Social_Proveedor'),
            datos.get('Direccion_Proveedor'),
            datos.get('Ciudad_Proveedor'),
            datos.get('Telefono_Proveedor'),
            datos.get('Correo_Proveedor')
        ))
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
