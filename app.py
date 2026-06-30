import pandas as pd
from lxml import etree
import streamlit as st
import os
import shutil
import sqlite3
import zipfile
import base_datos # Solo añadí esta línea para conectar con tu archivo base_datos.py

# Configuración inicial
st.set_page_config(page_title="Ortiz y Asociados", layout="wide")

# ESTILO PROFESIONAL (CSS REFINADO)
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

# DISTRIBUCIÓN
# Usamos el sidebar nativo de Streamlit para el control, es más limpio
with st.sidebar:
    st.markdown('<div style="font-family: sans-serif; font-size: 20px; font-weight: bold; color: white;">ORTIZ Y ASOCIADOS</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.write("Panel de Operaciones")
    uploaded_files = st.file_uploader("Cargar ZIP de facturas", type=["zip"])
    
    # EL BOTÓN DE TERCEROS BIEN POSICIONADO
    if st.button("Ver Terceros Registrados"):
        st.session_state.mostrar_terceros = True
    else:
        st.session_state.mostrar_terceros = False

# CONTENIDO PRINCIPAL
st.header("Gestión de Procesamiento")
st.markdown("---")

if st.session_state.get('mostrar_terceros', False):
    st.subheader("Base de Datos: Terceros")
    try:
        conn = sqlite3.connect("contabilidad.db")
        df_terceros = pd.read_sql_query("SELECT * FROM Terceros", conn)
        conn.close()
        st.dataframe(df_terceros, use_container_width=True)
    except:
        st.error("No se encontraron registros.")
else:
    st.info("Utiliza el panel lateral para cargar archivos o visualizar los terceros registrados.")

# Ocultar elementos de Streamlit
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)
if uploaded_files:
    lista_datos = []
    ns = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    }

    # Procesar cada archivo subido
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
                            else:
                                continue 

                        if invoice_tree is not None:
                            payment_means_code = invoice_tree.findtext('.//cac:PaymentMeans/cbc:PaymentMeansCode', namespaces=ns)
                            due_date = invoice_tree.findtext('.//cbc:DueDate', namespaces=ns) or invoice_tree.findtext('.//cac:PaymentTerms/cbc:PaymentDueDate', namespaces=ns)

                            tipo_pago = 'Contado'
                            if payment_means_code == '30' or due_date: 
                                tipo_pago = 'Crédito'

                            nit_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyTaxScheme/cbc:CompanyID', namespaces=ns)
                            if not nit_adquirente:
                                nit_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID', namespaces=ns)

                            supplier_party_node = invoice_tree.find('.//cac:AccountingSupplierParty/cac:Party', namespaces=ns)
                            acquirer_party_node = invoice_tree.find('.//cac:AccountingCustomerParty/cac:Party', namespaces=ns)

                            def get_address_info(party_node, ns):
                                if party_node is None:
                                    return '', None
                                street_name = party_node.findtext('.//cac:PostalAddress/cac:AddressLine/cbc:Line', namespaces=ns)
                                if not street_name: street_name = party_node.findtext('.//cac:PhysicalLocation/cac:Address/cac:AddressLine/cbc:Line', namespaces=ns)
                                if not street_name: street_name = party_node.findtext('.//cac:RegistrationAddress/cac:AddressLine/cbc:Line', namespaces=ns)
                                if not street_name: street_name = party_node.findtext('.//cac:PostalAddress/cbc:StreetName', namespaces=ns)
                                if not street_name: street_name = party_node.findtext('.//cbc:StreetName', namespaces=ns)

                                additional_street_name = party_node.findtext('.//cac:PostalAddress/cbc:AdditionalStreetName', namespaces=ns)
                                if not additional_street_name: additional_street_name = party_node.findtext('.//cbc:AdditionalStreetName', namespaces=ns)

                                city_name = party_node.findtext('.//cac:PhysicalLocation/cac:Address/cbc:CityName', namespaces=ns)
                                if not city_name: city_name = party_node.findtext('.//cac:RegistrationAddress/cbc:CityName', namespaces=ns)
                                if not city_name: city_name = party_node.findtext('.//cac:PostalAddress/cbc:CityName', namespaces=ns)
                                if not city_name: city_name = party_node.findtext('.//cac:Address/cbc:CityName', namespaces=ns)
                                if not city_name: city_name = party_node.findtext('.//cbc:CityName', namespaces=ns)

                                full_address = street_name if street_name else ''
                                if additional_street_name: full_address = f"{full_address}, {additional_street_name}"

                                return full_address.strip(), city_name

                            supplier_address, supplier_city = get_address_info(supplier_party_node, ns)
                            supplier_phone = supplier_party_node.findtext('.//cac:Contact/cbc:Telephone', namespaces=ns) if supplier_party_node is not None else None
                            supplier_email = supplier_party_node.findtext('.//cac:Contact/cbc:ElectronicMail', namespaces=ns) if supplier_party_node is not None else None

                            total_impuestos_sum = 0.0
                            otros_impuestos_sum = 0.0

                            for tax_total_node in invoice_tree.findall('.//cac:TaxTotal', namespaces=ns):
                                for tax_subtotal_node in tax_total_node.findall('.//cac:TaxSubtotal', namespaces=ns):
                                    tax_amount_str = tax_subtotal_node.findtext('.//cbc:TaxAmount', namespaces=ns)
                                    tax_amount = float(tax_amount_str) if tax_amount_str else 0.0
                                    total_impuestos_sum += tax_amount
                                    tax_type_code = tax_subtotal_node.findtext('.//cac:TaxCategory/cbc:TaxScheme/cbc:TaxTypeCode', namespaces=ns)
                                    if tax_type_code and tax_type_code.upper() not in ['VAT', 'IVA', '01']:
                                        otros_impuestos_sum += tax_amount

                            razon_social_proveedor = invoice_tree.findtext('.//cac:AccountingSupplierParty//cac:PartyName/cbc:Name', namespaces=ns)
                            if not razon_social_proveedor:
                                razon_social_proveedor = invoice_tree.findtext('.//cac:AccountingSupplierParty//cac:PartyLegalEntity/cbc:RegistrationName', namespaces=ns)
                            razon_social_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyName/cbc:Name', namespaces=ns)

                            datos = {
                                'ID_Factura': invoice_tree.findtext('.//cbc:ID', namespaces=ns),
                                'Fecha_Emision': invoice_tree.findtext('.//cbc:IssueDate', namespaces=ns),
                                'Fecha_Vencimiento': due_date,
                                'Tipo_Pago': tipo_pago,
                                'NIT_Proveedor': invoice_tree.findtext('.//cac:AccountingSupplierParty//cbc:CompanyID', namespaces=ns),
                                'Razon_Social_Proveedor': razon_social_proveedor,
                                'Direccion_Proveedor': supplier_address,
                                'Telefono_Proveedor': supplier_phone,
                                'Correo_Proveedor': supplier_email,
                                'Ciudad_Proveedor': supplier_city,
                                'NIT_Adquirente': nit_adquirente,
                                'Razon_Social_Adquirente': razon_social_adquirente,
                                'Moneda': invoice_tree.findtext('.//cbc:DocumentCurrencyCode', namespaces=ns),
                                'Total_Base_Impuestos': float(invoice_tree.findtext('.//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', namespaces=ns) or 0),
                                'Total_Impuestos': total_impuestos_sum,
                                'Otros_Impuestos': otros_impuestos_sum,
                                'Total_Factura': float(invoice_tree.findtext('.//cbc:PayableAmount', namespaces=ns) or 0)
                            }
                            lista_datos.append(datos)
                            base_datos.guardar_tercero(datos) # Llamada externa a tu base_datos.py
                    except Exception as e:
                        print(f"Error procesando {file}: {e}")

        if os.path.exists(extracted_path):
            shutil.rmtree(extracted_path)
        os.remove(zip_name)

    # 3. Crear el libro de compras
    df = pd.DataFrame(lista_datos)
    df_columns_order = ['ID_Factura', 'Fecha_Emision', 'Fecha_Vencimiento', 'Tipo_Pago', 'NIT_Proveedor', 'Razon_Social_Proveedor', 'Direccion_Proveedor', 'Telefono_Proveedor', 'Correo_Proveedor', 'Ciudad_Proveedor', 'NIT_Adquirente', 'Razon_Social_Adquirente', 'Moneda', 'Total_Base_Impuestos', 'Total_Impuestos', 'Otros_Impuestos', 'Total_Factura']
    for col in df_columns_order:
        if col not in df.columns: df[col] = None
    df = df[df_columns_order]

    df['Fecha_Emision'] = pd.to_datetime(df['Fecha_Emision'], errors='coerce')
    df['Fecha_Vencimiento'] = pd.to_datetime(df['Fecha_Vencimiento'], errors='coerce')
    df = df.sort_values(by='Fecha_Emision').reset_index(drop=True)
    df.insert(0, 'No_Item', range(1, 1 + len(df)))

    # --- LÓGICA ORIGINAL DE BASE_EXENTA ---
    df['Base_Exenta'] = df.apply(
    lambda row: row['Total_Factura'] if (pd.isna(row['Total_Base_Impuestos']) or row['Total_Base_Impuestos'] == 0) else 0, 
    axis=1)
    df_columns_order_final = ['No_Item', 'ID_Factura', 'Fecha_Emision', 'Fecha_Vencimiento', 'Tipo_Pago', 'NIT_Proveedor', 'Razon_Social_Proveedor', 'Direccion_Proveedor', 'Telefono_Proveedor', 'Correo_Proveedor', 'Ciudad_Proveedor', 'NIT_Adquirente', 'Razon_Social_Adquirente', 'Moneda', 'Total_Base_Impuestos', 'Base_Exenta', 'Total_Impuestos', 'Otros_Impuestos', 'Total_Factura']
    df = df[df_columns_order_final]

    total_row = pd.DataFrame([{
        'No_Item': None, 'ID_Factura': 'TOTAL', 'Fecha_Emision': None, 'Fecha_Vencimiento': None, 'Tipo_Pago': None, 'NIT_Proveedor': None, 'Razon_Social_Proveedor': None, 'Direccion_Proveedor': None, 'Telefono_Proveedor': None, 'Correo_Proveedor': None, 'Ciudad_Proveedor': None, 'NIT_Adquirente': None, 'Razon_Social_Adquirente': None, 'Moneda': None, 'Total_Base_Impuestos': df['Total_Base_Impuestos'].sum(), 'Base_Exenta': df['Base_Exenta'].sum(), 'Total_Impuestos': df['Total_Impuestos'].sum(), 'Otros_Impuestos': df['Otros_Impuestos'].sum(), 'Total_Factura': df['Total_Factura'].sum()
    }])
    df_final = pd.concat([df, total_row], ignore_index=True)

    st.write("Libro de Compras generado:")
    st.dataframe(df_final)

    # 4. Descargar a Excel
    output_file = "Libro_Compras_Final.xlsx"
    df_final.to_excel(output_file, index=False)
    with open(output_file, "rb") as f:
        st.download_button("Descargar Libro de Compras", f, file_name=output_file)
