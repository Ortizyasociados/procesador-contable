import sqlite3
import pandas as pd

def conectar():
    return sqlite3.connect("contabilidad.db")

def inicializar_base_datos():
    conn = conectar()
    cursor = conn.cursor()
    # Tabla Terceros
    cursor.execute('''CREATE TABLE IF NOT EXISTS Terceros 
                      (NIT TEXT PRIMARY KEY, Razon_Social TEXT, Direccion TEXT, Email TEXT, Telefono TEXT, 
                       Ciudad TEXT, Regimen TEXT, Tipo_Tercero TEXT)''')
    # Tabla Plan_Cuentas
    cursor.execute('''CREATE TABLE IF NOT EXISTS Plan_Cuentas 
                      (Codigo_Cuenta TEXT PRIMARY KEY, Nombre_Cuenta TEXT, Naturaleza TEXT, Es_Movimiento BOOLEAN)''')
    # Tabla Facturas 
    cursor.execute('''CREATE TABLE IF NOT EXISTS Libro_Compras 
                      (Factura TEXT PRIMARY KEY, Emision TEXT, NIT_Proveedor TEXT, Proveedor TEXT, Valor_Total REAL)''')
    # --- NUEVA TABLA: EL CEREBRO (LIBRO DIARIO) ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS Libro_Diario 
                      (ID_Asiento INTEGER, 
                       Numero_Comprobante TEXT,
                       Tipo_Comprobante TEXT,
                       Fecha TEXT,
                       Cuenta_Contable TEXT,
                       Descripcion TEXT,
                       Debe REAL,
                       Haber REAL,
                       NIT_Tercero TEXT)''')
    
    # --- 🛡️ AUTOSANACIÓN DE LA BASE DE DATOS 🛡️ ---
    # Elimina para siempre los '.0' que ya estén guardados en la tabla
    try:
        cursor.execute("UPDATE Plan_Cuentas SET Codigo_Cuenta = REPLACE(Codigo_Cuenta, '.0', '') WHERE Codigo_Cuenta LIKE '%.0'")
    except:
        pass
    # ----------------------------------------------

    conn.commit()
    conn.close()

def guardar_cuenta_puc(datos):
    conn = conectar()
    cursor = conn.cursor()
    
    # Limpieza extrema justo antes de inyectar a SQLite
    codigo_puro = str(datos['codigo']).strip().replace('.0', '')
    
    cursor.execute("INSERT OR REPLACE INTO Plan_Cuentas VALUES (?, ?, ?, ?)", 
                   (codigo_puro, datos['nombre'], datos['naturaleza'], datos['es_movimiento']))
    conn.commit()
    conn.close()

def obtener_cuentas_8_digitos():
    conn = conectar()
    # Doble seguridad: Trae solo cuentas de 8 caracteres reales QUE NO contengan puntos
    df = pd.read_sql_query("SELECT Codigo_Cuenta, Nombre_Cuenta FROM Plan_Cuentas WHERE length(Codigo_Cuenta) = 8 AND Codigo_Cuenta NOT LIKE '%.%'", conn)
    conn.close()
    return df

def guardar_tercero(datos, nombre="", direccion="", email="", telefono="", ciudad="", regimen="", tipo=""):
    if isinstance(datos, dict):
        nit = datos.get('NIT_Proveedor', datos.get('nit', ''))
        nombre = datos.get('Razon_Social_Proveedor', datos.get('nombre', ''))
        direccion = datos.get('Direccion_Proveedor', datos.get('direccion', ''))
        email = datos.get('Correo_Proveedor', datos.get('email', ''))
        telefono = datos.get('Telefono_Proveedor', datos.get('telefono', ''))
        ciudad = datos.get('Ciudad_Proveedor', datos.get('ciudad', ''))
        regimen = datos.get('regimen', '')
        tipo = datos.get('tipo', '')
    else:
        nit = datos
    
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO Terceros VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                   (nit, nombre, direccion, email, telefono, ciudad, regimen, tipo))
    conn.commit()
    conn.close()

def guardar_factura_en_libro(datos):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO Libro_Compras (Factura, Emision, NIT_Proveedor, Proveedor, Valor_Total) 
                      VALUES (?, ?, ?, ?, ?)''', 
                   (datos.get('ID_Factura'), 
                    datos.get('Fecha_Emision'), 
                    datos.get('NIT_Proveedor'), 
                    datos.get('Razon_Social_Proveedor'), 
                    datos.get('Total_Factura')))
    conn.commit()
    conn.close()

def obtener_siguiente_id_asiento():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(ID_Asiento) FROM Libro_Diario")
    resultado = cursor.fetchone()[0]
    conn.close()
    
    if resultado is None:
        return 1
    return resultado + 1

def guardar_lineas_diario(lineas_asiento):
    conn = conectar()
    cursor = conn.cursor()
    
    sql = '''INSERT INTO Libro_Diario 
             (ID_Asiento, Numero_Comprobante, Tipo_Comprobante, Fecha, 
              Cuenta_Contable, Descripcion, Debe, Haber, NIT_Tercero) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
             
    valores = [
        (linea['ID_Asiento'], linea['Numero_Comprobante'], linea['Tipo_Comprobante'], 
         linea['Fecha'], linea['Cuenta_Contable'], linea['Descripcion'], 
         linea['Debe'], linea['Haber'], linea['NIT_Tercero'])
        for linea in lineas_asiento
    ]
    
    cursor.executemany(sql, valores)
    conn.commit()
    conn.close()