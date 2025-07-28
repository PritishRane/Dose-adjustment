import streamlit as st
import pandas as pd
import unicodedata
import re

# ------------------ Load and Clean Dose Table ------------------
@st.cache_data
def load_and_clean_data():
    df = pd.read_csv("Crcldose.csv", encoding='ISO-8859-1')
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Define all replacements
    replacements = {
        '–': '-',    # en dash
        '—': '-',    # em dash
        '−': '-',    # minus
        '': '-',    # corrupted dash
        '≥': '>=',
        '≤': '<=',
        '?': '>=',
        '�': ''
    }

    for col in df.columns:
        if df[col].dtype == 'object':
            for bad, good in replacements.items():
                df[col] = df[col].str.replace(bad, good, regex=False)
            df[col] = df[col].str.strip()

    return df

# ------------------ Helper Functions ------------------
def calculate_crcl(age, weight, sex, scr):
    factor = 0.85 if sex == 'Female' else 1.0
    return round(((140 - age) * weight * factor) / (72 * scr), 2)

def crcl_in_range(crcl, range_str):
    range_str = range_str.strip().lower()
    try:
        if range_str == "any":
            return True
        elif '-' in range_str:
            low, high = map(float, range_str.split('-'))
            return low <= crcl <= high
        elif '>=' in range_str:
            return crcl >= float(range_str.replace('>=', '').strip())
        elif '>' in range_str:
            return crcl > float(range_str.replace('>', '').strip())
        elif '<=' in range_str:
            return crcl <= float(range_str.replace('<=', '').strip())
        elif '<' in range_str:
            return crcl < float(range_str.replace('<', '').strip())
    except:
        return False
    return False

def convert_mgkg_to_mg(dose_str, weight):
    match = re.search(r'(\d+)\s*mg/kg', dose_str)
    if match:
        dose = int(match.group(1)) * weight
        return re.sub(r'\d+\s*mg/kg', f'{dose} mg', dose_str)
    return dose_str

def get_dose(drug, crcl, weight, df):
    matches = df[df['Drug'].str.lower() == drug.lower()]
    if matches.empty:
        return f"⚠️ Drug '{drug}' not found in database."

    for _, row in matches.iterrows():
        if crcl_in_range(crcl, row['Range']):
            dose = convert_mgkg_to_mg(row['Recommended Dose'], weight)
            return f"✅ Dose for **{drug.title()}** (CrCl: `{crcl} mL/min`):\n\n**{dose}**"
    
    return f"⚠️ No matching CrCl range found for **{drug.title()}** (CrCl: `{crcl}`)"

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="CrCl Dose Calculator", layout="centered")
st.title("🧪 Drug Dose Adjustment Based on Creatinine Clearance")

# ✅ Load data here
df = load_and_clean_data()

# Input Fields
with st.form("dose_form"):
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age (years)", min_value=0, value=65)
        weight = st.number_input("Weight (kg)", min_value=10.0, value=70.0)
    with col2:
        sex = st.selectbox("Sex", ["Male", "Female"])
        scr = st.number_input("Serum Creatinine (mg/dL)", min_value=0.1, value=1.0)

    drug_list = sorted(df['Drug'].dropna().unique())
    drug = st.selectbox("Select Drug", drug_list)

    submitted = st.form_submit_button("Calculate Dose")

# Output
if submitted:
    crcl = calculate_crcl(age, weight, sex, scr)
    result = get_dose(drug, crcl, weight, df)

    st.markdown(f"### 🧮 Estimated CrCl: `{crcl} mL/min`")
    st.success(result)
