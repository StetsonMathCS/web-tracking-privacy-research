from pathlib import Path
import pandas as pd

#Locate the project directory
project_dir = Path(__file__).resolve().parent.parent

#Locate the Excel file dateset
excel_path = project_dir / "data" / "Website_Testing.xlsx"

#Read the Excel file
websites = pd.read_excel(
    excel_path,
    sheet_name = "Website Testing"
)

#preview the dateset
print(websites.head())

#count the websites 
print("Total websites to test:", len(websites))
