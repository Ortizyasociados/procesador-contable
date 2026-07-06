import pandas as pd
from lxml import etree
import streamlit as st
import os
import shutil
import sqlite3
import zipfile
import base_datos 

# Abre app.py y busca la parte superior donde importas tus módulos
import streamlit as st
import base_datos 

# --- AÑADE ESTAS LÍNEAS AQUÍ ---
# Esto garantiza que al arrancar la app, las tablas existan siempre
base_datos.inicializar_base_datos() 
# -------------------------------

# Configuración inicial
st.set_page_config(page_title="Ortiz y Asociados", layout="wide")

# --- NUEVO: INICIALIZAR MEMORIA DE PENDIENTES ---
if 'pendientes' not in st.session_state:
    st.session_state['pendientes'] = []
# ------------------------------------------------

# ESTILO PROFESIONAL
st.markdown("""
    <style>
    .stApp { background-color: #0f1115; }
    [data-testid="stSidebar"] { background-color: #171a1f; border-right: 1px solid #2d3139; }
    h1 { color: #ffffff !important; font-size: 2rem !important; }
    h3 { color: #8b949e !important; font-weight: 300 !important; }
    .stButton>button { background-color: #2e5a88 !important; color: white !important; border: none !important; width: 100%; border-radius: 4px; }
    .stButton>button:hover { background-color: #3b74b0 !important; }
    </style>
""", unsafe_allow_html=True)

# PANEL LATERAL
with st.sidebar:
    st.markdown('<div style="font-family: \'Georgia\', serif; font-size: 32px; font-weight: bold; color: white;">ORTIZ Y ASOCIADOS</div>', unsafe_allow_html=True)
    st.markdown("---")
    opcion = st.radio("MENÚ DE OPERACIONES", ["Bienvenida", "Subir Factura", "Editar Tercero", "Crear Comprobante"])

# --- LÓGICA DE NAVEGACIÓN ---

if opcion == "Bienvenida":
    st.title("Bienvenido al Sistema")
    st.write("Utilice el menú lateral para seleccionar una operación.")

elif opcion == "Subir Factura":
    st.title("Procesar Facturas")
    uploaded_files = st.file_uploader("Cargar ZIP de facturas (Puedes seleccionar varios)", type=["zip"], accept_multiple_files=True)

    if uploaded_files:
        lista_datos = []
        ns = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
        }
        
        def parse_float(valor):
            if not valor: return 0.0
            return float(str(valor).replace(',', '.'))

        for uploaded_file in uploaded_files:
            zip_name = uploaded_file.name
            with open(zip_name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            extracted_path = f"temp_data_{os.path.splitext(zip_name)[0]}"
            os.makedirs(extracted_path, exist_ok=True)
            
            with zipfile.ZipFile(zip_name, 'r') as zip_ref:
                zip_ref.extractall(extracted_path)
            
            for root_dir, dirs, files_list in os.walk(extracted_path):
                for file in files_list:
                    if file.endswith(".xml"):
                        try:
                            tree = etree.parse(os.path.join(root_dir, file))
                            root = tree.getroot()
                            cdata_content_node = root.find('.//cac:ExternalReference/cbc:Description', ns)
                            invoice_tree = None
                            
                            if cdata_content_node is not None and cdata_content_node.text:
                                cdata_content = cdata_content_node.text
                                invoice_tree = etree.fromstring(cdata_content.encode('utf-8'))
                            else:
                                if root.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice':
                                    invoice_tree = root
                            
                            if invoice_tree is not None:
                                payment_means_code = invoice_tree.findtext('.//cac:PaymentMeans/cbc:PaymentMeansCode', namespaces=ns)
                                due_date = invoice_tree.findtext('.//cbc:DueDate', namespaces=ns) or invoice_tree.findtext('.//cac:PaymentTerms/cbc:PaymentDueDate', namespaces=ns)
                                tipo_pago = 'Crédito' if (payment_means_code == '30' or due_date) else 'Contado'
                                
                                nit_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyTaxScheme/cbc:CompanyID', namespaces=ns) or invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID', namespaces=ns)
                                razon_social_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyTaxScheme/cbc:RegistrationName', namespaces=ns)
                                
                                supplier_party_node = invoice_tree.find('.//cac:AccountingSupplierParty/cac:Party', namespaces=ns)
                                
                                def get_address_info(party_node, ns):
                                    if party_node is None: return '', None
                                    street_name = party_node.findtext('.//cac:PostalAddress/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:PhysicalLocation/cac:Address/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:RegistrationAddress/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:PostalAddress/cbc:StreetName', namespaces=ns) or party_node.findtext('.//cbc:StreetName', namespaces=ns)
                                    city_name = party_node.findtext('.//cac:PhysicalLocation/cac:Address/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:RegistrationAddress/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:PostalAddress/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:Address/cbc:CityName', namespaces=ns) or party_node.findtext('.//cbc:CityName', namespaces=ns)
                                    return (street_name or '').strip(), city_name
                                
                                supplier_address, supplier_city = get_address_info(supplier_party_node, ns)
                                supplier_phone = supplier_party_node.findtext('.//cac:Contact/cbc:Telephone', namespaces=ns) if supplier_party_node is not None else None
                                supplier_email = supplier_party_node.findtext('.//cac:Contact/cbc:ElectronicMail', namespaces=ns) if supplier_party_node is not None else None
                                
                                descripcion_nodos = invoice_tree.xpath('.//cac:InvoiceLine/cac:Item/cbc:Description', namespaces=ns)
                                descripcion_items = ", ".join([n.text for n in descripcion_nodos if n.text])

                                # --- LÓGICA DE IMPUESTOS Y BASES ---
                                impuestos_factura = {
                                    'Base_Exenta': 0.0,
                                    'Base_IVA_5': 0.0, 'Valor_IVA_5': 0.0,
                                    'Base_IVA_19': 0.0, 'Valor_IVA_19': 0.0,
                                    'Otros_Impuestos': 0.0
                                }
                                
                                for parent_node in invoice_tree.xpath('./cac:TaxTotal | ./cac:WithholdingTaxTotal', namespaces=ns):
                                    for tax_sub in parent_node.findall('.//cac:TaxSubtotal', namespaces=ns):
                                        tax_id = tax_sub.findtext('.//cac:TaxScheme/cbc:ID', namespaces=ns)
                                        
                                        porcentaje_str = tax_sub.findtext('.//cac:TaxCategory/cbc:Percent', namespaces=ns)
                                        porcentaje = parse_float(porcentaje_str) if porcentaje_str else 0.0
                                        
                                        base_impuesto = parse_float(tax_sub.findtext('.//cbc:TaxableAmount', namespaces=ns))
                                        valor_impuesto = parse_float(tax_sub.findtext('.//cbc:TaxAmount', namespaces=ns))
                                        
                                        if tax_id == '01': # IVA
                                            if porcentaje == 19.0:
                                                impuestos_factura['Base_IVA_19'] += base_impuesto
                                                impuestos_factura['Valor_IVA_19'] += valor_impuesto
                                            elif porcentaje == 5.0:
                                                impuestos_factura['Base_IVA_5'] += base_impuesto
                                                impuestos_factura['Valor_IVA_5'] += valor_impuesto
                                            elif porcentaje == 0.0:
                                                impuestos_factura['Base_Exenta'] += base_impuesto
                                        else:
                                            # Cualquier otro impuesto o retención se va a "Otros Impuestos"
                                            impuestos_factura['Otros_Impuestos'] += valor_impuesto

                                monetary_total = invoice_tree.find('.//cac:LegalMonetaryTotal', namespaces=ns)
                                
                                datos = {
                                    'ID_Factura': invoice_tree.findtext('.//cbc:ID', namespaces=ns),
                                    'Fecha_Emision': invoice_tree.findtext('.//cbc:IssueDate', namespaces=ns),
                                    'Fecha_Vencimiento': due_date,
                                    'Tipo_Pago': tipo_pago,
                                    'NIT_Proveedor': invoice_tree.findtext('.//cac:AccountingSupplierParty//cbc:CompanyID', namespaces=ns),
                                    'Razon_Social_Proveedor': invoice_tree.findtext('.//cac:AccountingSupplierParty//cbc:RegistrationName', namespaces=ns),
                                    'Direccion_Proveedor': supplier_address,
                                    'Telefono_Proveedor': supplier_phone,
                                    'Correo_Proveedor': supplier_email,
                                    'Ciudad_Proveedor': supplier_city,
                                    'NIT_Adquirente': nit_adquirente,
                                    'Razon_Social_Adquirente': razon_social_adquirente,
                                    'Descripcion_Items': descripcion_items,
                                    'Moneda': invoice_tree.findtext('.//cbc:DocumentCurrencyCode', namespaces=ns),
                                    'Total_Factura': parse_float(monetary_total.findtext('cbc:PayableAmount', namespaces=ns))
                                }
                                
                                datos.update(impuestos_factura)
                                lista_datos.append(datos)
                                
                                base_datos.guardar_tercero(datos)
                                base_datos.guardar_factura_en_libro(datos)
                                
                        except Exception as e:
                            st.error(f"Error procesando {file} del ZIP {zip_name}: {e}")
                            
            if os.path.exists(extracted_path): shutil.rmtree(extracted_path)
            os.remove(zip_name)
            
        # --- Formateo Limpio para la Interfaz de Streamlit ---
        if lista_datos:

            # --- NUEVO: GUARDAR EN LA COLA DE PENDIENTES ---
            for dato in lista_datos:
                st.session_state['pendientes'].append(dato)
            # -----------------------------------------------

            st.success(f"¡Se procesaron {len(lista_datos)} factura(s) de {len(uploaded_files)} ZIP(s) correctamente!")
            df = pd.DataFrame(lista_datos)
            
            # ORDEN CRONOLÓGICO: Ordenar por fecha de emisión
            df = df.sort_values(by='Fecha_Emision').reset_index(drop=True)
            
            # NÚMERO DE ÍTEM: Crear la columna al principio
            df['Item'] = df.index + 1
            
            # Ajustar las columnas visibles incluyendo Item y Tipo_Pago
            columnas_visibles = [
                'Item', 'ID_Factura', 'Fecha_Emision', 'Fecha_Vencimiento', 'Tipo_Pago',
                'NIT_Proveedor', 'Razon_Social_Proveedor', 'Correo_Proveedor', 'Telefono_Proveedor', 'Direccion_Proveedor', 'Ciudad_Proveedor',
                'NIT_Adquirente', 'Razon_Social_Adquirente', 'Descripcion_Items', 
                'Base_Exenta', 'Base_IVA_5', 'Valor_IVA_5', 'Base_IVA_19', 'Valor_IVA_19', 'Otros_Impuestos', 'Total_Factura'
            ]
            
            df_display = df[[col for col in columnas_visibles if col in df.columns]].copy()
            
            # Renombrar para estética
            df_display = df_display.rename(columns={
                'ID_Factura': 'Factura',
                'Fecha_Emision': 'Emisión',
                'Fecha_Vencimiento': 'Vencimiento',
                'Tipo_Pago': 'Tipo Pago',
                'Razon_Social_Proveedor': 'Proveedor',
                'Razon_Social_Adquirente': 'Cliente',
                'Descripcion_Items': 'Detalle'
            })
            
            # CÁLCULO DE TOTALES
            columnas_moneda = [
                'Base_Exenta', 'Base_IVA_5', 'Valor_IVA_5', 'Base_IVA_19', 'Valor_IVA_19', 'Otros_Impuestos', 'Total_Factura'
            ]
            
            # Crear un diccionario para la fila de totales con valores en blanco para texto
            fila_totales = {col: '' for col in df_display.columns}
            fila_totales['Item'] = ''
            fila_totales['Factura'] = 'TOTALES'
            
            # Sumar las columnas numéricas
            for col in columnas_moneda:
                if col in df_display.columns:
                    fila_totales[col] = df_display[col].sum()
            
            # Añadir la fila de totales al final del DataFrame
            df_totales = pd.DataFrame([fila_totales])
            df_display = pd.concat([df_display, df_totales], ignore_index=True)
            
            # Aplicar formato de moneda SOLO a valores numéricos (ignora textos vacíos)
            for col in columnas_moneda:
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else x)
            
            st.write("### Libro de Compras Consolidado")
            st.dataframe(df_display, use_container_width=True, hide_index=True)

elif opcion == "Editar Tercero":
    st.title("Gestión de Terceros y PUC")
    
    import sqlite3
    import pandas as pd
    
    # 1. CONECTAR Y LEER LA BASE DE DATOS REAL (Lo que ya tienes guardado)
    conn = sqlite3.connect("contabilidad.db")
    terceros_bd = pd.read_sql_query("SELECT * FROM Terceros", conn)
    conn.close()

    # 2. MOSTRAR LA BASE DE DATOS EN PANTALLA
    st.subheader("Base de Datos Actual de Terceros")
    if terceros_bd.empty:
        st.warning("La base de datos de terceros está vacía. Sube un XML primero.")
    else:
            # --- FILTRADO DE LA TAREA 2 ---
            # 1. Eliminamos las filas que tengan el NIT vacío o nulo (quita la fila 0 en blanco)
            terceros_bd = terceros_bd.dropna(subset=['NIT'])
            terceros_bd = terceros_bd[terceros_bd['NIT'].astype(str).str.strip() != ""]
            
            # Evitamos errores si las columnas de cuentas aún no se han creado en el DataFrame
            if 'Cuenta_Principal' not in terceros_bd.columns:
                terceros_bd['Cuenta_Principal'] = ""
            if 'Cuenta_CXP' not in terceros_bd.columns:
                terceros_bd['Cuenta_CXP'] = ""
            
            # 2. Filtramos para mostrar únicamente las columnas requeridas (¡Ahora incluye las cuentas!)
            columnas_visibles = ['NIT', 'Razon_Social', 'Telefono', 'Email', 'Cuenta_Principal', 'Cuenta_CXP']
            df_vista = terceros_bd[columnas_visibles]
            
            # 3. Pintamos la tabla limpia, sin índices automáticos de fila
            st.dataframe(df_vista, hide_index=True, use_container_width=True)
            # -------------------------------
            
            st.markdown("---")
            st.subheader("Asignar o Actualizar Cuentas del Tercero")
            
            # Leemos el PUC usando la función que ya tienes
            df_cuentas = base_datos.obtener_cuentas_8_digitos()
            
            if df_cuentas.empty:
                st.warning("No hay cuentas registradas en el PUC.")
            else:
                # Preparamos las listas para los desplegables
                lista_terceros = terceros_bd['NIT'].astype(str) + " - " + terceros_bd['Razon_Social']
                lista_cuentas = df_cuentas['Codigo_Cuenta'].astype(str) + " - " + df_cuentas['Nombre_Cuenta']
                
                # Formulario para actualizar
                with st.form("form_actualizar_tercero"):
                    sel_tercero = st.selectbox("1. Selecciona el Tercero a actualizar", lista_terceros)
                    cta_ppal = st.selectbox("2. Cuenta Principal (Gasto/Ingreso)", lista_cuentas)
                    cta_cobrar_pagar = st.selectbox("3. Cuenta por Cobrar o Pagar", lista_cuentas)
                    
                    if st.form_submit_button("Actualizar Tercero"):
                        import sqlite3
                        
                        # Extraemos solo los números (NIT y Códigos) quitando el texto
                        nit_puro = sel_tercero.split(" - ")[0].strip()
                        codigo_ppal = cta_ppal.split(" - ")[0].strip()
                        codigo_cxp = cta_cobrar_pagar.split(" - ")[0].strip()
                        
                        # Conectamos y damos la orden REAL a la base de datos
                        conn_update = sqlite3.connect("contabilidad.db")
                        cursor_update = conn_update.cursor()
                        
                        # Nos aseguramos de que las columnas existan físicamente en la BD
                        try:
                            cursor_update.execute("ALTER TABLE Terceros ADD COLUMN Cuenta_Principal TEXT")
                            cursor_update.execute("ALTER TABLE Terceros ADD COLUMN Cuenta_CXP TEXT")
                            conn_update.commit()
                        except:
                            pass # Si ya existen, sigue derecho
                        
                        # Guardamos definitivamente las cuentas asignadas
                        cursor_update.execute("""
                            UPDATE Terceros 
                            SET Cuenta_Principal = ?, 
                                Cuenta_CXP = ? 
                            WHERE NIT = ?
                        """, (codigo_ppal, codigo_cxp, nit_puro))
                        
                        conn_update.commit()
                        conn_update.close()
                        
                        # Confirmación y recarga automática de la pantalla para ver la tabla actualizada
                        st.success("✅ Cuentas asignadas al tercero exitosamente.")
                        st.rerun()
                        
elif opcion == "Crear Comprobante":
    st.title("Generador de Comprobantes")

    # ESTRUCTURA PRINCIPAL: 70% Izquierda (Causación/Pagos), 30% Derecha (Visor)
    col_izq, col_der = st.columns([7, 3])

    with col_izq:
        # --- SECCIÓN SUPERIOR: CAUSACIÓN ---
        st.markdown("### Causación de Documentos")
        with st.container(border=True):
            
            # --- 1. BOTONES DE CONTROL DE LA COLA ---
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button(f"Llamar de Pendientes ({len(st.session_state['pendientes'])})"):
                    if len(st.session_state['pendientes']) > 0:
                        # CORRECCIÓN: Leemos el primero [0] SIN sacarlo de la lista (.pop lo borraba)
                        factura_actual = st.session_state['pendientes'][0]
                        st.session_state['comprobante_actual'] = factura_actual
                        st.rerun()
                    else:
                        st.warning("No hay operaciones pendientes por procesar.")
            
            with col_btn2:
                if st.button("Carga Manual"):
                    st.session_state['comprobante_actual'] = {}
                    st.rerun()

            st.markdown("---")

            # --- 2. PREPARACIÓN DE DATOS Y ENCABEZADO ---
            import datetime
            import sqlite3

            comp = st.session_state.get('comprobante_actual', {})

            # Formateamos la fecha del XML si existe
            fecha_defecto = datetime.date.today()
            if 'Fecha_Emision' in comp and comp['Fecha_Emision']:
                try:
                    fecha_defecto = datetime.datetime.strptime(comp['Fecha_Emision'], "%Y-%m-%d").date()
                except:
                    pass

            # --- 3. DISTRIBUCIÓN VISUAL (ORDEN DE IMPORTANCIA) ---
            # Fila 1: Datos de identificación del Tercero
            col_r1_1, col_r1_2 = st.columns([1, 2])
            with col_r1_1:
                nit_tercero = st.text_input("NIT", value=comp.get('NIT_Proveedor', ''))
            with col_r1_2:
                razon_social = st.text_input("Razón Social / Nombre", value=comp.get('Razon_Social_Proveedor', ''))

            # Fila 2: Datos de contacto
            col_r2_1, col_r2_2 = st.columns(2)
            with col_r2_1:
                st.text_input("Teléfono", value=comp.get('Telefono_Proveedor', ''))
            with col_r2_2:
                st.text_input("Correo", value=comp.get('Correo_Proveedor', ''))

            # Fila 3: Datos específicos del Documento Origen y Fecha
            col_r3_1, col_r3_2 = st.columns(2)
            with col_r3_1:
                st.text_input("Factura Electrónica (Origen)", value=comp.get('ID_Factura', ''))
            with col_r3_2:
                fecha_comprobante = st.date_input("Fecha de Contabilización", value=fecha_defecto)

            # Fila 4: Tipo de Comprobante y cálculo del Correlativo Automático
            col_r4_1, col_r4_2 = st.columns(2)
            with col_r4_1:
                tipo_comprobante = st.selectbox("Tipo de Comprobante", ["Compra", "Venta", "Egreso", "Ingreso", "Nota Contable"])

            # CONSULTA DEL CORRELATIVO AUTOMÁTICO REAL
            conn_corr = sqlite3.connect("contabilidad.db")
            cursor_corr = conn_corr.cursor()
            # Buscamos el número más alto para ese tipo de comprobante en el Libro_Diario
            cursor_corr.execute("SELECT MAX(CAST(Numero_Comprobante AS INTEGER)) FROM Libro_Diario WHERE Tipo_Comprobante = ?", (tipo_comprobante,))
            max_actual = cursor_corr.fetchone()[0]
            conn_corr.close()

            # Si no hay ninguno, arranca en 1. Si hay, le suma 1.
            siguiente_correlativo = 1 if max_actual is None else max_actual + 1

            with col_r4_2:
                # El correlativo se muestra real, automático y protegido
                st.text_input("Número Comprobante (Correlativo)", value=str(siguiente_correlativo), disabled=True)

            st.markdown("---")
            st.write("**Detalle del Asiento (Sumas Iguales)**")
            # Espacio reservado para la tabla editable (Data Editor)
            # --- LÓGICA DE LA TABLA DINÁMICA (ASIENTO CONTABLE) ---
            # 1. Inicializamos la tabla vacía en memoria si no existe
            if 'tabla_asiento' not in st.session_state:
                # Estructura base de las líneas del comprobante
                st.session_state['tabla_asiento'] = pd.DataFrame({
                    "Cuenta": ["", ""],          # Espacio para las cuentas
                    "Descripción": ["", ""],     # Detalle del movimiento
                    "Debe": [0.0, 0.0],          # Valores débito
                    "Haber": [0.0, 0.0]          # Valores crédito
                })

            # 2. Mostramos la tabla interactiva
            # num_rows="dynamic" permite al usuario agregar o eliminar filas libremente
            df_asiento = st.data_editor(
                st.session_state['tabla_asiento'],
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Debe": st.column_config.NumberColumn("Debe", format="$%.2f", min_value=0.0),
                    "Haber": st.column_config.NumberColumn("Haber", format="$%.2f", min_value=0.0)
                },
                key="editor_asiento"
            )

            # 3. Validación en tiempo real (Sumas Iguales)
            total_debe = df_asiento['Debe'].sum()
            total_haber = df_asiento['Haber'].sum()
            diferencia = abs(total_debe - total_haber)

            col_tot1, col_tot2, col_tot3 = st.columns(3)
            with col_tot1:
                st.metric("Total Debe", f"${total_debe:,.2f}")
            with col_tot2:
                st.metric("Total Haber", f"${total_haber:,.2f}")
            with col_tot3:
                if diferencia <= 0.01 and total_debe > 0: # Margen por decimales
                    st.success("✅ Asiento Cuadrado")
                else:
                    st.error(f"⚠️ Diferencia: ${diferencia:,.2f}")
        # --- SECCIÓN INFERIOR: PAGOS Y CRUCES (Independiente) ---
        st.markdown("<br>", unsafe_allow_html=True) # Espacio visual
        
        # El toggle hace que la sección inferior aparezca solo si el usuario la necesita
        activar_pagos = st.toggle("Activar Modo Pago / Cruce (Comprobantes Existentes)")
        
        if activar_pagos:
            with st.container(border=True):
                st.markdown("### Gestión de Pagos y Cruces")
                col_busq1, col_busq2 = st.columns(2)
                with col_busq1:
                    st.text_input("Buscar por NIT Tercero")
                with col_busq2:
                    st.text_input("Buscar por Número de Comprobante original")
                
                st.button("Buscar en Libro Diario")
                st.info("Los resultados y el formulario para realizar el pago/cruce aparecerán aquí.")

    with col_der:
        # --- SECCIÓN DERECHA: VISOR PDF ---
        st.markdown("### Visor de Documento")
        with st.container(border=True, height=750):
            st.write("📄 El PDF de la factura se previsualizará en este espacio al llamarlo desde la lista de pendientes.")