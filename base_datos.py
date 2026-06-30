import sqlite3

def inicializar_base_datos():
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
    conn.commit()
    conn.close()

def guardar_tercero(datos):
    conn = sqlite3.connect("contabilidad.db")
    cursor = conn.cursor()
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
        print("Error al guardar en base de datos:", e)
    finally:
        conn.close()
