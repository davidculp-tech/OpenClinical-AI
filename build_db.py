import sqlite3
import os
import glob
import xml.etree.ElementTree as ET

# --- CONFIGURATION ---
# UPDATE THIS PATH to your C-CDA XML folder
DOCS_FOLDER = r"C:\Users\Commander\Documents\AI\synthea_sample_data_ccda_latest"
DB_PATH = "patient_data.db"

# Namespaces are annoying in XML, this helper handles them
NAMESPACES = {'v3': 'urn:hl7-org:v3'}

def init_db():
    """Creates the SQLite database file and table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            full_name TEXT,
            dob TEXT,
            gender TEXT,
            filename TEXT,
            xml_content TEXT
        )
    ''')
    conn.commit()
    return conn

def extract_metadata(root):
    """Digs into the C-CDA XML to find the patient's identity."""
    try:
        # Navigate to patientRole
        patient_role = root.find(".//v3:recordTarget/v3:patientRole", NAMESPACES)
        
        # 1. Patient ID (The 'extension' attribute often holds the MRN)
        id_node = patient_role.find("v3:id", NAMESPACES)
        pat_id = id_node.attrib.get('extension', 'Unknown') if id_node is not None else "Unknown"

        # 2. Name
        patient = patient_role.find("v3:patient", NAMESPACES)
        name_node = patient.find("v3:name", NAMESPACES)
        
        # Combine Given + Family name
        givens = [g.text for g in name_node.findall("v3:given", NAMESPACES) if g.text]
        family = name_node.find("v3:family", NAMESPACES).text or ""
        full_name = f"{' '.join(givens)} {family}"

        # 3. DOB
        dob_raw = patient.find("v3:birthTime", NAMESPACES).attrib.get('value', '')
        # Simple format YYYYMMDD -> YYYY-MM-DD
        dob = f"{dob_raw[:4]}-{dob_raw[4:6]}-{dob_raw[6:8]}" if len(dob_raw) >= 8 else dob_raw

        # 4. Gender
        gender_node = patient.find("v3:administrativeGenderCode", NAMESPACES)
        gender = gender_node.attrib.get('displayName', 'Unknown') if gender_node is not None else "Unknown"

        return pat_id, full_name, dob, gender

    except AttributeError:
        return "Unknown", "Parse Error", "Unknown", "Unknown"

def main():
    # 1. Setup DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH) # Reset DB for a clean build
        print("Previous database removed. Starting fresh.")
    
    conn = init_db()
    cursor = conn.cursor()

    # 2. Find Files
    xml_files = glob.glob(os.path.join(DOCS_FOLDER, "*.xml"))
    print(f"Found {len(xml_files)} XML files. Processing...")

    # 3. Process Loop
    count = 0
    for file_path in xml_files:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract Metadata
            pat_id, name, dob, gender = extract_metadata(root)
            
            # Read Raw Content
            with open(file_path, "r", encoding="utf-8") as f:
                raw_xml = f.read()

            # Insert into SQL
            cursor.execute('''
                INSERT INTO patients (patient_id, full_name, dob, gender, filename, xml_content)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (pat_id, name, dob, gender, os.path.basename(file_path), raw_xml))
            
            count += 1
            if count % 10 == 0:
                print(f"Processed {count} records...")

        except Exception as e:
            print(f"Failed to process {os.path.basename(file_path)}: {e}")

    conn.commit()
    conn.close()
    print(f"\nSUCCESS: Database built with {count} patients ready for analysis.")

if __name__ == "__main__":
    main()