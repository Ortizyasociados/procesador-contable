import pandas as pd
import sqlite3

def ejecutar_carga():
    # 1. Leer el archivo
    df = pd.read_csv('Plan_De_Cuentas_Actualizado.csv')
    
    # 2. Conectar y limpiar/cargar la tabla
    conn = sqlite3.connect("contabilidad.db")
    
    # Esta línea vuelca todo tu archivo a la base de datos
    df.to_sql('Plan_Cuentas', conn, if_exists='replace', index=False)
    
    conn.commit()
    conn.close()
    print("¡Listo! Tu PUC está cargado en la base de datos.")

ejecutar_carga()
