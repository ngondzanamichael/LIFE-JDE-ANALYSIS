import streamlit as st
import pandas as pd
import re
from io import BytesIO

# Set page config
st.set_page_config(
    page_title="Data Cleaning Tool",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main title
st.title("📊 LIFE/JDE Data Cleaning Tool")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Files")
    lor518_file = st.file_uploader("Upload LOR518 File", type=['xlsx'])
    lor850_file = st.file_uploader("Upload LOR850 File", type=['xlsx'])
    jde_file = st.file_uploader("Upload JDE Data File", type=['xlsx'])
    
    st.markdown("---")
    st.markdown("### Options")
    show_raw_data = st.checkbox("Show raw data preview", False)
    auto_process = st.checkbox("Auto-process on upload", True)
    process_btn = st.button("Process Data", disabled=not (lor518_file and lor850_file and jde_file))

# Main content area
if lor518_file and lor850_file and jde_file and (auto_process or process_btn):
    # Load data
    with st.spinner("Loading data..."):
        data_life = pd.read_excel(lor518_file)
        lor850 = pd.read_excel(lor850_file)
        data_jde = pd.read_excel(jde_file)
    
    if show_raw_data:
        st.subheader("Raw Data Preview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**LOR518 Data**")
            st.dataframe(data_life.head())
        with col2:
            st.markdown("**LOR850 Data**")
            st.dataframe(lor850.head())
        with col3:
            st.markdown("**JDE Data**")
            st.dataframe(data_jde.head())

    # Data cleaning process
    st.subheader("Data Processing Results")
    
    with st.expander("Data Cleaning Steps", expanded=False):
        st.markdown("""
        1. Column renaming and standardization
        2. Filtering for specific conditions (prechargement, faulty pickups)
        3. BL number validation
        4. Status verification
        5. Identification of fictitious transporters
        """)

    # Processing tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Prechargement", "BL Jumps", "TMP Transporters", 
        "Fictitious Transporters", "Status 565", "Invalid BLs", 
        "Faulty Pickups"
    ])

    # Process data (your original cleaning steps)
    with st.spinner("Processing data..."):
        # Rename and clean columns in data_life
        new_columns = {}
        for col in data_life.columns:
            new_col = col.strip().lower()
            if 'unnamed: 6' in new_col:
                new_col = 'vendor'
            if 'unnamed: 8' in new_col:
                new_col = 'customer name'
            new_columns[col] = new_col
        data_life = data_life.rename(columns=new_columns)

        # Rename and clean columns in lor850
        new_columns = {}
        for col in lor850.columns:
            new_col = col.strip().lower()
            if 'unnamed: 5' in new_col:
                new_col = 'customer'
            if 'unnamed: 8' in new_col:
                new_col = 'produit'
            new_columns[col] = new_col
        lor850 = lor850.rename(columns=new_columns)

        # Rename and clean columns in data_jde
        new_columns = {}
        for col in data_jde.columns:
            new_col = col.strip().lower()
            new_columns[col] = new_col
        data_jde = data_jde.rename(columns=new_columns)

        # Keep specific columns
        data_life_columns = ['ticket date', 'plant', 'ticket#', 'customer', 'vendor', 'ship to', 'customer name',
               'prod desc', 'delv', 'truck', 'hired', 'shipment', 'load']
        data_life = data_life[data_life_columns]

        data_jde_columns = ['n° expéd.', 'magasin/usine', 't c', 'dernier statut', 'statut suivant', 
                           'date comm.', 'nº comm.', 'description 1']
        data_jde = data_jde[data_jde_columns]

        lor850_keep = ['plant', 'receipt date', 'customer', 'produit', 'qty', 'external ticket/bol', 
                       'carrier id', 'carrier name', 'driver name', 'reference no', 'user']
        lor850 = lor850[lor850_keep]

        # Prechargement analysis
        prechargement = data_life[data_life['vendor'].str.contains('PRECHARGEMENT', na=False)]
        
        # BL jumps analysis
        data_life['ticket date'] = pd.to_datetime(data_life['ticket date'])
        data_life.sort_values('ticket date', inplace=True)
        plant_data = data_life[['plant', 'ticket#', 'delv']].sort_values(by=['ticket#'])
        plant_data['difference'] = plant_data['ticket#'].diff().fillna(0)
        saut_bl = plant_data[plant_data['difference'] != 1]

        # Faulty pickup analysis
        faulty_pickup = data_life[(data_life['hired'] != 'TMP') & (data_life['delv'] == 'N')]
        
        # Status verification
        data_jde_filtered = data_jde[
            data_jde['t c'].isin(['SO', 'ST']) &
            ~data_jde['dernier statut'].isin([980, 984, 989])
        ]
        
        merged_data = data_life.merge(data_jde_filtered[['n° expéd.', 'statut suivant']],
                                   left_on='shipment', right_on='n° expéd.', how='left')
        merged_data_filtered = merged_data[merged_data['statut suivant'] != 999.0]
        staut_suivant_565 = merged_data[merged_data['statut suivant'] == 565.0]
        
        # Fictitious transporters
        trans_tmp = data_life[(data_life['hired'] == 'TMP') & (data_life['delv'] == 'Y')]
        
        trans_fic = lor850[lor850['produit'].str.contains('POUZZOLANE|PETCOKE|GYPSE|CLINKER|CALCAIRE|SABLE', na=False) &
            (lor850['carrier name'] == "Transpoteur Fictif")]
        
        # BL validation
        def validate_bl_number(bl_number):
            if pd.isna(bl_number):
                return False
            parts = str(bl_number).split('-')
            if len(parts) != 2:
                return False
            try:
                number_part = parts[1]
                return bool(re.fullmatch(r'^[347]\d{5}$', number_part))
            except (AttributeError, TypeError):
                return False

        lor850['valid bl'] = lor850['external ticket/bol'].apply(validate_bl_number)
        faux_bl = lor850[(lor850['produit'].str.contains('PETCOKE|GYPSE|CLINKER', na=False)) & (lor850['valid bl'] == False)]

    # Display results in tabs
    with tab1:
        st.markdown("**Prechargement Records**")
        st.dataframe(prechargement)
        st.markdown(f"**Count:** {len(prechargement)} records")

    with tab2:
        st.markdown("**BL Number Jumps**")
        st.dataframe(saut_bl)
        st.markdown(f"**Count:** {len(saut_bl)} jumps detected")
        
    with tab3:
        st.markdown("**TMP Transporters**")
        st.dataframe(trans_tmp)
        st.markdown(f"**Count:** {len(trans_tmp)} records")

    with tab4:
        st.markdown("**Fictitious Transporters**")
        st.dataframe(trans_fic)
        st.markdown(f"**Count:** {len(trans_fic)} records")

    with tab5:
        st.markdown("**Status 565 Records**")
        st.dataframe(staut_suivant_565)
        st.markdown(f"**Count:** {len(staut_suivant_565)} records")

    with tab6:
        st.markdown("**Invalid BL Numbers**")
        st.dataframe(faux_bl)
        st.markdown(f"**Count:** {len(faux_bl)} invalid BLs")

    with tab7:
        st.markdown("**Faulty Pickups**")
        st.dataframe(faulty_pickup)
        st.markdown(f"**Count:** {len(faulty_pickup)} records")

    # Download button
    st.markdown("---")
    st.subheader("Export Results")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        prechargement.to_excel(writer, sheet_name='prechargement', index=False)
        saut_bl.to_excel(writer, sheet_name='saut_bl', index=False)
        trans_tmp.to_excel(writer, sheet_name='trans_tmp', index=False)
        trans_fic.to_excel(writer, sheet_name='trans_fic', index=False)
        merged_data.to_excel(writer, sheet_name='statut_suivant', index=False)
        faux_bl.to_excel(writer, sheet_name='faux_bl', index=False)
        faulty_pickup.to_excel(writer, sheet_name='faulty_pickup', index=False)
