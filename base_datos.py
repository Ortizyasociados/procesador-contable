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
def guardar_factura_en_libro(datos):
    conn = sqlite3.connect("contabilidad.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Libro_Compras (
            ID_Factura TEXT PRIMARY KEY,
            Fecha_Emision TEXT,
            NIT_Proveedor TEXT,
            Razon_Social_Proveedor TEXT,
            Total_Factura REAL,
            Total_Base_Impuestos REAL,
            Total_Impuestos REAL
        )
    ''')
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO Libro_Compras (ID_Factura, Fecha_Emision, NIT_Proveedor, Razon_Social_Proveedor, Total_Factura, Total_Base_Impuestos, Total_Impuestos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos.get('ID_Factura'),
            datos.get('Fecha_Emision'),
            datos.get('NIT_Proveedor'),
            datos.get('Razon_Social_Proveedor'),
            datos.get('Total_Factura'),
            datos.get('Total_Base_Impuestos'),
            datos.get('Total_Impuestos')
        ))
        conn.commit()
    finally:
        conn.close()

def guardar_movimiento_diario(datos_contables):
    conn = sqlite3.connect("contabilidad.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Diario_Contable (
            ID_Movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha TEXT,
            Cuenta_PUC TEXT,
            Descripcion TEXT,
            Debito REAL,
            Credito REAL
        )
    ''')
    # Aquí guardarás tus asientos contables definitivos
    cursor.execute('INSERT INTO Diario_Contable (Fecha, Cuenta_PUC, Descripcion, Debito, Credito) VALUES (?, ?, ?, ?, ?)', 
                   (datos_contables['fecha'], datos_contables['cuenta'], datos_contables['desc'], datos_contables['debito'], datos_contables['credito']))
    conn.commit()
    conn.close()
