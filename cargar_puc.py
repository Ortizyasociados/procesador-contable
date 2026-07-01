import pandas as pd
from base_datos import guardar_cuenta_puc

def ejecutar_carga():
    # Leer el archivo con los encabezados exactos detectados
    df = pd.read_csv('Plan_De_Cuentas_Actualizado.csv')
    
    print(f"Iniciando carga de {len(df)} cuentas...")
    
    # Iterar sobre el archivo y guardar fila por fila
    for _, fila in df.iterrows():
        datos = {
            'codigo': str(fila['Codigo_Cuenta']),
            'nombre': fila['Nombre_Cuenta'],
            'nivel': int(fila['Nivel']),
            'padre': str(fila['Codigo_Padre']),
            'naturaleza': fila['Naturaleza'],
            'es_movimiento': bool(fila['Es_Movimiento'])
        }
        guardar_cuenta_puc(datos)
        
    print("¡Proceso completado con éxito! El PUC ha sido cargado en la base de datos.")

if __name__ == "__main__":
    ejecutar_carga()
