"""
Oracle to SQL Server Migration - Streamlit Web Application

Production-ready web interface for database migration with:
- Upfront credential collection
- Complete object discovery and selection
- Conflict resolution options
- Real-time progress tracking
- Industry best practices

Run with: streamlit run app.py
"""

import streamlit as st
import logging
import json
from pathlib import Path
from datetime import datetime
import time

# Configure logging with UTF-8 encoding for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/migration_webapp.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Oracle to SQL Server Migration",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'oracle_creds' not in st.session_state:
    st.session_state.oracle_creds = {}
if 'sqlserver_creds' not in st.session_state:
    st.session_state.sqlserver_creds = {}
if 'discovery_result' not in st.session_state:
    st.session_state.discovery_result = None
if 'selection' not in st.session_state:
    st.session_state.selection = {}
if 'migration_options' not in st.session_state:
    st.session_state.migration_options = {}
if 'migration_results' not in st.session_state:
    st.session_state.migration_results = None

# Simple, clean CSS styling
st.markdown("""
<style>
    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render clean minimal application header"""
    st.title("Oracle → SQL Server Migration")
    st.caption("Professional Database Migration Tool")

    # Simple progress indicator
    progress_steps = ["Credentials", "Discovery", "Selection", "Options", "Migration", "Results"]

    cols = st.columns(len(progress_steps))
    for idx, (col, name) in enumerate(zip(cols, progress_steps), 1):
        with col:
            if idx < st.session_state.step:
                st.success(f"✓ {name}")
            elif idx == st.session_state.step:
                st.info(f"➤ {name}")
            else:
                st.write(f"{idx}. {name}")

    st.divider()


def step1_credentials():
    """Step 1: Collect database credentials"""
    st.header("Step 1: Database Credentials")
    st.info("Please provide connection details for both Oracle and SQL Server databases.")

    # Oracle Credentials
    st.subheader("🔵 Oracle Database")
    col1, col2 = st.columns(2)

    with col1:
        oracle_host = st.text_input("Host", value="localhost", key="oracle_host")
        oracle_port = st.number_input("Port", value=1521, min_value=1, max_value=65535, key="oracle_port")
        oracle_service = st.text_input("Service Name", value="XEPDB1", key="oracle_service")

    with col2:
        oracle_username = st.text_input("Username", key="oracle_username")
        oracle_password = st.text_input("Password", type="password", key="oracle_password")

    # SQL Server Credentials
    st.subheader("🟢 SQL Server Database")
    col3, col4 = st.columns(2)

    with col3:
        sqlserver_host = st.text_input("Server", value="localhost", key="sqlserver_host")
        sqlserver_database = st.text_input("Database", value="MigrationTarget", key="sqlserver_database")

    with col4:
        sqlserver_username = st.text_input("Username", value="sa", key="sqlserver_username")
        sqlserver_password = st.text_input("Password", type="password", key="sqlserver_password")

    # Navigation buttons
    st.markdown("---")
    
    # Test Connection button (always visible)
    col_test, col_next = st.columns([1, 1])
    
    with col_test:
        if st.button("🔌 Test Connection", type="secondary"):
            if not all([oracle_username, oracle_password, sqlserver_username, sqlserver_password]):
                st.error("❌ Please fill in all required fields")
            else:
                with st.spinner("Testing connections..."):
                    is_valid, message = test_connections(
                        oracle_host, oracle_port, oracle_service, oracle_username, oracle_password,
                        sqlserver_host, sqlserver_database, sqlserver_username, sqlserver_password
                    )
                    
                    if is_valid:
                        st.success(f"✅ {message}")
                        # Save credentials and mark as validated
                        st.session_state.oracle_creds = {
                            "host": oracle_host,
                            "port": oracle_port,
                            "service_name": oracle_service,
                            "username": oracle_username,
                            "password": oracle_password
                        }
                        st.session_state.sqlserver_creds = {
                            "server": sqlserver_host,
                            "database": sqlserver_database,
                            "username": sqlserver_username,
                            "password": sqlserver_password
                        }
                        st.session_state.credentials_validated = True
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                        st.session_state.credentials_validated = False

    
    # Next button (only visible after successful validation)
    with col_next:
        # Check if credentials have been validated
        if st.session_state.get('credentials_validated', False):
            if st.button("➡️ Next: Discovery", type="primary"):
                st.session_state.step = 2
                st.rerun()
        else:
            # Show disabled-looking button with message
            st.button("➡️ Next: Discovery", type="primary", disabled=True)
            st.caption("⚠️ Please test connection first")


def step2_discovery():
    """Step 2: Discover all database objects"""
    st.header("Step 2: Database Discovery")

    if st.session_state.discovery_result is None:
        st.info("Discovering all database objects from Oracle. This may take a few moments...")

        if st.button("🔍 Start Discovery", type="primary"):
            with st.spinner("Discovering database objects..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    from database.oracle_connector import OracleConnector
                    from utils.comprehensive_discovery import ComprehensiveDiscovery

                    # Connect
                    status_text.text("Connecting to Oracle...")
                    progress_bar.progress(10)
                    oracle_conn = OracleConnector(st.session_state.oracle_creds)

                    if not oracle_conn.connect():
                        st.error("❌ Failed to connect to Oracle database")
                        return

                    # Discover
                    status_text.text("Discovering objects...")
                    progress_bar.progress(30)

                    discovery = ComprehensiveDiscovery(oracle_conn)
                    result = discovery.discover_all()

                    progress_bar.progress(90)

                    # Save result
                    st.session_state.discovery_result = discovery.to_json(result)

                    # Save to file
                    output_dir = Path("output")
                    output_dir.mkdir(exist_ok=True)
                    with open(output_dir / "discovery_result.json", 'w') as f:
                        json.dump(st.session_state.discovery_result, f, indent=2)

                    oracle_conn.disconnect()

                    progress_bar.progress(100)
                    status_text.text("Discovery complete!")
                    time.sleep(0.5)
                    st.success("✅ Discovery completed successfully!")
                    st.rerun()

                except Exception as e:
                    logger.error(f"Discovery failed: {e}", exc_info=True)
                    st.error(f"❌ Discovery failed: {str(e)}")

    else:
        # Display discovery results
        result = st.session_state.discovery_result

        st.success("✅ Discovery completed successfully!")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Objects", result['summary']['total_objects'])
        with col2:
            st.metric("Tables", result['counts']['tables'])
        with col3:
            st.metric("Packages", result['counts']['packages'])
        with col4:
            st.metric("Procedures", result['counts']['procedures'])

        # Detailed counts
        st.subheader("📊 Object Breakdown")
        col5, col6, col7, col8 = st.columns(4)

        with col5:
            st.metric("Functions", result['counts']['functions'])
        with col6:
            st.metric("Triggers", result['counts']['triggers'])
        with col7:
            st.metric("Views", result['counts']['views'])
        with col8:
            st.metric("Sequences", result['counts']['sequences'])

        # Discovery time
        st.info(f"⏱️ Discovery completed in {result['summary']['discovery_time']}")

        # Navigation
        col_back, col_next = st.columns([1, 1])

        with col_back:
            if st.button("⬅️ Back to Credentials"):
                st.session_state.step = 1
                st.rerun()

        with col_next:
            if st.button("➡️ Next: Select Objects", type="primary"):
                st.session_state.step = 3
                st.rerun()


def step3_selection():
    """Step 3: Select objects to migrate"""
    st.header("Step 3: Select Objects to Migrate")
    st.info("Select all objects you want to migrate. You can review and modify your selections before proceeding.")

    result = st.session_state.discovery_result

    # Tables Selection
    st.subheader("📋 Tables")
    tables = result['objects']['tables']

    if tables:
        col_select_all, col_select_none = st.columns([1, 1])

        with col_select_all:
            if st.button("✓ Select All Tables"):
                for table in tables:
                    st.session_state[f"table_{table['name']}"] = True
                st.rerun()

        with col_select_none:
            if st.button("✗ Deselect All Tables"):
                for table in tables:
                    st.session_state[f"table_{table['name']}"] = False
                st.rerun()

        # Display tables with checkboxes
        st.markdown("---")

        for table in tables:
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                # Initialize default if not present
                if f"table_{table['name']}" not in st.session_state:
                    st.session_state[f"table_{table['name']}"] = False
                    
                selected = st.checkbox(
                    f"**{table['name']}**",
                    key=f"table_{table['name']}"
                )

            with col2:
                st.text(f"{table['row_count']:,} rows | {table['size_mb']:.2f} MB")

            with col3:
                if selected:
                    # Initialize default if not present
                    if f"table_data_{table['name']}" not in st.session_state:
                        st.session_state[f"table_data_{table['name']}"] = True
                        
                    migrate_data = st.checkbox(
                        "Include Data",
                        key=f"table_data_{table['name']}"
                    )
    else:
        st.info("No tables found in the database")

    st.markdown("---")

    # Packages Selection
    st.subheader("📦 Packages")
    packages = result['objects']['packages']

    if packages:
        col_select_all_pkg, col_select_none_pkg = st.columns([1, 1])

        with col_select_all_pkg:
            if st.button("✓ Select All Packages"):
                for pkg in packages:
                    st.session_state[f"package_{pkg['name']}"] = True
                st.rerun()

        with col_select_none_pkg:
            if st.button("✗ Deselect All Packages"):
                for pkg in packages:
                    st.session_state[f"package_{pkg['name']}"] = False
                st.rerun()

        st.markdown("---")

        for pkg in packages:
            col1, col2 = st.columns([3, 2])

            with col1:
                # Initialize default if not present
                if f"package_{pkg['name']}" not in st.session_state:
                    st.session_state[f"package_{pkg['name']}"] = False
                    
                st.checkbox(
                    f"**{pkg['name']}**",
                    key=f"package_{pkg['name']}"
                )

            with col2:
                member_count = pkg.get('metadata', {}).get('member_count', 0)
                status = "✅" if pkg['status'] == 'VALID' else "⚠️"
                st.text(f"{member_count} members {status}")
    else:
        st.info("No packages found in the database")

    st.markdown("---")

    # Procedures, Functions, Triggers
    tabs = st.tabs(["Procedures", "Functions", "Triggers", "Views", "Sequences"])

    # Procedures Tab
    with tabs[0]:
        procedures = result['objects']['procedures']
        if procedures:
            col_all, col_none = st.columns([1, 1])
            with col_all:
                if st.button("✓ Select All", key="select_all_proc"):
                    for proc in procedures:
                        st.session_state[f"procedure_{proc['name']}"] = True
                    st.rerun()
            with col_none:
                if st.button("✗ Deselect All", key="deselect_all_proc"):
                    for proc in procedures:
                        st.session_state[f"procedure_{proc['name']}"] = False
                    st.rerun()

            for proc in procedures:
                status = "✅" if proc['status'] == 'VALID' else "⚠️"
                # Initialize default if not present
                if f"procedure_{proc['name']}" not in st.session_state:
                    st.session_state[f"procedure_{proc['name']}"] = False
                    
                st.checkbox(
                    f"{proc['name']} {status}",
                    key=f"procedure_{proc['name']}"
                )
        else:
            st.info("No procedures found")

    # Functions Tab
    with tabs[1]:
        functions = result['objects']['functions']
        if functions:
            col_all, col_none = st.columns([1, 1])
            with col_all:
                if st.button("✓ Select All", key="select_all_func"):
                    for func in functions:
                        st.session_state[f"function_{func['name']}"] = True
                    st.rerun()
            with col_none:
                if st.button("✗ Deselect All", key="deselect_all_func"):
                    for func in functions:
                        st.session_state[f"function_{func['name']}"] = False
                    st.rerun()

            for func in functions:
                status = "✅" if func['status'] == 'VALID' else "⚠️"
                # Initialize default if not present
                if f"function_{func['name']}" not in st.session_state:
                    st.session_state[f"function_{func['name']}"] = False
                    
                st.checkbox(
                    f"{func['name']} {status}",
                    key=f"function_{func['name']}"
                )
        else:
            st.info("No functions found")

    # Triggers Tab
    with tabs[2]:
        triggers = result['objects']['triggers']
        if triggers:
            col_all, col_none = st.columns([1, 1])
            with col_all:
                if st.button("✓ Select All", key="select_all_trig"):
                    for trig in triggers:
                        st.session_state[f"trigger_{trig['name']}"] = True
                    st.rerun()
            with col_none:
                if st.button("✗ Deselect All", key="deselect_all_trig"):
                    for trig in triggers:
                        st.session_state[f"trigger_{trig['name']}"] = False
                    st.rerun()

            for trig in triggers:
                table_name = trig.get('metadata', {}).get('table_name', 'N/A')
                # Initialize default if not present
                if f"trigger_{trig['name']}" not in st.session_state:
                    st.session_state[f"trigger_{trig['name']}"] = False
                    
                st.checkbox(
                    f"{trig['name']} (on {table_name})",
                    key=f"trigger_{trig['name']}"
                )
        else:
            st.info("No triggers found")

    # Views Tab
    with tabs[3]:
        views = result['objects']['views']
        if views:
            col_all, col_none = st.columns([1, 1])
            with col_all:
                if st.button("✓ Select All", key="select_all_view"):
                    for view in views:
                        st.session_state[f"view_{view['name']}"] = True
                    st.rerun()
            with col_none:
                if st.button("✗ Deselect All", key="deselect_all_view"):
                    for view in views:
                        st.session_state[f"view_{view['name']}"] = False
                    st.rerun()

            for view in views:
                # Initialize default if not present
                if f"view_{view['name']}" not in st.session_state:
                    st.session_state[f"view_{view['name']}"] = False
                    
                st.checkbox(
                    f"{view['name']}",
                    key=f"view_{view['name']}"
                )
        else:
            st.info("No views found")

    # Sequences Tab
    with tabs[4]:
        sequences = result['objects']['sequences']
        if sequences:
            col_all, col_none = st.columns([1, 1])
            with col_all:
                if st.button("✓ Select All", key="select_all_seq"):
                    for seq in sequences:
                        st.session_state[f"sequence_{seq['name']}"] = True
                    st.rerun()
            with col_none:
                if st.button("✗ Deselect All", key="deselect_all_seq"):
                    for seq in sequences:
                        st.session_state[f"sequence_{seq['name']}"] = False
                    st.rerun()

            for seq in sequences:
                current_val = seq.get('metadata', {}).get('current_value', 'N/A')
                # Initialize default if not present
                if f"sequence_{seq['name']}" not in st.session_state:
                    st.session_state[f"sequence_{seq['name']}"] = False
                    
                st.checkbox(
                    f"{seq['name']} (current: {current_val})",
                    key=f"sequence_{seq['name']}"
                )
        else:
            st.info("No sequences found")

    # Show Selection Summary BEFORE navigation
    st.markdown("---")
    st.subheader("📊 Selection Summary")

    selected = get_selected_objects()
    selected_count = count_selected_objects()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Tables", len(selected['tables']))
        st.caption(f"With data: {len(selected['tables_with_data'])}")

    with col2:
        st.metric("Packages", len(selected['packages']))

    with col3:
        st.metric("Procedures", len(selected['procedures']))
        st.caption(f"Functions: {len(selected['functions'])}")

    with col4:
        st.metric("Other", len(selected['triggers']) + len(selected['views']) + len(selected['sequences']))
        st.caption(f"Triggers/Views/Seqs")

    # Total count with color indicator
    if selected_count == 0:
        st.warning(f"⚠️ **TOTAL OBJECTS TO MIGRATE: 0** - Please select at least one object before proceeding!")
    else:
        st.success(f"✅ **TOTAL OBJECTS TO MIGRATE: {selected_count}**")

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns([1, 1])

    with col_back:
        if st.button("⬅️ Back to Discovery"):
            st.session_state.step = 2
            st.rerun()

    with col_next:
        if st.button("➡️ Next: Migration Options", type="primary"):
            # Validate selection
            if selected_count == 0:
                st.error("❌ Please select at least one object to migrate")
            else:
                # SAVE the selection to session state before moving to next step
                st.session_state.selection = selected
                logger.info(f"User selected {selected_count} objects: {selected}")
                st.session_state.step = 4
                st.rerun()


def step4_migration_options():
    """Step 4: Configure migration options"""
    st.header("Step 4: Migration Options")
    st.info("Configure how the migration should handle conflicts and existing objects.")

    # Selection Summary
    st.subheader("📊 Selection Summary")
    selected = get_selected_objects()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tables", len(selected['tables']))
    with col2:
        st.metric("Tables with Data", len(selected['tables_with_data']))
    with col3:
        st.metric("Packages", len(selected['packages']))
    with col4:
        total = (len(selected['tables']) + len(selected['packages']) +
                len(selected['procedures']) + len(selected['functions']) +
                len(selected['triggers']) + len(selected['views']) +
                len(selected['sequences']))
        st.metric("Total Objects", total)

    # Detailed list of selected objects
    if total > 0:
        with st.expander("📋 View All Selected Objects", expanded=False):
            if selected['tables']:
                st.markdown("**📋 Tables:**")
                for i, table in enumerate(selected['tables'], 1):
                    data_icon = "📊" if table in selected['tables_with_data'] else "📝"
                    st.markdown(f"{i}. {data_icon} {table}")
                st.markdown("---")

            if selected['packages']:
                st.markdown("**📦 Packages:**")
                for i, pkg in enumerate(selected['packages'], 1):
                    st.markdown(f"{i}. {pkg}")
                st.markdown("---")

            if selected['procedures']:
                st.markdown("**⚙️ Procedures:**")
                for i, proc in enumerate(selected['procedures'], 1):
                    st.markdown(f"{i}. {proc}")
                st.markdown("---")

            if selected['functions']:
                st.markdown("**🔧 Functions:**")
                for i, func in enumerate(selected['functions'], 1):
                    st.markdown(f"{i}. {func}")
                st.markdown("---")

            if selected['triggers']:
                st.markdown("**⚡ Triggers:**")
                for i, trig in enumerate(selected['triggers'], 1):
                    st.markdown(f"{i}. {trig}")
                st.markdown("---")

            if selected['views']:
                st.markdown("**👁️ Views:**")
                for i, view in enumerate(selected['views'], 1):
                    st.markdown(f"{i}. {view}")
                st.markdown("---")

            if selected['sequences']:
                st.markdown("**🔢 Sequences:**")
                for i, seq in enumerate(selected['sequences'], 1):
                    st.markdown(f"{i}. {seq}")

    st.markdown("---")

    # Conflict Resolution Options
    st.subheader("⚙️ Conflict Resolution")

    conflict_strategy = st.radio(
        "If an object already exists in SQL Server:",
        options=[
            "DROP_AND_CREATE",
            "SKIP_EXISTING",
            "CREATE_OR_ALTER",
            "FAIL_ON_CONFLICT"
        ],
        format_func=lambda x: {
            "DROP_AND_CREATE": "🔄 Drop and recreate (recommended)",
            "SKIP_EXISTING": "⏭️ Skip existing objects",
            "CREATE_OR_ALTER": "🔀 Create or alter (if supported)",
            "FAIL_ON_CONFLICT": "❌ Fail if object exists"
        }[x],
        index=0,
        key="conflict_strategy"
    )

    st.session_state.migration_options['conflict_strategy'] = conflict_strategy

    # Data Migration Options
    st.markdown("---")
    st.subheader("📊 Data Migration Options")

    batch_size = st.slider(
        "Batch size for data migration",
        min_value=100,
        max_value=10000,
        value=1000,
        step=100,
        help="Number of rows to insert in each batch. Larger batches are faster but use more memory."
    )
    st.session_state.migration_options['batch_size'] = batch_size

    truncate_before_load = st.checkbox(
        "Truncate tables before loading data",
        value=False,
        help="If enabled, existing data in SQL Server tables will be deleted before migration."
    )
    st.session_state.migration_options['truncate_before_load'] = truncate_before_load

    # Error Handling
    st.markdown("---")
    st.subheader("🛡️ Error Handling")

    stop_on_error = st.checkbox(
        "Stop migration on first error",
        value=False,
        help="If enabled, migration will stop when the first error occurs. Otherwise, it will continue with remaining objects."
    )
    st.session_state.migration_options['stop_on_error'] = stop_on_error

    max_retry_attempts = st.number_input(
        "Maximum retry attempts per object",
        min_value=0,
        max_value=5,
        value=3,
        help="Number of times to retry if an object migration fails."
    )
    st.session_state.migration_options['max_retry_attempts'] = max_retry_attempts

    # LLM Options
    st.markdown("---")
    st.subheader("🤖 LLM Options")

    use_llm_decomposer = st.checkbox(
        "Use LLM for package decomposition (recommended)",
        value=True,
        help="Uses Claude Sonnet 4 to intelligently analyze and decompose Oracle packages."
    )
    st.session_state.migration_options['use_llm_decomposer'] = use_llm_decomposer

    enable_auto_repair = st.checkbox(
        "Enable automatic error repair",
        value=True,
        help="Uses LLM to automatically fix syntax errors during deployment."
    )
    st.session_state.migration_options['enable_auto_repair'] = enable_auto_repair

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns([1, 1])

    with col_back:
        if st.button("⬅️ Back to Selection"):
            st.session_state.step = 3
            st.rerun()

    with col_next:
        if st.button("➡️ Start Migration", type="primary"):
            st.session_state.step = 5
            st.rerun()


def step5_migration():
    """Step 5: Execute migration"""
    st.header("Step 5: Migration Execution")

    if st.session_state.migration_results is None:
        st.info("Ready to start migration. This process will run without interruption.")

        # Show final summary
        selected = get_selected_objects()
        total = (len(selected['tables']) + len(selected['packages']) +
                len(selected['procedures']) + len(selected['functions']) +
                len(selected['triggers']) + len(selected['views']) +
                len(selected['sequences']))

        st.success(f"📊 **TOTAL OBJECTS TO MIGRATE: {total}**")

        # Show breakdown by type
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("📋 Tables", len(selected['tables']))
            if selected['tables_with_data']:
                st.caption(f"📊 {len(selected['tables_with_data'])} with data")
        with col2:
            st.metric("📦 Packages", len(selected['packages']))
        with col3:
            st.metric("⚙️ Procedures", len(selected['procedures']))
        with col4:
            st.metric("🔧 Functions", len(selected['functions']))
        with col5:
            other_count = len(selected['triggers']) + len(selected['views']) + len(selected['sequences'])
            st.metric("⚡ Other", other_count)
            if other_count > 0:
                st.caption(f"Triggers/Views/Seqs")

        # Detailed list of all objects that will be migrated
        st.markdown("---")
        with st.expander("📋 Click to view complete list of objects to migrate", expanded=True):
            cols = st.columns(2)

            with cols[0]:
                if selected['tables']:
                    st.markdown("**📋 Tables:**")
                    for i, table in enumerate(selected['tables'], 1):
                        data_icon = "📊" if table in selected['tables_with_data'] else "📝"
                        st.markdown(f"{i}. {data_icon} `{table}`")
                    st.markdown("---")

                if selected['procedures']:
                    st.markdown("**⚙️ Procedures:**")
                    for i, proc in enumerate(selected['procedures'], 1):
                        st.markdown(f"{i}. `{proc}`")
                    st.markdown("---")

                if selected['triggers']:
                    st.markdown("**⚡ Triggers:**")
                    for i, trig in enumerate(selected['triggers'], 1):
                        st.markdown(f"{i}. `{trig}`")

            with cols[1]:
                if selected['packages']:
                    st.markdown("**📦 Packages:**")
                    for i, pkg in enumerate(selected['packages'], 1):
                        st.markdown(f"{i}. `{pkg}`")
                    st.markdown("---")

                if selected['functions']:
                    st.markdown("**🔧 Functions:**")
                    for i, func in enumerate(selected['functions'], 1):
                        st.markdown(f"{i}. `{func}`")
                    st.markdown("---")

                if selected['views']:
                    st.markdown("**👁️ Views:**")
                    for i, view in enumerate(selected['views'], 1):
                        st.markdown(f"{i}. `{view}`")
                    st.markdown("---")

                if selected['sequences']:
                    st.markdown("**🔢 Sequences:**")
                    for i, seq in enumerate(selected['sequences'], 1):
                        st.markdown(f"{i}. `{seq}`")

        st.markdown("---")
        st.warning("⚠️ **Important:** Once you click 'Start Migration', the process will begin and cannot be interrupted. Please review the list above carefully.")

        if st.button("🚀 Start Migration Now", type="primary"):
            execute_migration()

    else:
        # Display results
        display_migration_results()




# Helper Functions for Enhanced UI Presentation

def render_log_entry(log_message: str) -> str:
    """Apply color coding to log messages using markdown"""
    if "✅" in log_message or "Success" in log_message or "successfully" in log_message:
        return f":green[{log_message}]"
    elif "❌" in log_message or "Failed" in log_message or "Error" in log_message:
        return f":red[{log_message}]"
    elif "⚠️" in log_message or "Warning" in log_message or "Partial" in log_message:
        return f":orange[{log_message}]"
    elif "🔄" in log_message or "Migrating" in log_message:
        return f":blue[{log_message}]"
    else:
        return log_message


def render_object_result_card(obj_result: dict, obj_type: str):
    """Render a structured card for migration result instead of raw JSON"""
    status = obj_result.get('status', 'unknown')
    obj_name = obj_result.get('object_name', 'Unknown')
    
    # Status badge
    if status == 'success':
        badge = "✅ **SUCCESS**"
        badge_color = "green"
    elif status == 'partial':
        badge = "⚠️ **PARTIAL SUCCESS**"
        badge_color = "orange"
    else:
        badge = "❌ **FAILED**"
        badge_color = "red"
    
    # Header
    st.markdown(f"#### {obj_name}")
    st.markdown(f":{badge_color}[{badge}]")
    
    # Type-specific rendering
    if obj_type == 'packages' and obj_result.get('strategy') == 'DECOMPOSED':
        render_package_details(obj_result)
    elif obj_type == 'tables':
        render_table_details(obj_result)
    else:
        # Generic object details
        message = obj_result.get('message', 'No details available')
        st.info(f"**Result:** {message}")
    
    # Error details if failed
    if status in ['error', 'failed']:
        if 'error_history' in obj_result or 'error' in obj_result:
            render_error_details(
                obj_result.get('error_history', []),
                obj_result.get('final_attempt', ''),
                obj_result.get('error', obj_result.get('message', ''))
            )
    
    # Technical details (show as code block instead of nested expander)
    st.markdown("---")
    st.markdown("**🔍 Technical Details (JSON)**")
    st.json(obj_result)


def render_package_details(pkg_result: dict):
    """Render special formatting for decomposed package results"""
    st.markdown("**Migration Strategy:** Package Decomposition")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Members", pkg_result.get('total_members', 0))
    with col2:
        st.metric("Succeeded", pkg_result.get('success_count', 0), delta_color="normal")
    with col3:
        st.metric("Failed", pkg_result.get('failure_count', 0), delta_color="inverse")
    
    # Warnings
    if pkg_result.get('has_global_variables'):
        st.warning("⚠️ Package contains global variables - may require manual review")
    if pkg_result.get('has_initialization'):
        st.warning("⚠️ Package contains initialization code - requires manual migration")
    
    # Migration notes (no nested expander)
    notes = pkg_result.get('notes', [])
    if notes:
        st.markdown("**📝 Migration Notes:**")
        for note in notes:
            st.markdown(f"- {note}")
    
    # Individual members
    members = pkg_result.get('members', [])
    if members:
        st.markdown("**Individual Members:**")
        for member in members:
            member_status = member.get('status', 'unknown')
            icon = "✅" if member_status == 'success' else "❌"
            member_name = member.get('member_name', 'Unknown')
            sqlserver_name = member.get('sqlserver_name', member_name)
            member_type = member.get('type', 'Unknown')
            
            # Use columns for compact display
            col_icon, col_info = st.columns([1, 9])
            with col_icon:
                st.markdown(icon)
            with col_info:
                st.markdown(f"**{member_name}** ({member_type}) → `{sqlserver_name}`")
                if member_status != 'success':
                    msg = member.get('message', 'Unknown error')
                    st.caption(f":red[{msg}]")


def render_table_details(table_result: dict):
    """Render special formatting for table migration results with column info"""
    message = table_result.get('message', 'No details available')
    st.info(f"**Result:** {message}")
    
    # Data migration stats (if available)
    if 'rows_migrated' in table_result:
        rows_migrated = table_result.get('rows_migrated', 0)
        rows_expected = table_result.get('rows_expected', rows_migrated)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Rows Migrated", f"{rows_migrated:,}")
        with col2:
            if rows_expected > 0:
                completion_pct = (rows_migrated / rows_expected) * 100
                st.metric("Completion", f"{completion_pct:.1f}%")
    
    # Column information (if available in metadata) - no nested expander
    if 'columns' in table_result:
        st.markdown("**📋 Column Details:**")
        columns = table_result['columns']
        if isinstance(columns, list):
            # Create a nice table display
            col_data = []
            for col in columns:
                if isinstance(col, dict):
                    col_data.append({
                        "Column": col.get('name', 'Unknown'),
                        "Type": col.get('data_type', 'Unknown'),
                        "Nullable": "Yes" if col.get('nullable', True) else "No",
                        "Identity": "✓" if col.get('is_identity', False) else ""
                    })
            if col_data:
                st.table(col_data)
        else:
            st.write(columns)


def render_error_details(error_history: list, final_attempt: str, error_message: str = ""):
    """Render error information in a user-friendly format"""
    st.markdown("---")
    st.markdown("### ❌ Error Details")
    
    # Main error message
    if error_message:
        st.error(f"**Error:** {error_message}")
    
    # Retry history timeline
    if error_history and len(error_history) > 0:
        st.markdown("**Retry History:**")
        for i, error_entry in enumerate(error_history, 1):
            attempt_num = error_entry.get('attempt', i)
            err_msg = error_entry.get('error', 'Unknown error')
            
            # Truncate long error messages
            if len(err_msg) > 200:
                err_msg = err_msg[:200] + "..."
            
            st.markdown(f"**Attempt {attempt_num}:** :red[{err_msg}]")
    
    # Final SQL attempt (show directly, no nested expander)
    if final_attempt:
        st.markdown("**📄 Final SQL Attempt:**")
        st.code(final_attempt, language='sql')
    
    # Actionable suggestions
    st.info("💡 **Next Steps:** Review the error details above and check the unresolved migrations log for more information.")


def calculate_migration_stats(results: dict) -> dict:
    """Calculate performance metrics from migration results"""
    stats = {
        'total_duration': 0,
        'avg_time_per_object': 0,
        'success_rate': 0,
        'by_type': {}
    }
    
    # Calculate success rate
    total = results.get('summary', {}).get('total', 0)
    success = results.get('summary', {}).get('success', 0)
    if total > 0:
        stats['success_rate'] = (success / total) * 100
    
    # Calculate by type
    for obj_type, obj_results in results.get('results', {}).items():
        if obj_results and isinstance(obj_results, list):
            # Filter out non-dict entries (like strings from foreign_keys)
            valid_results = [r for r in obj_results if isinstance(r, dict)]
            if valid_results:
                type_success = sum(1 for r in valid_results if r.get('status') in ['success', 'partial'])
                type_total = len(valid_results)
                stats['by_type'][obj_type] = {
                    'total': type_total,
                    'success': type_success,
                    'success_rate': (type_success / type_total * 100) if type_total > 0 else 0
                }
    
    return stats


# Helper Functions


def test_connections(oracle_host, oracle_port, oracle_service, oracle_user, oracle_pass,
                    sqlserver_host, sqlserver_db, sqlserver_user, sqlserver_pass):
    """Test database connections"""
    try:
        from database.oracle_connector import OracleConnector
        from database.sqlserver_connector import SQLServerConnector

        # Test Oracle
        oracle_creds = {
            "host": oracle_host,
            "port": oracle_port,
            "service_name": oracle_service,
            "username": oracle_user,
            "password": oracle_pass
        }
        oracle_conn = OracleConnector(oracle_creds)
        if not oracle_conn.connect():
            return False, "Failed to connect to Oracle database"
        oracle_conn.disconnect()

        # Test SQL Server
        sqlserver_creds = {
            "server": sqlserver_host,
            "database": sqlserver_db,
            "username": sqlserver_user,
            "password": sqlserver_pass
        }
        sqlserver_conn = SQLServerConnector(sqlserver_creds)
        if not sqlserver_conn.connect():
            return False, "Failed to connect to SQL Server database"
        sqlserver_conn.disconnect()

        return True, "Both connections successful!"

    except Exception as e:
        logger.error(f"Connection test failed: {e}", exc_info=True)
        return False, f"Connection error: {str(e)}"


def count_selected_objects():
    """Count total selected objects"""
    count = 0

    # Count tables
    if st.session_state.discovery_result:
        for table in st.session_state.discovery_result['objects']['tables']:
            if st.session_state.get(f"table_{table['name']}", False):
                count += 1

        # Count packages
        for pkg in st.session_state.discovery_result['objects']['packages']:
            if st.session_state.get(f"package_{pkg['name']}", False):
                count += 1

        # Count procedures
        for proc in st.session_state.discovery_result['objects']['procedures']:
            if st.session_state.get(f"procedure_{proc['name']}", False):
                count += 1

        # Count functions
        for func in st.session_state.discovery_result['objects']['functions']:
            if st.session_state.get(f"function_{func['name']}", False):
                count += 1

        # Count triggers
        for trig in st.session_state.discovery_result['objects']['triggers']:
            if st.session_state.get(f"trigger_{trig['name']}", False):
                count += 1

        # Count views
        for view in st.session_state.discovery_result['objects']['views']:
            if st.session_state.get(f"view_{view['name']}", False):
                count += 1

        # Count sequences
        for seq in st.session_state.discovery_result['objects']['sequences']:
            if st.session_state.get(f"sequence_{seq['name']}", False):
                count += 1

    return count


def get_selected_objects():
    """Get all selected objects"""
    # If selection was already saved (from Step 3), use that
    if st.session_state.get('selection') and st.session_state.selection:
        logger.info(f"Using saved selection from session state")
        return st.session_state.selection

    # Otherwise, collect from checkbox states
    selected = {
        'tables': [],
        'tables_with_data': [],
        'packages': [],
        'procedures': [],
        'functions': [],
        'triggers': [],
        'views': [],
        'sequences': []
    }

    if st.session_state.discovery_result:
        # Tables
        for table in st.session_state.discovery_result['objects']['tables']:
            if st.session_state.get(f"table_{table['name']}", False):
                selected['tables'].append(table['name'])
                if st.session_state.get(f"table_data_{table['name']}", True):
                    selected['tables_with_data'].append(table['name'])

        # Packages
        for pkg in st.session_state.discovery_result['objects']['packages']:
            if st.session_state.get(f"package_{pkg['name']}", False):
                selected['packages'].append(pkg['name'])

        # Procedures
        for proc in st.session_state.discovery_result['objects']['procedures']:
            if st.session_state.get(f"procedure_{proc['name']}", False):
                selected['procedures'].append(proc['name'])

        # Functions
        for func in st.session_state.discovery_result['objects']['functions']:
            if st.session_state.get(f"function_{func['name']}", False):
                selected['functions'].append(func['name'])

        # Triggers
        for trig in st.session_state.discovery_result['objects']['triggers']:
            if st.session_state.get(f"trigger_{trig['name']}", False):
                selected['triggers'].append(trig['name'])

        # Views
        for view in st.session_state.discovery_result['objects']['views']:
            if st.session_state.get(f"view_{view['name']}", False):
                selected['views'].append(view['name'])

        # Sequences
        for seq in st.session_state.discovery_result['objects']['sequences']:
            if st.session_state.get(f"sequence_{seq['name']}", False):
                selected['sequences'].append(seq['name'])

    return selected


def execute_migration():
    """Execute the migration process with engaging UI"""
    try:
        from config.config_enhanced import CostTracker
        from agents.orchestrator_agent import MigrationOrchestrator
        from utils.migration_engine_v2 import get_user_selection, migrate_table_data, validate_migration

        selected = get_selected_objects()
        total_objects = (len(selected['tables']) + len(selected['packages']) +
                        len(selected['procedures']) + len(selected['functions']) +
                        len(selected['triggers']) + len(selected['views']) +
                        len(selected['sequences']))

        cost_tracker = CostTracker()
        orchestrator = MigrationOrchestrator(
            st.session_state.oracle_creds,
            st.session_state.sqlserver_creds,
            cost_tracker,
            st.session_state.migration_options
        )

        results = {
            "tables": [],
            "packages": [],
            "procedures": [],
            "functions": [],
            "triggers": [],
            "views": [],
            "sequences": []
        }

        success_count = 0
        failure_count = 0

        # Simple, clean migration UI
        st.subheader("🚀 Migration in Progress")
        st.caption("AI-powered migration • Real-time tracking")

        # Simple metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🎯 Total", total_objects)
        metric_success = col2.empty()
        metric_failed = col3.empty()
        metric_progress = col4.empty()

        # Simple progress bar
        progress_bar = st.progress(0)
        progress_text = st.empty()

        # Current operation
        current_operation = st.empty()

        # Migration log
        st.divider()
        st.subheader("📋 Migration Log")
        log_container = st.container()

        logs = []
        current_idx = 0
        start_time = time.time()

        def update_metrics():
            """Update simple metrics"""
            metric_success.metric("✅ Success", success_count)
            metric_failed.metric("❌ Failed", failure_count)

            progress_pct = (current_idx / total_objects) if total_objects > 0 else 0
            metric_progress.metric("📊 Progress", f"{int(progress_pct * 100)}%")

            progress_bar.progress(progress_pct)
            elapsed = int(time.time() - start_time)
            eta = int((elapsed / current_idx * (total_objects - current_idx))) if current_idx > 0 else 0
            progress_text.text(f"Progress: {current_idx}/{total_objects} | Elapsed: {elapsed}s | ETA: {eta}s")

        def add_log(message):
            """Add log entry with professional formatting"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Filter out verbose internal messages
            if any(skip_pattern in message.lower() for skip_pattern in ['debug', 'trace', 'verbose', 'internal']):
                return
            
            # Format the log entry with color coding
            formatted_msg = render_log_entry(message)
            logs.append(f"`{timestamp}` {formatted_msg}")
            
            # Display in container with professional styling
            with log_container:
                # Show only last15 logs to keep it clean
                st.markdown("---")
                for log in logs[-15:]:
                    st.markdown(log)

        # Migrate tables
        if selected['tables']:
            current_operation.info(f"📋 Migrating {len(selected['tables'])} Tables...")

            for i, table_name in enumerate(selected['tables'], 1):
                result = orchestrator.orchestrate_table_migration(table_name)
                result['object_name'] = table_name
                result['object_type'] = 'TABLE'
                results["tables"].append(result)

                if result.get("status") == "success":
                    success_count += 1
                    
                    # Migrate data if selected
                    if table_name in selected['tables_with_data']:
                        data_result = migrate_table_data(
                            st.session_state.oracle_creds,
                            st.session_state.sqlserver_creds,
                            table_name
                        )

                        if data_result.get("status") == "success":
                            rows = data_result.get("rows_migrated", 0)
                            add_log(f"✅ **{table_name}** — {rows:,} rows")
                        else:
                            add_log(f"⚠️ **{table_name}** — structure only")
                    else:
                        add_log(f"✅ **{table_name}** — structure")
                else:
                    failure_count += 1
                    add_log(f"❌ **{table_name}** — failed")

                current_idx += 1
                update_metrics()

        # Apply foreign keys after all tables are created
        if selected['tables']:
            current_operation.info("🔗 Applying Foreign Keys...")
            fk_result = orchestrator.apply_all_foreign_keys()

            if fk_result.get('total', 0) > 0:
                applied = fk_result.get('applied', 0)
                failed = fk_result.get('failed', 0)
                add_log(f"🔗 Foreign Keys: {applied} applied, {failed} failed" if failed > 0 else f"🔗 Foreign Keys: {applied} applied")
                results["foreign_keys"] = fk_result

        # Migrate packages  
        if selected['packages']:
            current_operation.info(f"📦 Migrating {len(selected['packages'])} Packages...")

            for i, pkg_name in enumerate(selected['packages'], 1):
                result = orchestrator.orchestrate_code_object_migration(pkg_name, "PACKAGE")
                result['object_name'] = pkg_name
                result['object_type'] = 'PACKAGE'
                results["packages"].append(result)

                if result.get("status") in ["success", "partial"]:
                    success_count += 1
                    member_count = result.get("total_members", 0)
                    success_members = result.get("success_count", 0)
                    if result.get("status") == "success":
                        add_log(f"✅ **{pkg_name}** — {success_members}/{member_count} members")
                    else:
                        add_log(f"⚠️ **{pkg_name}** — {success_members}/{member_count} members")
                else:
                    failure_count += 1
                    add_log(f"❌ **{pkg_name}** — failed")

                current_idx += 1
                update_metrics()

        # Migrate other objects
        obj_config = {
            "procedures": ("⚙️", "Procedures"),
            "functions": ("🔧", "Functions"),
            "triggers": ("⚡", "Triggers"),
            "views": ("👁️", "Views"),
            "sequences": ("🔢", "Sequences")
        }

        for obj_type in ["procedures", "functions", "triggers", "views", "sequences"]:
            obj_list = selected[obj_type]
            if obj_list:
                icon, display_name = obj_config[obj_type]
                current_operation.info(f"{icon} Migrating {len(obj_list)} {display_name}...")

                for obj_name in obj_list:
                    result = orchestrator.orchestrate_code_object_migration(obj_name, obj_type[:-1].upper())
                    result['object_name'] = obj_name
                    result['object_type'] = obj_type[:-1].upper()
                    results[obj_type].append(result)

                    if result.get("status") == "success":
                        success_count += 1
                        add_log(f"✅ **{obj_name}**")
                    else:
                        failure_count += 1
                        add_log(f"❌ **{obj_name}**")

                    current_idx += 1
                    update_metrics()

        # Migration Complete!
        update_metrics()
        add_log("🎉 Migration completed!")

        total_time = int(time.time() - start_time)
        success_rate = int((success_count / total_objects) * 100) if total_objects > 0 else 0

        current_operation.success(f"🎉 **Migration Complete!** | Success: {success_count} | Failed: {failure_count} | Success Rate: {success_rate}% | Time: {total_time}s")

        # Save results
        final_results = {
            "selection": selected,
            "results": results,
            "summary": {
                "total": total_objects,
                "success": success_count,
                "failed": failure_count
            },
            "cost": str(cost_tracker),
            "timestamp": datetime.now().isoformat(),
            "options": st.session_state.migration_options
        }

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        with open(output_dir / "migration_results.json", 'w') as f:
            json.dump(final_results, f, indent=2)

        st.session_state.migration_results = final_results

        time.sleep(2)  # Give users time to see the final status
        st.rerun()

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        st.error(f"❌ Migration failed: {str(e)}")


def display_migration_results():
    """Display migration results with enhanced formatting"""
    results = st.session_state.migration_results

    st.success("✅ Migration completed!")

    # Calculate stats
    stats = calculate_migration_stats(results)
    
    # Summary Dashboard
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Objects", results['summary']['total'])
    with col2:
        st.metric("✅ Successful", results['summary']['success'])
    with col3:
        st.metric("❌ Failed", results['summary']['failed'])
    with col4:
        success_rate = stats.get('success_rate', 0)
        st.metric("Success Rate", f"{success_rate:.1f}%")

    # Cost and timestamp
    col_cost, col_time = st.columns(2)
    with col_cost:
        st.info(f"💰 {results['cost']}")
    with col_time:
        timestamp = results.get('timestamp', 'Unknown')
        if timestamp and timestamp != 'Unknown':
            try:
                dt = datetime.fromisoformat(timestamp)
                st.info(f"🕐 Completed: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                st.info(f"🕐 Completed: {timestamp}")

    # Performance stats by type
    if stats.get('by_type'):
        with st.expander("📈 Performance by Object Type"):
            for obj_type, type_stats in stats['by_type'].items():
                col_type, col_count, col_rate = st.columns([2, 1, 1])
                with col_type:
                    st.write(f"**{obj_type.capitalize()}**")
                with col_count:
                    st.write(f"{type_stats['success']}/{type_stats['total']}")
                with col_rate:
                    st.write(f"{type_stats['success_rate']:.0f}%")

    # Detailed results with structured cards
    st.markdown("---")
    st.subheader("📊 Detailed Results")

    tabs = st.tabs(["Tables", "Packages", "Procedures", "Functions", "Triggers", "Views", "Sequences"])

    for tab, (obj_type, obj_results) in zip(tabs, results['results'].items()):
        with tab:
            if obj_results:
                for obj_result in obj_results:
                    status = obj_result.get('status', 'unknown')
                    icon = "✅" if status in ['success', 'partial'] else "❌"
                    obj_name = obj_result.get('object_name', 'Unknown')

                    with st.expander(f"{icon} {obj_name}", expanded=(status not in ['success'])):
                        # Use new structured card rendering
                        render_object_result_card(obj_result, obj_type)
            else:
                st.info(f"No {obj_type} were migrated")

    # Download results
    st.markdown("---")
    st.download_button(
        label="📥 Download Full Results (JSON)",
        data=json.dumps(results, indent=2),
        file_name=f"migration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

    # Navigation to Verification
    st.markdown("---")
    col_restart, col_verify = st.columns([1, 1])

    with col_restart:
        if st.button("🔄 Start New Migration"):
            # Reset session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
    with col_verify:
        if st.button("🔎 Verify Migration (Post-Migration)", type="primary"):
            st.session_state.step = 6
            st.rerun()



def step6_verification():
    """Step 6: Post-Migration Verification"""
    st.header("Step 6: Post-Migration Verification")
    st.info("Verify migrated data and review unresolved issues.")

    tabs = st.tabs(["🔍 Data Verification", "⚠️ Unresolved Issues", "🧠 Migration Memory"])

    # Tab 1: Data Verification
    with tabs[0]:
        st.subheader("Verify Table Data")
        
        # Get migrated tables
        migrated_tables = []
        if st.session_state.migration_results:
            for table_res in st.session_state.migration_results['results']['tables']:
                if table_res.get('status') == 'success':
                    migrated_tables.append(table_res.get('object_name'))
        
        if migrated_tables:
            selected_table = st.selectbox("Select Table to Verify", migrated_tables)
            
            if st.button("Check Row Count"):
                try:
                    from database.sqlserver_connector import SQLServerConnector
                    conn = SQLServerConnector(st.session_state.sqlserver_creds)
                    if conn.connect():
                        count = conn.execute_query(f"SELECT COUNT(*) FROM [{selected_table}]")[0][0]
                        st.metric(f"Rows in SQL Server ({selected_table})", f"{count:,}")
                        conn.disconnect()
                    else:
                        st.error("Failed to connect to SQL Server")
                except Exception as e:
                    st.error(f"Verification failed: {e}")
        else:
            st.info("No tables were successfully migrated to verify.")

    # Tab 2: Unresolved Issues
    with tabs[1]:
        st.subheader("Unresolved Migrations (JSONL)")
        
        log_file = Path("logs/unresolved_migrations.jsonl")
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            st.warning(f"Found {len(lines)} unresolved issues.")
            
            for line in lines:
                try:
                    entry = json.loads(line)
                    with st.expander(f"❌ {entry.get('object_type')} - {entry.get('object_name')}"):
                        st.json(entry)
                except:
                    pass
        else:
            st.success("No unresolved issues found in logs!")

    # Tab 3: Memory
    with tabs[2]:
        st.subheader("Migration Memory Stats")
        try:
            from database.migration_memory import MigrationMemory
            memory = MigrationMemory()
            stats = memory.get_stats()
            st.json(stats)
        except Exception as e:
            st.error(f"Could not load memory: {e}")

    # Back button
    if st.button("⬅️ Back to Results"):
        st.session_state.step = 5
        st.rerun()


# Main Application

def main():
    """Main application entry point"""
    render_header()

    # Route to appropriate step
    if st.session_state.step == 1:
        step1_credentials()
    elif st.session_state.step == 2:
        step2_discovery()
    elif st.session_state.step == 3:
        step3_selection()
    elif st.session_state.step == 4:
        step4_migration_options()
    elif st.session_state.step == 5:
        step5_migration()
    elif st.session_state.step == 6:
        step6_verification()


if __name__ == "__main__":
    main()
