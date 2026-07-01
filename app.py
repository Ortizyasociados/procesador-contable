import pandas as pd
from lxml import etree
import streamlit as st
import os
import shutil
import sqlite3
import zipfile
import base_datos 

# Configuración inicial
st.set_page_config(page_title="Ortiz y Asociados", layout="wide")

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
    uploaded_files = st.file_uploader("Cargar ZIP de facturas", type=["zip"])
    
    if uploaded_files:
        lista_datos = []
        ns = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
        }
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
                                supplier_party_node = invoice_tree.find('.//cac:AccountingSupplierParty/cac:Party', namespaces=ns)
                                def get_address_info(party_node, ns):
                                    if party_node is None: return '', None
                                    street_name = party_node.findtext('.//cac:PostalAddress/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:PhysicalLocation/cac:Address/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:RegistrationAddress/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:PostalAddress/cbc:StreetName', namespaces=ns) or party_node.findtext('.//cbc:StreetName', namespaces=ns)
                                    city_name = party_node.findtext('.//cac:PhysicalLocation/cac:Address/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:RegistrationAddress/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:PostalAddress/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:Address/cbc:CityName', namespaces=ns) or party_node.findtext('.//cbc:CityName', namespaces=ns)
                                    return (street_name or '').strip(), city_name
                                supplier_address, supplier_city = get_address_info(supplier_party_node, ns)
                                supplier_phone = supplier_party_node.findtext('.//cac:Contact/cbc:Telephone', namespaces=ns) if supplier_party_node is not None else None
                                supplier_email = supplier_party_node.findtext('.//cac:Contact/cbc:ElectronicMail', namespaces=ns) if supplier_party_node is not None else None
                                total_impuestos_sum = 0.0
                                otros_impuestos_sum = 0.0
                                for tax_total_node in invoice_tree.findall('.//cac:TaxTotal', namespaces=ns):
                                    for tax_subtotal_node in tax_total_node.findall('.//cac:TaxSubtotal', namespaces=ns):
                                        tax_amount = float(tax_subtotal_node.findtext('.//cbc:TaxAmount', namespaces=ns) or 0.0)
                                        total_impuestos_sum += tax_amount
                                        if (tax_subtotal_node.findtext('.//cac:TaxCategory/cbc:TaxScheme/cbc:TaxTypeCode', namespaces=ns) or '').upper() not in ['VAT', 'IVA', '01']: otros_impuestos_sum += tax_amount
                                datos = {
                                    'ID_Factura': invoice_tree.findtext('.//cbc:ID', namespaces=ns),
                                    'Fecha_Emision': invoice_tree.findtext('.//cbc:IssueDate', namespaces=ns),
                                    'Fecha_Vencimiento': due_date,
                                    'Tipo_Pago': tipo_pago,
                                    'NIT_Proveedor': invoice_tree.findtext('.//cac:AccountingSupplierParty//cbc:CompanyID', namespaces=ns),
                                    'Razon_Social_Proveedor': invoice_tree.findtext('.//cac:AccountingSupplierParty//cac:PartyName/cbc:Name', namespaces=ns) or invoice_tree.findtext('.//cac:AccountingSupplierParty//cac:PartyLegalEntity/cbc:RegistrationName', namespaces=ns),
                                    'Direccion_Proveedor': supplier_address,
                                    'Telefono_Proveedor': supplier_phone,
                                    'Correo_Proveedor': supplier_email,
                                    'Ciudad_Proveedor': supplier_city,
                                    'NIT_Adquirente': nit_adquirente,
                                    'Razon_Social_Adquirente': invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyName/cbc:Name', namespaces=ns),
                                    'Moneda': invoice_tree.findtext('.//cbc:DocumentCurrencyCode', namespaces=ns),
                                    'Total_Base_Impuestos': float(invoice_tree.findtext('.//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount', namespaces=ns) or 0),
                                    'Total_Impuestos': total_impuestos_sum,
                                    'Otros_Impuestos': otros_impuestos_sum,
                                    'Total_Factura': float(invoice_tree.findtext('.//cbc:PayableAmount', namespaces=ns) or 0)
                                }
                                lista_datos.append(datos)
                                base_datos.guardar_tercero(datos)
                        except Exception as e:
                            print(f"Error procesando {file}: {e}")
            if os.path.exists(extracted_path): shutil.rmtree(extracted_path)
            os.remove(zip_name)
        df = pd.DataFrame(lista_datos)
        st.write("Libro de Compras generado:")
        st.dataframe(df)

elif opcion == "Editar Tercero":
    st.title("Base de Datos: Terceros")
    try:
        conn = sqlite3.connect("contabilidad.db")
        df_terceros = pd.read_sql_query("SELECT * FROM Terceros", conn)
        conn.close()
        st.dataframe(df_terceros, use_container_width=True)
    except:
        st.error("No se encontraron registros.")

elif opcion == "Crear Comprobante":
    st.title("Crear Comprobante")
    st.write("Sección en desarrollo.")

st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)
