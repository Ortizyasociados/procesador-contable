import sqlite3

def conectar():
    return sqlite3.connect("contabilidad.db")

def inicializar_base_datos():
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Tabla Terceros (Actualizada con Cuenta_Contable)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Terceros (
            NIT TEXT PRIMARY KEY,
            Razon_Social TEXT,
            Direccion TEXT,
            Ciudad TEXT,
            Telefono TEXT,
            Email TEXT,
            Cuenta_Contable TEXT
        )
    ''')
    
    # 2. Tabla Plan_Cuentas (PUC de 8 dígitos jerárquico)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Plan_Cuentas (
            Codigo_Cuenta TEXT PRIMARY KEY,
            Nombre_Cuenta TEXT,
            Nivel INTEGER,
            Codigo_Padre TEXT,
            Naturaleza TEXT,
            Es_Movimiento BOOLEAN
        )
    ''')
    
    # 3. Tabla Libro_Compras
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
    
    # 4. Tabla Diario_Contable
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Diario_Contable (
            ID_Movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha TEXT,
            Comprobante TEXT,
            Codigo_Cuenta TEXT,
            Tercero_NIT TEXT,
            Descripcion TEXT,
            Debito REAL,
            Credito REAL,
            Tipo TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def guardar_tercero(datos):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO Terceros (NIT, Razon_Social, Direccion, Ciudad, Telefono, Email)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datos.get('NIT_Proveedor'), datos.get('Razon_Social_Proveedor'), 
              datos.get('Direccion_Proveedor'), datos.get('Ciudad_Proveedor'), 
              datos.get('Telefono_Proveedor'), datos.get('Correo_Proveedor')))
        conn.commit()
    finally:
        conn.close()

def guardar_factura_en_libro(datos):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO Libro_Compras (ID_Factura, Fecha_Emision, NIT_Proveedor, Razon_Social_Proveedor, Total_Factura, Total_Base_Impuestos, Total_Impuestos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datos.get('ID_Factura'), datos.get('Fecha_Emision'), datos.get('NIT_Proveedor'), 
              datos.get('Razon_Social_Proveedor'), datos.get('Total_Factura'), 
              datos.get('Total_Base_Impuestos'), datos.get('Total_Impuestos')))
        conn.commit()
    finally:
        conn.close()

def guardar_cuenta_puc(datos):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO Plan_Cuentas (Codigo_Cuenta, Nombre_Cuenta, Nivel, Codigo_Padre, Naturaleza, Es_Movimiento)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datos['codigo'], datos['nombre'], datos['nivel'], datos['padre'], datos['naturaleza'], datos['es_movimiento']))
        conn.commit()
    finally:
        conn.close()

def guardar_movimiento_diario(datos):
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Diario_Contable (Fecha, Comprobante, Codigo_Cuenta, Tercero_NIT, Descripcion, Debito, Credito, Tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datos['fecha'], datos['comprobante'], datos['cuenta'], datos['nit'], datos['desc'], datos['debito'], datos['credito'], datos['tipo']))
        conn.commit()
    finally:
        conn.close()

# Llamar a esto al iniciar tu app para asegurar que todas las tablas existan
inicializar_base_datos()
