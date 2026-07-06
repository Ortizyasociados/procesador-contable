import pandas as pd
from base_datos import guardar_cuenta_puc, inicializar_base_datos

def ejecutar_carga():
    # --- LA PIEZA CLAVE ---
    # Esto construye las tablas vacías en el archivo nuevo antes de inyectar datos
    inicializar_base_datos()
    # ----------------------
    
    archivo_csv = 'Plan_de_Cuentas_Actualizado.csv'
    
    # Lectura corregida con manejo de comas y alineación perfecta
    df = pd.read_csv(
        archivo_csv, 
        encoding='latin-1', 
        dtype={'CODIGO': str, 'NOMBRE CUENTA': str, 'NATURALEZA': str, 'ACUMULA': str},
        on_bad_lines='skip'
    )
    
    print(f"Iniciando carga de {len(df)} cuentas...")
    
    for _, fila in df.iterrows():
        # Limpieza estricta del código
        codigo_original = str(fila['CODIGO']).strip()
        codigo_limpio = codigo_original.split('.')[0]
        
        # Validación de la lógica de movimiento (SI acumula = NO es cuenta operativa)
        acumula_valor = str(fila['ACUMULA']).strip().upper()
        es_movimiento_real = False if acumula_valor == 'SI' else True
        
        datos = {
            'codigo': codigo_limpio,
            'nombre': str(fila['NOMBRE CUENTA']).strip(),
            'nivel': 1, 
            'padre': None,
            'naturaleza': str(fila['NATURALEZA']).strip(),
            'es_movimiento': es_movimiento_real
        }
        guardar_cuenta_puc(datos)
        
    print("¡Proceso completado con éxito! Las cuentas han sido cargadas.")

if __name__ == "__main__":
    ejecutar_carga()
    

