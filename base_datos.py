import sqlite3

def guardar_tercero(nit, razon, dir, ciu, tel, mail):
    conn = sqlite3.connect("contabilidad.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO Terceros (NIT, Razon_Social, Direccion, Ciudad, Telefono, Email)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nit, razon, dir, ciu, tel, mail))
    conn.commit()
    conn.close()
