import streamlit as st
import sqlite3
import ollama
import os
import xml.etree.ElementTree as ET

# --- CONFIG ---
DB_PATH = "patient_data.db"
MODEL_NAME = "mistral-nemo" 

# --- SAFE PARSER FUNCTION ---
def clean_medical_record(xml_string):
    """
    Safely strips C-CDA XML tags to extract only human-readable text.
    Includes type-checking to prevent 'List' errors.
    """
    if not isinstance(xml_string, str):
        return f"Error: Expected string data but got {type(xml_string)}. Reload database."

    try:
        # Parse XML (Encode to bytes to safely handle '<?xml...?>' headers)
        root = ET.fromstring(xml_string.encode('utf-8'))
        
        # Strip Namespaces (Removes the {urn:hl7...} prefixes)
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        
        output_text = []
        
        # Extract Section Titles and Text
        for section in root.findall(".//section"):
            title = section.find("title")
            text_node = section.find("text")
            
            if title is not None and title.text:
                section_title = title.text.upper().strip()
                
                # Extract text content recursively
                content = "No narrative text."
                if text_node is not None:
                    # .itertext() grabs all text, even inside tables/lists
                    raw_text = "".join(text_node.itertext())
                    content = " ".join(raw_text.split()) # Remove extra whitespace
                
                output_text.append(f"### {section_title}\n{content}\n")
                    
        return "\n".join(output_text) if output_text else "No structured clinical sections found."

    except Exception as e:
        return f"PARSING ERROR: {str(e)}\n(Returning raw XML might help debug)."

# --- PAGE SETUP ---
st.set_page_config(page_title="OpenClinical AI", page_icon="🏥", layout="wide")
st.title("🏥 OpenClinical AI: SQL-Grounded Analyst")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Patient Search") # Renamed from "Selector" to "Search"
    
    if not os.path.exists(DB_PATH):
        st.error(f"Database missing: {DB_PATH}")
        st.stop()
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, dob, gender, patient_id FROM patients ORDER BY full_name")
    patients = cursor.fetchall()
    conn.close()

    if not patients:
        st.warning("Database empty.")
        st.stop()

    # Create the search list
    # I added the Patient ID (p[4]) to the label so they can search by Name OR ID
    patient_map = {f"{p[1]} (ID: {p[4]}) - DOB: {p[2]}": p[0] for p in patients}
    
    # --- THE SEARCH BAR UPGRADE ---
    selected_label = st.selectbox(
        "Type Name or ID to search:", 
        options=list(patient_map.keys()),
        index=None,                 # <--- Defaults to Empty
        placeholder="Start typing..." # <--- Helper text
    )

    # If nothing is selected yet, stop here (shows a clean homepage)
    if selected_label is None:
        st.info("👈 Please search for a patient in the sidebar to begin.")
        st.stop()

    # Get the ID
    patient_db_id = patient_map[selected_label]

    # LOAD DATA
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, xml_content, dob, patient_id FROM patients WHERE id = ?", (patient_db_id,))
    record = cursor.fetchone()
    conn.close()

    if record:
        patient_name, raw_xml_data, dob, mrn = record
        
        # --- EXECUTE SAFE PARSER ---
        clean_text_data = clean_medical_record(raw_xml_data)
        
        st.divider()
        st.caption("✅ **Data Status**")
        with st.expander("View Extracted Clinical Text"):
            st.text(clean_text_data)
    else:
        st.error("Load failed.")
        st.stop()

# --- MAIN PAGE ---
st.info(f"**Patient:** {patient_name} | **DOB:** {dob} | **MRN:** {mrn}")

# --- CHAT INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Reset chat if patient changes
if "last_patient" not in st.session_state or st.session_state.last_patient != patient_db_id:
    st.session_state.messages = []
    st.session_state.last_patient = patient_db_id

# Display History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle Input
if prompt := st.chat_input(f"Ask about {patient_name}..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("Analyzing clinical data..."):
            # SYSTEM PROMPT (Uses the CLEANED text)
            final_prompt = (
                f"You are a clinical assistant. Use the summary below to answer the user.\n"
                f"If the answer is not in the text, say 'Not found'.\n"
                f"=== CLINICAL SUMMARY ===\n"
                f"{clean_text_data}\n"
                f"=== END SUMMARY ===\n\n"
                f"USER QUESTION: {prompt}"
            )

            try:
                stream = ollama.chat(
                    model=MODEL_NAME,
                    messages=[{'role': 'user', 'content': final_prompt}],
                    stream=True,
                    options={"num_ctx": 32768, "temperature": 0.0}
                )
                
                for chunk in stream:
                    if chunk['message']['content']:
                        full_response += chunk['message']['content']
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"Ollama Error: {e}")