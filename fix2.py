import pandas as pd
from src.gsheets import get_sheet

sheet = get_sheet('Casas')
data = sheet.get_all_records()
for i, row in enumerate(data):
    if 'Lavalleja 2217' in str(row.get('dirección')):
        print(f'Actualizando Lavalleja 2217 (Fila {i+2})')
        sheet.update_cell(i+2, 25, 4.0)
        sheet.update_cell(i+2, 26, 'Muchos comercios cerca')
        sheet.update_cell(i+2, 27, 'Poco transporte público')
        sheet.update_cell(i+2, 28, '{"Comercios": 4, "Transporte": 4}')
