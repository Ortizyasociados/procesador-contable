import zipfile
import pandas as pd
from lxml import etree
import streamlit as st
import os
import shutil

# --- CONFIGURACIÓN E INTERFAZ ---
st.title("Procesador de Facturas")
uploaded_files = st.file_uploader("Sube tus archivos ZIP", type=["zip"], accept_multiple_files=True)

if uploaded_files:
    lista_datos = []
    ns = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    }

    # Procesar cada archivo subido
    for uploaded_file in uploaded_files:
        zip_name = uploaded_file.name
        
        # Guardar en disco temporalmente
        with open(zip_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        extracted_path = f"temp_data_{os.path.splitext(zip_name)[0]}"
        os.makedirs(extracted_path, exist_ok=True)

        with zipfile.ZipFile(zip_name, 'r') as zip_ref:
            zip_ref.extractall(extracted_path)

        # Tu lógica de procesamiento intacta
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
                        elif root.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice':
                            invoice_tree = root
                        
                        if invoice_tree is not None:
                            payment_means_code = invoice_tree.findtext('.//cac:PaymentMeans/cbc:PaymentMeansCode', namespaces=ns)
                            due_date = invoice_tree.findtext('.//cbc:DueDate', namespaces=ns) or invoice_tree.findtext('.//cac:PaymentTerms/cbc:PaymentDueDate', namespaces=ns)
                            tipo_pago = 'Crédito' if (payment_means_code == '30' or due_date) else 'Contado'
                            
                            nit_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyTaxScheme/cbc:CompanyID', namespaces=ns) or invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID', namespaces=ns)
                            
                            supplier_party_node = invoice_tree.find('.//cac:AccountingSupplierParty/cac:Party', namespaces=ns)
                            
                            def get_address_info(party_node, ns):
                                if party_node is None: return '', None
                                street = party_node.findtext('.//cac:PostalAddress/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:PhysicalLocation/cac:Address/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:RegistrationAddress/cac:AddressLine/cbc:Line', namespaces=ns) or party_node.findtext('.//cac:PostalAddress/cbc:StreetName', namespaces=ns) or party_node.findtext('.//cbc:StreetName', namespaces=ns)
                                add_street = party_node.findtext('.//cac:PostalAddress/cbc:AdditionalStreetName', namespaces=ns) or party_node.findtext('.//cbc:AdditionalStreetName', namespaces=ns)
                                city = party_node.findtext('.//cac:PhysicalLocation/cac:Address/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:RegistrationAddress/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:PostalAddress/cbc:CityName', namespaces=ns) or party_node.findtext('.//cac:Address/cbc:CityName', namespaces=ns) or party_node.findtext('.//cbc:CityName', namespaces=ns)
                                full_address = f"{street}, {add_street}".strip(', ') if street else ''
                                return full_address, city

                            supplier_address, supplier_city = get_address_info(supplier_party_node, ns)
                            supplier_phone = supplier_party_node.findtext('.//cac:Contact/cbc:Telephone', namespaces=ns) if supplier_party_node is not None else None
                            supplier_email = supplier_party_node.findtext('.//cac:Contact/cbc:ElectronicMail', namespaces=ns) if supplier_party_node is not None else None
                            
                            total_impuestos_sum = 0.0
                            otros_impuestos_sum = 0.0
                            for tax_subtotal in invoice_tree.findall('.//cac:TaxSubtotal', namespaces=ns):
                                amt = float(tax_subtotal.findtext('.//cbc:TaxAmount', namespaces=ns) or 0)
                                total_impuestos_sum += amt
                                if (tax_subtotal.findtext('.//cac:TaxCategory/cbc:TaxScheme/cbc:TaxTypeCode', namespaces=ns) or '').upper() not in ['VAT', 'IVA', '01']:
                                    otros_impuestos_sum += amt
                            
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
                    except Exception as e:
                        st.error(f"Error en {file}: {e}")

        # Limpiar archivos temporales
        shutil.rmtree(extracted_path)
        os.remove(zip_name)

    # Generación del DataFrame
    df = pd.DataFrame(lista_datos)
    # [Aquí se mantiene tu lógica de ordenamiento y totales]
    df['Fecha_Emision'] = pd.to_datetime(df['Fecha_Emision'], errors='coerce')
    df = df.sort_values(by='Fecha_Emision').reset_index(drop=True)
    df.insert(0, 'No_Item', range(1, 1 + len(df)))
    df['Base_Exenta'] = df.apply(lambda row: row['Total_Base_Impuestos'] if (pd.isna(row['Total_Base_Impuestos']) or row['Total_Base_Impuestos'] == 0) else 0, axis=1)

    st.success("Procesamiento completado")
    st.dataframe(df)

    # Botones de descarga
    output_file = "Libro_Compras_Final.xlsx"
    df.to_excel(output_file, index=False)
    with open(output_file, "rb") as f:
        st.download_button("Descargar Libro de Compras", f, file_name=output_file)
