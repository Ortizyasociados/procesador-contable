import zipfile
import pandas as pd
from lxml import etree
import streamlit as st
import os
import shutil

# 1. Subir archivo(s)
print("Por favor, sube tu archivo(s) .zip:")
uploaded = st.file_uploader("Sube tu archivo ZIP", type=["zip"])

lista_datos = []
ns = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
}

for zip_name in uploaded.keys():
    extracted_path = f"temp_data_{os.path.splitext(zip_name)[0]}"
    os.makedirs(extracted_path, exist_ok=True)

    with zipfile.ZipFile(zip_name, 'r') as zip_ref:
        zip_ref.extractall(extracted_path)

    # Recorrer todos los XML en el ZIP
    for root_dir, dirs, files_list in os.walk(extracted_path):
        for file in files_list:
            if file.endswith(".xml"):
                try:
                    tree = etree.parse(os.path.join(root_dir, file))
                    root = tree.getroot()

                    # Extraer el XML incrustado (CDATA) del contenedor
                    cdata_content_node = root.find('.//cac:ExternalReference/cbc:Description', ns)
                    invoice_tree = None
                    if cdata_content_node is not None and cdata_content_node.text:
                        cdata_content = cdata_content_node.text
                        invoice_tree = etree.fromstring(cdata_content.encode('utf-8'))
                    else:
                        # If no CDATA, try to parse the XML directly as an Invoice
                        # This handles cases where the main XML IS the invoice
                        if root.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice':
                            invoice_tree = root
                        else:
                            print(f"No CDATA content found and not a direct Invoice XML for {file}")
                            continue # Skip this file if no invoice content found

                    if invoice_tree is not None:
                        # Determine payment type
                        payment_means_code = invoice_tree.findtext('.//cac:PaymentMeans/cbc:PaymentMeansCode', namespaces=ns)
                        due_date = invoice_tree.findtext('.//cbc:DueDate', namespaces=ns) or invoice_tree.findtext('.//cac:PaymentTerms/cbc:PaymentDueDate', namespaces=ns)

                        tipo_pago = 'Contado'
                        if payment_means_code == '30' or due_date: # '30' typically means Credit Transfer
                            tipo_pago = 'Crédito'

                        # Extract acquirer's NIT more robustly
                        nit_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyTaxScheme/cbc:CompanyID', namespaces=ns)
                        if not nit_adquirente:
                            nit_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID', namespaces=ns)

                        # --- Extract details for Supplier and Acquirer ---
                        supplier_party_node = invoice_tree.find('.//cac:AccountingSupplierParty/cac:Party', namespaces=ns)
                        acquirer_party_node = invoice_tree.find('.//cac:AccountingCustomerParty/cac:Party', namespaces=ns)

                        # Helper to get address components, handles potential None
                        def get_address_info(party_node, ns):
                            if party_node is None:
                                return '', None # Return empty address and None city if party node is not found

                            street_name = None
                            # Try common paths for street name (more specific first)
                            street_name = party_node.findtext('.//cac:PostalAddress/cac:AddressLine/cbc:Line', namespaces=ns)
                            if not street_name:
                                street_name = party_node.findtext('.//cac:PhysicalLocation/cac:Address/cac:AddressLine/cbc:Line', namespaces=ns)
                            if not street_name:
                                street_name = party_node.findtext('.//cac:RegistrationAddress/cac:AddressLine/cbc:Line', namespaces=ns)
                            if not street_name:
                                street_name = party_node.findtext('.//cac:PostalAddress/cbc:StreetName', namespaces=ns)
                            if not street_name:
                                street_name = party_node.findtext('.//cbc:StreetName', namespaces=ns)

                            additional_street_name = None
                            additional_street_name = party_node.findtext('.//cac:PostalAddress/cbc:AdditionalStreetName', namespaces=ns)
                            if not additional_street_name:
                                additional_street_name = party_node.findtext('.//cbc:AdditionalStreetName', namespaces=ns)

                            city_name = None
                            # Try common paths for city name
                            city_name = party_node.findtext('.//cac:PhysicalLocation/cac:Address/cbc:CityName', namespaces=ns)
                            if not city_name:
                                city_name = party_node.findtext('.//cac:RegistrationAddress/cbc:CityName', namespaces=ns)
                            if not city_name:
                                city_name = party_node.findtext('.//cac:PostalAddress/cbc:CityName', namespaces=ns)
                            if not city_name:
                                city_name = party_node.findtext('.//cac:Address/cbc:CityName', namespaces=ns)
                            if not city_name:
                                city_name = party_node.findtext('.//cbc:CityName', namespaces=ns)

                            full_address = street_name if street_name else ''
                            if additional_street_name:
                                full_address = f"{full_address}, {additional_street_name}"

                            return full_address.strip(), city_name

                        supplier_address, supplier_city = get_address_info(supplier_party_node, ns)

                        # Supplier Phone and Email
                        supplier_phone = supplier_party_node.findtext('.//cac:Contact/cbc:Telephone', namespaces=ns) if supplier_party_node is not None else None
                        supplier_email = supplier_party_node.findtext('.//cac:Contact/cbc:ElectronicMail', namespaces=ns) if supplier_party_node is not None else None

                        # --- Calculate Total_Impuestos and Otros_Impuestos ---
                        total_impuestos_sum = 0.0
                        otros_impuestos_sum = 0.0

                        for tax_total_node in invoice_tree.findall('.//cac:TaxTotal', namespaces=ns):
                            for tax_subtotal_node in tax_total_node.findall('.//cac:TaxSubtotal', namespaces=ns):
                                tax_amount_str = tax_subtotal_node.findtext('.//cbc:TaxAmount', namespaces=ns)
                                tax_amount = float(tax_amount_str) if tax_amount_str else 0.0
                                total_impuestos_sum += tax_amount

                                tax_type_code = tax_subtotal_node.findtext('.//cac:TaxCategory/cbc:TaxScheme/cbc:TaxTypeCode', namespaces=ns)
                                # Assuming 'VAT' and 'IVA' are the main types for the standard tax
                                if tax_type_code and tax_type_code.upper() not in ['VAT', 'IVA', '01']: # '01' is a common code for IVA/VAT
                                    otros_impuestos_sum += tax_amount

                        # Supplier Name extraction with fallback
                        razon_social_proveedor = invoice_tree.findtext('.//cac:AccountingSupplierParty//cac:PartyName/cbc:Name', namespaces=ns)
                        if not razon_social_proveedor:
                            razon_social_proveedor = invoice_tree.findtext('.//cac:AccountingSupplierParty//cac:PartyLegalEntity/cbc:RegistrationName', namespaces=ns)

                        # Acquirer Name
                        razon_social_adquirente = invoice_tree.findtext('.//cac:AccountingCustomerParty//cac:PartyName/cbc:Name', namespaces=ns)

                        # Extract data
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
                            'Total_Impuestos': total_impuestos_sum, # Use the calculated sum
                            'Otros_Impuestos': otros_impuestos_sum, # New column
                            'Total_Factura': float(invoice_tree.findtext('.//cbc:PayableAmount', namespaces=ns) or 0)
                        }
                        lista_datos.append(datos)
                except Exception as e:
                    print(f"Error procesando {file}: {e}")

    # Clean up extracted files for the current zip
    if os.path.exists(extracted_path):
        shutil.rmtree(extracted_path)

# 3. Crear el libro de compras
df = pd.DataFrame(lista_datos)

# Define the desired column order (updated with new columns)
df_columns_order = [
    'ID_Factura',
    'Fecha_Emision',
    'Fecha_Vencimiento',
    'Tipo_Pago',
    'NIT_Proveedor',
    'Razon_Social_Proveedor',
    'Direccion_Proveedor',
    'Telefono_Proveedor',
    'Correo_Proveedor',
    'Ciudad_Proveedor',
    'NIT_Adquirente',
    'Razon_Social_Adquirente',
    'Moneda',
    'Total_Base_Impuestos',
    'Total_Impuestos',
    'Otros_Impuestos',
    'Total_Factura'
]
# Ensure all columns exist before reindexing, fill missing with None or empty string
for col in df_columns_order:
    if col not in df.columns:
        df[col] = None

df = df[df_columns_order]

# Convert date columns to datetime objects and sort
df['Fecha_Emision'] = pd.to_datetime(df['Fecha_Emision'], errors='coerce')
df['Fecha_Vencimiento'] = pd.to_datetime(df['Fecha_Vencimiento'], errors='coerce')
df = df.sort_values(by='Fecha_Emision').reset_index(drop=True)

# Add 'No_Item' column as the first column AFTER sorting
df.insert(0, 'No_Item', range(1, 1 + len(df)))

# Calculate 'Base_Exenta' based on logic
df['Base_Exenta'] = df.apply(lambda row: row['Total_Base_Impuestos'] if (pd.isna(row['Total_Base_Impuestos']) or row['Total_Base_Impuestos'] == 0) else 0, axis=1)

# Reorder columns to include Base_Exenta in a logical place (e.g., after Total_Base_Impuestos)
# Create a new column order including 'Base_Exenta'
df_columns_order_final = [
    'No_Item',
    'ID_Factura',
    'Fecha_Emision',
    'Fecha_Vencimiento',
    'Tipo_Pago',
    'NIT_Proveedor',
    'Razon_Social_Proveedor',
    'Direccion_Proveedor',
    'Telefono_Proveedor',
    'Correo_Proveedor',
    'Ciudad_Proveedor',
    'NIT_Adquirente',
    'Razon_Social_Adquirente',
    'Moneda',
    'Total_Base_Impuestos',
    'Base_Exenta', # New position for Base_Exenta
    'Total_Impuestos',
    'Otros_Impuestos',
    'Total_Factura'
]

df = df[df_columns_order_final]

print("\nLibro de Compras generado y ordenado cronológicamente:")
display(df)

# Add a total row at the end
total_row = pd.DataFrame([{
    'No_Item': None,
    'ID_Factura': 'TOTAL',
    'Fecha_Emision': None,
    'Fecha_Vencimiento': None,
    'Tipo_Pago': None,
    'NIT_Proveedor': None,
    'Razon_Social_Proveedor': None,
    'Direccion_Proveedor': None,
    'Telefono_Proveedor': None,
    'Correo_Proveedor': None,
    'Ciudad_Proveedor': None,
    'NIT_Adquirente': None,
    'Razon_Social_Adquirente': None,
    'Moneda': None,
    'Total_Base_Impuestos': df['Total_Base_Impuestos'].sum(),
    'Base_Exenta': df['Base_Exenta'].sum(), # Sum for Base_Exenta
    'Total_Impuestos': df['Total_Impuestos'].sum(),
    'Otros_Impuestos': df['Otros_Impuestos'].sum(), # Sum for Otros_Impuestos
    'Total_Factura': df['Total_Factura'].sum()
}])

# Concatenate the total row
df_final = pd.concat([df, total_row], ignore_index=True)

print("\nLibro de Compras con totales:")
display(df_final)

# 4. Descargar a Excel
df_final.to_excel("Libro_Compras_Final.xlsx", index=False)
files.download("Libro_Compras_Final.xlsx")

# Generate a Third-Party Database (updated with new columns)
third_parties_df = pd.DataFrame()

# Extract unique suppliers
sup = df[['NIT_Proveedor', 'Razon_Social_Proveedor', 'Direccion_Proveedor', 'Telefono_Proveedor', 'Correo_Proveedor', 'Ciudad_Proveedor']].copy() # Use .copy() to avoid SettingWithCopyWarning
sup = sup.drop_duplicates().rename(columns={
    'NIT_Proveedor': 'NIT_Tercero',
    'Razon_Social_Proveedor': 'Razon_Social_Tercero',
    'Direccion_Proveedor': 'Direccion_Tercero',
    'Telefono_Proveedor': 'Telefono_Tercero',
    'Correo_Proveedor': 'Correo_Tercero',
    'Ciudad_Proveedor': 'Ciudad_Tercero'
})
sup['Tipo_Tercero'] = 'Proveedor'

# Extract unique acquirers (only NIT and Razon_Social)
acu = df[['NIT_Adquirente', 'Razon_Social_Adquirente']].copy()
acu = acu.drop_duplicates().rename(columns={
    'NIT_Adquirente': 'NIT_Tercero',
    'Razon_Social_Adquirente': 'Razon_Social_Tercero'
})
acu['Tipo_Tercero'] = 'Adquirente'

# Combine and drop duplicates (in case a third-party is both supplier and acquirer)
third_parties_df = pd.concat([sup, acu], ignore_index=True).drop_duplicates(subset=['NIT_Tercero']).reset_index(drop=True)

# Define all third party columns with reduced acquirer details
all_third_party_cols = [
    'NIT_Tercero',
    'Razon_Social_Tercero',
    'Direccion_Tercero',
    'Telefono_Tercero',
    'Correo_Tercero',
    'Ciudad_Tercero',
    'Tipo_Tercero'
]

# Ensure all columns are present and reorder
for col in all_third_party_cols:
    if col not in third_parties_df.columns:
        third_parties_df[col] = None

third_parties_df = third_parties_df[all_third_party_cols]

print("\nBase de Datos de Terceros (Proveedores y Adquirentes):")
display(third_parties_df)

# Download Third-Party Database to Excel
third_parties_df.to_excel("Base_Datos_Terceros.xlsx", index=False)
files.download("Base_Datos_Terceros.xlsx")
