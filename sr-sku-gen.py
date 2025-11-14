"""
Asian Supermarket SKU System
File: asian_supermarket_sku_system.py

This single-file package contains:
- SKU specification (human-readable and numeric)
- In-memory dictionaries for categories/brands (editable)
- SQLite3 schema and helper functions to initialize and interact with the DB
- Auto-SKU generation algorithm (human-readable and compact numeric)
- CSV/Spreadsheet export helpers (template + export)
- A PyQt6 GUI to create / preview / save SKUs and export the sku list

Usage:
- Run as `python asian_supermarket_sku_system.py` to open the GUI.
- Import functions from the file in other modules for programmatic use.

Notes:
- This code is intentionally self-contained and avoids external dependencies beyond PyQt6.
- CSV export is UTF-8 with BOM to help Excel open it correctly.
- The numeric SKU generator uses a per-(category,brand) counter stored in the DB.

"""

from __future__ import annotations
import sqlite3
import csv
import os
import datetime
from typing import Optional, Tuple

# PyQt6 imports
try:
    from PyQt6 import QtWidgets, QtCore
except Exception:
    QtWidgets = None
    QtCore = None

DB_FILENAME = "skus.db"

# ======== Config / Lookups ========
# These maps are example starting values. Expand as needed or load from a config table in the DB.
CATEGORY_MAP = {
    '01': {
        'name': 'Groceries & Staples',
        'subcategories': {
            '1': 'Noodle',
            '2': 'Sauce',
            '3': 'Spices',
            '4': 'Pulses & Beans',
            '5': 'Tea',
            '6': 'Flour',
            '7': 'Oil'
        }
    },
    '02': {
        'name': 'Rice',
        'subcategories': {
            '1': 'Basmati',
            '2': 'Sella Basmati',
            '3': 'Idli',
            '4': 'Soona Masoori',
            '5': 'Brown',
            '6': 'Glutonious',
            '7': 'Jasmin',
            '8': 'Sushi',
            '9': 'Puffed Rice',
            '10': 'Rice Flakes'
        }
    },
    '03': {
        'name': 'Fresh',
        'subcategories': {
            '1': 'Meat',
            '2': 'Vegetable',
            '3': 'Fruit'
        }
    },
    '04': {
        'name': 'Frozen',
        'subcategories': {
            '1': 'Whole Fish',
            '2': 'Block Fish',
            '3': 'Vegetable',
            '4': 'Pastry',
            '5': 'Meat',
            '6': 'Dessert'
        }
    },
    '05': {
        'name': 'Beverages',
        'subcategories': {
            '1': 'Soft drinks',
            '2': 'Juice',
            '3': 'Smoothie',
            '4': 'Ice Tea',
            '5': 'Bubble Tea',
            '6': 'Falooda',
            '7': 'Sparkling',
            '8': 'Herbal',
            '9': 'Limonade',
            '10': 'Aloevera'
        }
    },
    '06': {
        'name': 'Sweets & Deserts',
        'subcategories': {
            '1': 'Icecream',
            '2': 'Coconut Desert',
            '3': 'Handmade'
        }
    },
    '07': {
        'name': 'Snacks & Munching',
        'subcategories': {
            '1': 'Chips',
            '2': 'Biscuits',
            '3': 'Rusk',
            '4': 'Chanachur'
        }
    },
    '08': {
        'name': 'Non-Food',
        'subcategories': {
            '1': 'Incense',
            '2': 'Utensils',
            '3': 'Kitchen Accessories'
        }
    }
}

BRAND_MAP = {
    '001': 'A',
    '002': 'AASHIRVAAD',
    '003': 'ACECOOK',
    '004': 'AFROASE',
    '005': 'AGARBATTI',
    '006': 'AHMED',
    '007': 'AKASH',
    '008': 'ANNAM',
    '009': 'ANNY',
    '010': 'AROD-D',
    '011': 'ASH K',
    '012': 'ASHOKA',
    '013': 'ASIAN CHOICE',
    '014': 'ATOOM',
    '015': 'AQUAPEARL',
    '016': 'BAIJIA',
    '017': 'BAMBOO TREE',
    '018': 'BICANO',
    '019': 'BIK',
    '020': 'BINGGRAE',
    '021': 'BIBIGO',
    '022': 'BOMBAY',
    '023': 'BRITANNIA',
    '024': 'CARNATION',
    '025': 'CARABAO',
    '026': 'CHIU CHOW',
    '027': 'CHUPA CHUPS',
    '028': 'COCK',
    '029': 'COCON',
    '030': 'COFE',
    '031': 'CROWN FARM',
    '032': 'CYPRESSA',
    '033': 'DAN',
    '034': 'DABUR',
    '035': 'DETTOL',
    '036': 'DOUX',
    '037': 'EAGLOBE',
    '038': 'EFP',
    '039': 'ELEFANT',
    '040': 'ELEPHANT',
    '041': 'ENCONA',
    '042': 'EVERBEST',
    '043': 'FARMER',
    '044': 'FOCO',
    '045': 'GENKI RAMUNE',
    '046': 'GINGERBON',
    '047': 'GITS',
    '048': 'GOGI',
    '049': 'GOLESTAN',
    '050': 'GOLD KILI',
    '051': 'GOLDEN MOUNTAIN',
    '052': 'GREEN FARM',
    '053': 'GREEN TABLE',
    '054': 'HAIDILAO',
    '055': 'HALDIRAM',
    '056': 'HAOHAO',
    '057': 'HEALTHY BOY',
    '058': 'HEERA',
    '059': 'HEER',
    '060': 'HEINZ',
    '061': 'HEMANI',
    '062': 'HENG SHUN',
    '063': 'HERBEX',
    '064': 'HERITAGE AFRIKA',
    '065': "HERR'S",
    '066': 'HIKARI MISO',
    '067': 'HUMZA',
    '068': 'HOT CHIP',
    '069': 'HORLICKS',
    '070': 'HYPER MALT',
    '071': 'IDEAL',
    '072': 'IFAD',
    '073': 'INDOMIE',
    '074': 'INDIA GATE',
    '075': 'ISPAHANI',
    '076': 'JAZZA',
    '077': 'JH FOODS',
    '078': 'JHFOODS',
    '079': 'JIA BRAND',
    '080': 'JIABAO',
    '081': 'JIADUOBAO',
    '082': 'JING YI GEN',
    '083': 'JONGGA',
    '084': 'KAIJAE',
    '085': 'KAILO',
    '086': 'KATO',
    '087': 'KHANUM',
    '088': 'KHONG DO',
    '089': 'KIKKOMAN',
    '090': 'KIMHO',
    '091': 'KINGZEST',
    '092': 'KNORR',
    '093': 'KOH-KAE',
    '094': 'KTC',
    '095': 'KULFI ICE',
    '096': 'KURKURE',
    '097': 'LACTASOY',
    '098': 'LAILA',
    '099': 'LAKOVO',
    '100': 'LAO GAN MA',
    '101': 'LAZIZA',
    '102': 'LAYS',
    '103': 'LEXUS',
    '104': 'LIJJAT',
    '105': 'LIPTON',
    '106': 'LITTLE MOONS',
    '107': 'LKK',
    '108': 'LONGLIFE',
    '109': 'MAE KRUA',
    '110': 'MAE NAPA',
    '111': 'MAGGI',
    '112': 'MAN TANG XIAN',
    '113': 'MAO XIONG',
    '114': 'MARUKOME',
    '115': 'MAMA',
    '116': "MAMA'S CHOICE",
    '117': 'MDH',
    '118': 'MEGA',
    '119': 'MEGACHEF',
    '120': 'MEHEK',
    '121': 'MEIJI H.PANDA',
    '122': 'MILKIS',
    '123': 'MILO',
    '124': 'MINI MELTS',
    '125': 'ML SQUID',
    '126': 'MOGUMOGU',
    '127': 'MP',
    '128': 'MTR',
    '129': 'MYM',
    '130': 'NARCISSUS',
    '131': 'NATURINDA',
    '132': 'NESTLÉ',
    '133': 'NIDO',
    '134': 'NITTAYA',
    '135': 'NONGSHIM',
    '136': 'NOODLE HOUSE',
    '137': 'OISHI',
    '138': 'OKF',
    '139': 'OTAFUKU',
    '140': 'OVALTINE',
    '141': 'OYAKATA',
    '142': 'PATAK',
    '143': 'PAN',
    '144': 'PARACHUTE',
    '145': 'PARLE',
    '146': 'PG TIPS',
    '147': 'PCD',
    '148': 'PERFIT',
    '149': 'PILLSBURY',
    '150': 'PLUVERA',
    '151': 'PRAN',
    '152': 'PRESIDENT',
    '153': 'PRB',
    '154': 'PRIMA',
    '155': 'PULMUONE',
    '156': 'QARSHI',
    '157': 'RAFHAN',
    '158': 'RAITIP',
    '159': 'RADHUNI',
    '160': 'RABBIT',
    '161': 'REGAL',
    '162': 'RENUKA',
    '163': 'RICO',
    '164': 'ROYAL ORIENT',
    '165': 'ROYAL THAI',
    '166': 'ROYAL THAI RICE',
    '167': 'ROYAL TIGER',
    '168': 'RUBICON',
    '169': 'RUCHI',
    '170': 'SAGIKO',
    '171': 'SAHIBA',
    '172': 'SALANTY',
    '173': 'SAMYANG',
    '174': 'SANHAN',
    '175': 'SCHANI',
    '176': 'SEMPIओ',
    '177': 'SHANA',
    '178': 'SHAN',
    '179': 'SHAN WAI',
    '180': 'SHEZAN',
    '181': 'SHODESH'
}

# Quantity map added (1‑digit codes)
QUANTITY_MAP = {
    '1': '250g/ml',
    '2': '500g/ml',
    '3': '1000g/ml',
    '4': '3000g/ml',
    '5': '5000g/ml',
    '6': '8000g/ml',
    '7': '10000g/ml',
    '8': '15000g/ml',
    '9': '20000g/ml'
}

# ======== SQLite Helpers ========

def get_connection(db_path: str = DB_FILENAME) -> sqlite3.Connection:
    # Use check_same_thread=False to allow connection from PyQt6 threads
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    cur = conn.cursor()
    try:
        cur.execute('PRAGMA journal_mode=WAL')
        conn.commit()
    finally:
        cur.close()
    return conn


def migrate_counters_table(conn: sqlite3.Connection):
    """Migrate counters table to include subcategory_code and quantity_code if missing"""
    cur = conn.cursor()
    try:
        # Check if counters table exists and get its schema
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='counters'")
        if cur.fetchone():
            # Table exists, check columns
            cur.execute("PRAGMA table_info(counters)")
            columns = [row[1] for row in cur.fetchall()]
            
            # Check if we need to migrate
            needs_migration = False
            if 'subcategory_code' not in columns or 'quantity_code' not in columns:
                needs_migration = True
            
            if needs_migration:
                print("Migrating counters table to new schema...")
                # Since counters are just sequence numbers, we can safely drop and recreate
                # The counters will be regenerated as needed when SKUs are created
                cur.execute("DROP TABLE IF EXISTS counters")
                conn.commit()
                print("Counters table dropped - will be recreated with new schema")
    finally:
        cur.close()


def migrate_skus_table(conn: sqlite3.Connection):
    """Migrate skus table to new schema if needed"""
    cur = conn.cursor()
    try:
        # Check if skus table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='skus'")
        if cur.fetchone():
            # Table exists, check columns
            cur.execute("PRAGMA table_info(skus)")
            columns = [row[1] for row in cur.fetchall()]
            
            # Required columns for new schema
            required_columns = ['human_sku', 'numeric_sku', 'brand_code', 'category_code', 
                              'subcategory_code', 'quantity_code', 'product_seq', 'full_product_name']
            
            # Check if we need to migrate
            needs_migration = False
            for req_col in required_columns:
                if req_col not in columns:
                    needs_migration = True
                    break
            
            if needs_migration:
                print("Migrating skus table to new schema...")
                # Backup existing data if possible
                try:
                    # Try to read existing data
                    cur.execute("SELECT * FROM skus")
                    old_data = cur.fetchall()
                    old_columns = columns
                    print(f"Found {len(old_data)} existing SKU records to migrate")
                except Exception as e:
                    print(f"Could not read existing SKU data: {e}")
                    old_data = []
                    old_columns = []
                
                # Drop old table
                cur.execute("DROP TABLE IF EXISTS skus")
                conn.commit()
                print("Skus table dropped - will be recreated with new schema")
                
                # Note: We don't restore old data because the schema is too different
                # Users will need to recreate SKUs with the new system
                if old_data:
                    print(f"Note: {len(old_data)} old SKU records were not migrated due to schema changes")
    finally:
        cur.close()


def initialize_db(conn: Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True
    cur = conn.cursor()
    try:
        # Migrate existing tables if needed (before creating them)
        migrate_skus_table(conn)
        migrate_counters_table(conn)
        
        # skus table stores the components of the SKU separately for easy querying
        # Create after migration to ensure correct schema
        cur.execute('''
        CREATE TABLE IF NOT EXISTS skus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            human_sku TEXT UNIQUE NOT NULL,
            numeric_sku TEXT UNIQUE NOT NULL,
            brand_code TEXT NOT NULL,
            category_code TEXT NOT NULL,
            subcategory_code TEXT NOT NULL,
            quantity_code TEXT NOT NULL,
            product_seq TEXT NOT NULL,
            product_slug TEXT,
            full_product_name TEXT,
            country_code TEXT,
            note TEXT,
            barcode TEXT,
            created_at TEXT
        );
        ''')
        
        # counters table stores the last used sequence per (brand,category,subcategory,quantity)
        # Create after migration to ensure correct schema
        cur.execute('''
        CREATE TABLE IF NOT EXISTS counters (
            brand_code TEXT,
            category_code TEXT,
            subcategory_code TEXT,
            quantity_code TEXT,
            counter INTEGER,
            PRIMARY KEY (brand_code, category_code, subcategory_code, quantity_code)
        );
        ''')
        conn.commit()
    finally:
        cur.close()
    if close_after:
        conn.close()
    return conn


# Format human-readable SKU: BBB-CC-S-Q-PPP
def format_human_sku(brand_code: str, category_code: str, subcategory_code: str, quantity_code: str, product_seq: str) -> str:
    return f"{brand_code}-{category_code}-{subcategory_code}-{quantity_code}-{product_seq}"


# Format numeric SKU (compact, no separators)
def format_numeric_sku(brand_code: str, category_code: str, subcategory_code: str, quantity_code: str, product_seq: str) -> str:
    return f"{brand_code}{category_code}{subcategory_code}{quantity_code}{product_seq}"


def generate_product_code_from_name(name: str, length: int = 3) -> str:
    # Keep this for backward compatibility if needed; not used as the final product id
    clean = ''.join(ch for ch in name.upper() if ch.isalnum())
    if len(clean) >= length:
        return clean[:length]
    else:
        return clean.ljust(length, 'X')


def get_next_sequence(conn: sqlite3.Connection, brand_code: str, category_code: str, subcategory_code: str, quantity_code: str) -> int:
    cur = conn.cursor()
    try:
        cur.execute('SELECT counter FROM counters WHERE brand_code=? AND category_code=? AND subcategory_code=? AND quantity_code=?',
                    (brand_code, category_code, subcategory_code, quantity_code))
        row = cur.fetchone()
        if row is None:
            cur.execute('INSERT INTO counters (brand_code, category_code, subcategory_code, quantity_code, counter) VALUES (?,?,?,?,?)',
                        (brand_code, category_code, subcategory_code, quantity_code, 1))
            conn.commit()
            return 1
        else:
            next_val = row['counter'] + 1
            cur.execute('UPDATE counters SET counter=? WHERE brand_code=? AND category_code=? AND subcategory_code=? AND quantity_code=?',
                        (next_val, brand_code, category_code, subcategory_code, quantity_code))
            conn.commit()
            return next_val
    finally:
        cur.close()


def create_sku_record(conn: sqlite3.Connection, brand_code: str, category_code: str, subcategory_code: str, quantity_code: str, product_name: str, country_code: Optional[str] = None, note: Optional[str] = None, barcode: Optional[str] = None) -> Tuple[str, str]:
    # Create slug
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in product_name).strip('-')

    brand_code = brand_code.zfill(3)
    category_code = category_code.zfill(2)
    # Safe string slicing - get last character or use the whole string if too short
    subcategory_code = subcategory_code[-1] if len(subcategory_code) > 0 else '0'
    quantity_code = quantity_code[-1] if len(quantity_code) > 0 else '0'

    seq = get_next_sequence(conn, brand_code, category_code, subcategory_code, quantity_code)
    product_seq = str(seq).zfill(2)

    human_sku = format_human_sku(brand_code, category_code, subcategory_code, quantity_code, product_seq)
    numeric_sku = format_numeric_sku(brand_code, category_code, subcategory_code, quantity_code, product_seq)

    created_at = datetime.datetime.utcnow().isoformat()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO skus (human_sku, numeric_sku, brand_code, category_code, subcategory_code, quantity_code, product_seq, product_slug, full_product_name, country_code, note, barcode, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (human_sku, numeric_sku, brand_code, category_code, subcategory_code, quantity_code, product_seq, slug, product_name, country_code, note, barcode, created_at))
        conn.commit()
    finally:
        cur.close()
    return human_sku, numeric_sku


def export_skus_to_csv(conn: sqlite3.Connection, filepath: str):
    cur = conn.cursor()
    try:
        cur.execute('SELECT * FROM skus ORDER BY id')
        rows = cur.fetchall()
        columns = [
            ("id", "ID"),
            ("human_sku", "Human SKU"),
            ("numeric_sku", "Numeric SKU"),
            ("brand_code", "Brand Code"),
            ("category_code", "Category Code"),
            ("subcategory_code", "Subcategory Code"),
            ("quantity_code", "Quantity Code"),
            ("product_seq", "Product Seq"),
            ("product_slug", "Slug Name"),
            ("full_product_name", "Product Name"),
            ("country_code", "Country Code"),
            ("note", "Note"),
            ("barcode", "Barcode"),
            ("created_at", "Created At")
        ]
        # Write with BOM to increase Excel compatibility
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([display for _, display in columns])
            for r in rows:
                writer.writerow([r[key] for key, _ in columns])
    finally:
        cur.close()
    return filepath


def create_spreadsheet_template(filepath: str):
    # Sample columns and a few example rows to seed a template
    header = ["category_code","brand_code","product_name","variant_code","country_code","note","barcode"]
    examples = [
        ['02','01','Shin Ramyun','02','KR','spicy instant ramen','88010731XXXX'],
        ['05','03','Soy Sauce 1L','05','JP','all-purpose soy sauce','49000000YYYY'],
    ]
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(examples)
    return filepath

# ======== Simple CLI utilities ========

def list_skus(conn: sqlite3.Connection, limit: int = 100):
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                id, 
                human_sku, 
                numeric_sku, 
                product_slug, 
                full_product_name, 
                barcode, 
                created_at
            FROM skus 
            ORDER BY id DESC 
            LIMIT ?
        ''', (limit,))
        return cur.fetchall()
    finally:
        cur.close()


def get_sku_by_id(conn: sqlite3.Connection, sku_id: int):
    """Get a single SKU record by ID"""
    cur = conn.cursor()
    try:
        cur.execute('SELECT * FROM skus WHERE id = ?', (sku_id,))
        return cur.fetchone()
    finally:
        cur.close()


def update_sku_record(conn: sqlite3.Connection, sku_id: int, brand_code: str, category_code: str, subcategory_code: str, quantity_code: str, product_name: str, country_code: Optional[str] = None, note: Optional[str] = None, barcode: Optional[str] = None):
    """Update an existing SKU record"""
    # Create slug
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in product_name).strip('-')

    brand_code = brand_code.zfill(3)
    category_code = category_code.zfill(2)
    subcategory_code = subcategory_code[-1] if len(subcategory_code) > 0 else '0'
    quantity_code = quantity_code[-1] if len(quantity_code) > 0 else '0'

    # Get existing SKU to preserve product_seq
    existing = get_sku_by_id(conn, sku_id)
    if not existing:
        raise ValueError(f"SKU with id {sku_id} not found")
    
    product_seq = existing['product_seq']
    human_sku = format_human_sku(brand_code, category_code, subcategory_code, quantity_code, product_seq)
    numeric_sku = format_numeric_sku(brand_code, category_code, subcategory_code, quantity_code, product_seq)

    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE skus SET 
                human_sku=?, numeric_sku=?, brand_code=?, category_code=?, subcategory_code=?, 
                quantity_code=?, product_slug=?, full_product_name=?, country_code=?, note=?, barcode=?
            WHERE id=?
        ''', (human_sku, numeric_sku, brand_code, category_code, subcategory_code, quantity_code, 
              slug, product_name, country_code, note, barcode, sku_id))
        conn.commit()
    finally:
        cur.close()
    return human_sku, numeric_sku


def delete_sku_record(conn: sqlite3.Connection, sku_id: int):
    """Delete a SKU record by ID"""
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM skus WHERE id = ?', (sku_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close()


def get_last_ten_entries(conn: sqlite3.Connection):
    """Get the last 10 SKU entries"""
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT id, human_sku, numeric_sku, brand_code, category_code, subcategory_code, 
                   quantity_code, product_seq, full_product_name, country_code, note, barcode, created_at
            FROM skus 
            ORDER BY id DESC 
            LIMIT 10
        ''')
        return cur.fetchall()
    finally:
        cur.close()

# ======== PyQt6 GUI ========

PYQT_APP_TEXT = "Asian Supermarket SKU Manager"

if QtWidgets is not None:
    class MainWindow(QtWidgets.QWidget):
        def __init__(self, db_path: str = DB_FILENAME):
            super().__init__()
            self.db_path = db_path
            self.conn = None
            try:
                self.conn = get_connection(self.db_path)
                initialize_db(self.conn)
            except Exception as e:
                print(f"Error initializing database: {e}")
                QtWidgets.QMessageBox.critical(self, "Database Error", f"Failed to initialize database: {e}")
                # Try to continue with a None connection - operations will check for it
            self.setWindowTitle(PYQT_APP_TEXT)
            self.setMinimumSize(800, 480)
            self.layout = QtWidgets.QVBoxLayout(self)

            form = QtWidgets.QFormLayout()

            # Category
            self.category_cb = QtWidgets.QComboBox()
            for code, info in sorted(CATEGORY_MAP.items()):
                display = f"{code} - {info['name']}"
                self.category_cb.addItem(display, code)
            self.category_cb.currentIndexChanged.connect(self.update_subcategories)
            form.addRow('Category', self.category_cb)

            # Subcategory
            self.subcategory_cb = QtWidgets.QComboBox()
            form.addRow('Subcategory', self.subcategory_cb)

            # Brand (3-digit codes)
            self.brand_cb = QtWidgets.QComboBox()
            for code, name in sorted(BRAND_MAP.items()):
                self.brand_cb.addItem(f"{code} - {name}", code)
            form.addRow('Brand', self.brand_cb)

            # Quantity
            self.quantity_cb = QtWidgets.QComboBox()
            for qcode, qlabel in sorted(QUANTITY_MAP.items()):
                self.quantity_cb.addItem(f"{qcode} - {qlabel}", qcode)
            form.addRow('Quantity', self.quantity_cb)

            # Product name
            self.product_le = QtWidgets.QLineEdit()
            self.product_le.textEdited.connect(self.update_slug_preview)
            form.addRow('Product name', self.product_le)

            # Slug (read-only)
            self.slug_le = QtWidgets.QLineEdit()
            self.slug_le.setReadOnly(True)
            form.addRow('Slug (auto)', self.slug_le)

            # Country
            self.country_le = QtWidgets.QLineEdit()
            self.country_le.setPlaceholderText('Optional country code (e.g. KR, JP)')
            form.addRow('Country', self.country_le)

            # Note / Barcode
            self.note_le = QtWidgets.QLineEdit()
            form.addRow('Note', self.note_le)
            self.barcode_le = QtWidgets.QLineEdit()
            form.addRow('Barcode', self.barcode_le)

            # Buttons
            btn_layout = QtWidgets.QHBoxLayout()
            self.preview_btn = QtWidgets.QPushButton('Preview SKU')
            self.preview_btn.clicked.connect(self.preview_sku)
            btn_layout.addWidget(self.preview_btn)

            self.save_btn = QtWidgets.QPushButton('Save SKU to DB')
            self.save_btn.clicked.connect(self.save_sku)
            btn_layout.addWidget(self.save_btn)

            self.export_btn = QtWidgets.QPushButton('Export CSV')
            self.export_btn.clicked.connect(self.export_csv)
            btn_layout.addWidget(self.export_btn)

            self.template_btn = QtWidgets.QPushButton('Create Spreadsheet Template')
            self.template_btn.clicked.connect(self.create_template_file)
            btn_layout.addWidget(self.template_btn)

            # Additional buttons for view, edit, and log
            btn_layout2 = QtWidgets.QHBoxLayout()
            self.view_btn = QtWidgets.QPushButton('View Entries')
            self.view_btn.clicked.connect(self.view_entries)
            btn_layout2.addWidget(self.view_btn)

            self.edit_btn = QtWidgets.QPushButton('Edit Entries')
            self.edit_btn.clicked.connect(self.edit_entries)
            btn_layout2.addWidget(self.edit_btn)

            self.log_btn = QtWidgets.QPushButton('Generate Log (Last 10)')
            self.log_btn.clicked.connect(self.generate_log)
            btn_layout2.addWidget(self.log_btn)

            # Output area
            self.output = QtWidgets.QTextEdit()
            self.output.setReadOnly(True)
            self.output.setMinimumHeight(180)

            self.layout.addLayout(form)
            self.layout.addLayout(btn_layout)
            self.layout.addLayout(btn_layout2)
            self.layout.addWidget(self.output)

            # initialize subcategories for the first category
            self.update_subcategories()

        def closeEvent(self, event):
            """Handle window close event - properly close database connection"""
            try:
                if hasattr(self, 'conn') and self.conn:
                    self.conn.close()
                    print("Database connection closed")
            except Exception as e:
                print(f"Error closing database: {e}")
            event.accept()

        def __del__(self):
            """Clean up database connection when object is destroyed"""
            try:
                if hasattr(self, 'conn') and self.conn:
                    self.conn.close()
                    print("Database connection closed in destructor")
            except Exception as e:
                print(f"Error closing database in destructor: {e}")

        def update_subcategories(self):
            self.subcategory_cb.clear()
            category_code = self.category_cb.currentData()
            if category_code is None:
                return
            subs = CATEGORY_MAP.get(category_code, {}).get('subcategories', {})
            # subs is dict of '1': 'Noodle' etc.
            for code, name in sorted(subs.items(), key=lambda x: int(x[0])):
                self.subcategory_cb.addItem(f"{code} - {name}", code)

        def peek_next_sequence(self, brand_code: str, category_code: str, subcategory_code: str, quantity_code: str) -> int:
            try:
                if not hasattr(self, 'conn') or self.conn is None:
                    return 1
                cur = self.conn.cursor()
                try:
                    cur.execute('SELECT counter FROM counters WHERE brand_code=? AND category_code=? AND subcategory_code=? AND quantity_code=?',
                                (brand_code.zfill(3), category_code.zfill(2), subcategory_code, quantity_code))
                    row = cur.fetchone()
                    return (row['counter'] + 1) if row is not None else 1
                finally:
                    cur.close()
            except Exception as e:
                print(f"Error in peek_next_sequence: {e}")
                return 1

        def update_slug_preview(self, text: str = None):
            # Accept the text argument from the signal (PyQt6 provides it),
            # but also allow calling without args.
            name = text if text is not None else self.product_le.text().strip()
            name = name.strip() if isinstance(name, str) else ''
            slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in name).strip('-')
            # Prevent any recursive signals / side effects when updating the slug field
            try:
                self.slug_le.blockSignals(True)
                self.slug_le.setText(slug)
            finally:
                self.slug_le.blockSignals(False)

        def preview_sku(self):
            try:
                brand_code = self.brand_cb.currentData() or '000'
                category_code = self.category_cb.currentData() or '00'
                subcategory_code = self.subcategory_cb.currentData() or '0'
                quantity_code = self.quantity_cb.currentData() or '0'
                product_name = self.product_le.text().strip() or 'UNNAMED'
                # peek sequence without committing
                next_seq = self.peek_next_sequence(brand_code, category_code, subcategory_code, quantity_code)
                product_seq = str(next_seq).zfill(2)
                human = format_human_sku(brand_code.zfill(3), category_code.zfill(2), subcategory_code, quantity_code, product_seq)
                numeric = format_numeric_sku(brand_code.zfill(3), category_code.zfill(2), subcategory_code, quantity_code, product_seq)
                self.output.append(f"Preview: Human SKU: {human} | Numeric SKU: {numeric} | Name: {product_name}")
            except Exception as e:
                self.output.append(f"Error previewing SKU: {e}")
                print(f"Error in preview_sku: {e}")

        def save_sku(self):
            try:
                brand_code = self.brand_cb.currentData() or '000'
                category_code = self.category_cb.currentData() or '00'
                subcategory_code = self.subcategory_cb.currentData() or '0'
                quantity_code = self.quantity_cb.currentData() or '0'
                product_name = self.product_le.text().strip() or 'UNNAMED'
                country_code = self.country_le.text().strip().upper() or None
                note = self.note_le.text().strip() or None
                barcode = self.barcode_le.text().strip() or None
                
                if not hasattr(self, 'conn') or self.conn is None:
                    self.output.append("Error: Database connection is not available")
                    return
                
                human, numeric = create_sku_record(self.conn, brand_code, category_code, subcategory_code, quantity_code, product_name, country_code, note, barcode)
                self.output.append(f"Saved SKU: {human}  (numeric: {numeric}) | Name: {product_name}")
            except sqlite3.IntegrityError as e:
                self.output.append(f"Error saving SKU: Integrity error - {e}")
                print(f"IntegrityError in save_sku: {e}")
            except Exception as e:
                self.output.append(f"Error saving SKU: {e}")
                print(f"Error in save_sku: {e}")

        def export_csv(self):
            try:
                path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save SKU CSV', os.path.expanduser('~/skus_export.csv'), 'CSV Files (*.csv)')
                if not path:
                    return
                if not hasattr(self, 'conn') or self.conn is None:
                    self.output.append("Error: Database connection is not available")
                    return
                out = export_skus_to_csv(self.conn, path)
                self.output.append(f"Exported SKUs to: {out}")
            except Exception as e:
                self.output.append(f"Error exporting CSV: {e}")
                print(f"Error in export_csv: {e}")

        def create_template_file(self):
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Create Template CSV', os.path.expanduser('~/sku_template.csv'), 'CSV Files (*.csv)')
            if not path:
                return
            out = create_spreadsheet_template(path)
            self.output.append(f"Created spreadsheet template at: {out}")

        def view_entries(self):
            """Open a dialog to view all SKU entries"""
            if not hasattr(self, 'conn') or self.conn is None:
                QtWidgets.QMessageBox.warning(self, "Database Error", "Database connection is not available")
                return
            
            try:
                entries = list_skus(self.conn, limit=1000)
                if not entries:
                    QtWidgets.QMessageBox.information(self, "No Entries", "No SKU entries found in database.")
                    return
                
                # Create dialog window
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("View SKU Entries")
                dialog.setMinimumSize(800, 600)
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # Create table
                table = QtWidgets.QTableWidget()
                table.setColumnCount(7)
                table.setHorizontalHeaderLabels(["ID", "Human SKU", "Numeric SKU", "Slug Name", "Product Name", "Barcode", "Created At"])
                table.setRowCount(len(entries))
                
                for row_idx, entry in enumerate(entries):
                    table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(entry['id'])))
                    table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(entry['human_sku']))
                    table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(entry['numeric_sku']))
                    table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(entry['product_slug'] or ''))
                    table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(entry['full_product_name'] or ''))
                    table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(entry['barcode'] or ''))
                    table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(entry['created_at']))
                
                table.resizeColumnsToContents()
                layout.addWidget(table)
                
                # Close button
                close_btn = QtWidgets.QPushButton("Close")
                close_btn.clicked.connect(dialog.accept)
                layout.addWidget(close_btn)
                
                dialog.exec()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error viewing entries: {e}")
                print(f"Error in view_entries: {e}")

        def edit_entries(self):
            """Open a dialog to edit/delete SKU entries"""
            if not hasattr(self, 'conn') or self.conn is None:
                QtWidgets.QMessageBox.warning(self, "Database Error", "Database connection is not available")
                return
            
            try:
                entries = list_skus(self.conn, limit=1000)
                if not entries:
                    QtWidgets.QMessageBox.information(self, "No Entries", "No SKU entries found in database.")
                    return
                
                # Create dialog window
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("Edit/Delete SKU Entries")
                dialog.setMinimumSize(900, 700)
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # Create table
                table = QtWidgets.QTableWidget()
                table.setColumnCount(7)
                table.setHorizontalHeaderLabels(["ID", "Human SKU", "Numeric SKU", "Slug Name", "Product Name", "Barcode", "Created At"])
                table.setRowCount(len(entries))
                table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
                table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
                
                for row_idx, entry in enumerate(entries):
                    table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(entry['id'])))
                    table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(entry['human_sku']))
                    table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(entry['numeric_sku']))
                    table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(entry['product_slug'] or ''))
                    table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(entry['full_product_name'] or ''))
                    table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(entry['barcode'] or ''))
                    table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(entry['created_at']))
                
                table.resizeColumnsToContents()
                layout.addWidget(table)
                
                # Buttons layout
                btn_layout = QtWidgets.QHBoxLayout()
                
                edit_btn = QtWidgets.QPushButton("Edit Selected")
                edit_btn.clicked.connect(lambda: self.edit_selected_entry(dialog, table))
                btn_layout.addWidget(edit_btn)
                
                delete_btn = QtWidgets.QPushButton("Delete Selected")
                delete_btn.clicked.connect(lambda: self.delete_selected_entry(dialog, table))
                btn_layout.addWidget(delete_btn)
                
                close_btn = QtWidgets.QPushButton("Close")
                close_btn.clicked.connect(dialog.accept)
                btn_layout.addWidget(close_btn)
                
                layout.addLayout(btn_layout)
                dialog.exec()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error opening edit dialog: {e}")
                print(f"Error in edit_entries: {e}")

        def edit_selected_entry(self, parent_dialog, table):
            """Edit the selected entry"""
            current_row = table.currentRow()
            if current_row < 0:
                QtWidgets.QMessageBox.warning(parent_dialog, "No Selection", "Please select an entry to edit.")
                return
            
            try:
                sku_id = int(table.item(current_row, 0).text())
                sku_data = get_sku_by_id(self.conn, sku_id)
                
                if not sku_data:
                    QtWidgets.QMessageBox.warning(parent_dialog, "Not Found", f"SKU with ID {sku_id} not found.")
                    return
                
                # Create edit dialog
                edit_dialog = QtWidgets.QDialog(parent_dialog)
                edit_dialog.setWindowTitle(f"Edit SKU - {sku_data['human_sku']}")
                edit_dialog.setMinimumSize(500, 600)
                layout = QtWidgets.QVBoxLayout(edit_dialog)
                
                form = QtWidgets.QFormLayout()
                
                # Category
                category_cb = QtWidgets.QComboBox()
                for code, info in sorted(CATEGORY_MAP.items()):
                    display = f"{code} - {info['name']}"
                    category_cb.addItem(display, code)
                    if code == sku_data['category_code']:
                        category_cb.setCurrentIndex(category_cb.count() - 1)
                form.addRow('Category', category_cb)
                
                # Subcategory
                subcategory_cb = QtWidgets.QComboBox()
                def update_subcats():
                    subcategory_cb.clear()
                    cat_code = category_cb.currentData()
                    if cat_code:
                        subs = CATEGORY_MAP.get(cat_code, {}).get('subcategories', {})
                        for code, name in sorted(subs.items(), key=lambda x: int(x[0])):
                            subcategory_cb.addItem(f"{code} - {name}", code)
                            if code == sku_data['subcategory_code']:
                                subcategory_cb.setCurrentIndex(subcategory_cb.count() - 1)
                category_cb.currentIndexChanged.connect(update_subcats)
                update_subcats()
                form.addRow('Subcategory', subcategory_cb)
                
                # Brand
                brand_cb = QtWidgets.QComboBox()
                for code, name in sorted(BRAND_MAP.items()):
                    brand_cb.addItem(f"{code} - {name}", code)
                    if code == sku_data['brand_code']:
                        brand_cb.setCurrentIndex(brand_cb.count() - 1)
                form.addRow('Brand', brand_cb)
                
                # Quantity
                quantity_cb = QtWidgets.QComboBox()
                for qcode, qlabel in sorted(QUANTITY_MAP.items()):
                    quantity_cb.addItem(f"{qcode} - {qlabel}", qcode)
                    if qcode == sku_data['quantity_code']:
                        quantity_cb.setCurrentIndex(quantity_cb.count() - 1)
                form.addRow('Quantity', quantity_cb)
                
                # Product name
                product_le = QtWidgets.QLineEdit()
                product_le.setText(sku_data['full_product_name'] or '')
                form.addRow('Product name', product_le)
                
                # Country
                country_le = QtWidgets.QLineEdit()
                country_le.setText(sku_data['country_code'] or '')
                form.addRow('Country', country_le)
                
                # Note
                note_le = QtWidgets.QLineEdit()
                note_le.setText(sku_data['note'] or '')
                form.addRow('Note', note_le)
                
                # Barcode
                barcode_le = QtWidgets.QLineEdit()
                barcode_le.setText(sku_data['barcode'] or '')
                form.addRow('Barcode', barcode_le)
                
                layout.addLayout(form)
                
                # Buttons
                btn_layout = QtWidgets.QHBoxLayout()
                save_btn = QtWidgets.QPushButton("Save")
                save_btn.clicked.connect(lambda: self.save_edited_entry(edit_dialog, sku_id, brand_cb, category_cb, subcategory_cb, quantity_cb, product_le, country_le, note_le, barcode_le))
                btn_layout.addWidget(save_btn)
                
                cancel_btn = QtWidgets.QPushButton("Cancel")
                cancel_btn.clicked.connect(edit_dialog.reject)
                btn_layout.addWidget(cancel_btn)
                
                layout.addLayout(btn_layout)
                edit_dialog.exec()
            except Exception as e:
                QtWidgets.QMessageBox.critical(parent_dialog, "Error", f"Error editing entry: {e}")
                print(f"Error in edit_selected_entry: {e}")

        def save_edited_entry(self, dialog, sku_id, brand_cb, category_cb, subcategory_cb, quantity_cb, product_le, country_le, note_le, barcode_le):
            """Save the edited entry"""
            try:
                brand_code = brand_cb.currentData() or '000'
                category_code = category_cb.currentData() or '00'
                subcategory_code = subcategory_cb.currentData() or '0'
                quantity_code = quantity_cb.currentData() or '0'
                product_name = product_le.text().strip() or 'UNNAMED'
                country_code = country_le.text().strip().upper() or None
                note = note_le.text().strip() or None
                barcode = barcode_le.text().strip() or None
                
                human, numeric = update_sku_record(self.conn, sku_id, brand_code, category_code, subcategory_code, quantity_code, product_name, country_code, note, barcode)
                QtWidgets.QMessageBox.information(dialog, "Success", f"SKU updated successfully:\n{human} (numeric: {numeric})")
                self.output.append(f"Updated SKU: {human} (numeric: {numeric}) | Name: {product_name}")
                dialog.accept()
            except Exception as e:
                QtWidgets.QMessageBox.critical(dialog, "Error", f"Error saving entry: {e}")
                print(f"Error in save_edited_entry: {e}")

        def delete_selected_entry(self, parent_dialog, table):
            """Delete the selected entry"""
            current_row = table.currentRow()
            if current_row < 0:
                QtWidgets.QMessageBox.warning(parent_dialog, "No Selection", "Please select an entry to delete.")
                return
            
            try:
                sku_id = int(table.item(current_row, 0).text())
                sku_name = table.item(current_row, 4).text()
                
                reply = QtWidgets.QMessageBox.question(
                    parent_dialog, "Confirm Delete",
                    f"Are you sure you want to delete SKU:\n{sku_name} (ID: {sku_id})?",
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                )
                
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    if delete_sku_record(self.conn, sku_id):
                        QtWidgets.QMessageBox.information(parent_dialog, "Success", "SKU deleted successfully.")
                        self.output.append(f"Deleted SKU: {sku_name} (ID: {sku_id})")
                        # Refresh the table
                        parent_dialog.accept()
                        self.edit_entries()  # Reopen to refresh
                    else:
                        QtWidgets.QMessageBox.warning(parent_dialog, "Error", "Failed to delete SKU.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(parent_dialog, "Error", f"Error deleting entry: {e}")
                print(f"Error in delete_selected_entry: {e}")

        def generate_log(self):
            """Generate a log of the last 10 entries"""
            if not hasattr(self, 'conn') or self.conn is None:
                QtWidgets.QMessageBox.warning(self, "Database Error", "Database connection is not available")
                return
            
            try:
                entries = get_last_ten_entries(self.conn)
                if not entries:
                    QtWidgets.QMessageBox.information(self, "No Entries", "No SKU entries found in database.")
                    return
                
                # Generate log text
                log_text = "=" * 80 + "\n"
                log_text += "LAST 10 SKU ENTRIES LOG\n"
                log_text += f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                log_text += "=" * 80 + "\n\n"
                
                for idx, entry in enumerate(entries, 1):
                    log_text += f"Entry #{idx}:\n"
                    log_text += f"  ID: {entry['id']}\n"
                    log_text += f"  Human SKU: {entry['human_sku']}\n"
                    log_text += f"  Numeric SKU: {entry['numeric_sku']}\n"
                    log_text += f"  Brand Code: {entry['brand_code']}\n"
                    log_text += f"  Category Code: {entry['category_code']}\n"
                    log_text += f"  Subcategory Code: {entry['subcategory_code']}\n"
                    log_text += f"  Quantity Code: {entry['quantity_code']}\n"
                    log_text += f"  Product Seq: {entry['product_seq']}\n"
                    log_text += f"  Product Name: {entry['full_product_name']}\n"
                    if entry['country_code']:
                        log_text += f"  Country: {entry['country_code']}\n"
                    if entry['note']:
                        log_text += f"  Note: {entry['note']}\n"
                    if entry['barcode']:
                        log_text += f"  Barcode: {entry['barcode']}\n"
                    log_text += f"  Created At: {entry['created_at']}\n"
                    log_text += "-" * 80 + "\n\n"
                
                # Display in output area
                self.output.clear()
                self.output.append(log_text)
                
                # Also offer to save to file
                reply = QtWidgets.QMessageBox.question(
                    self, "Log Generated",
                    "Log generated successfully. Would you like to save it to a file?",
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                )
                
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    path, _ = QtWidgets.QFileDialog.getSaveFileName(
                        self, 'Save Log File', 
                        os.path.expanduser(f'~/sku_log_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'),
                        'Text Files (*.txt);;All Files (*)'
                    )
                    if path:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(log_text)
                        QtWidgets.QMessageBox.information(self, "Success", f"Log saved to:\n{path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error generating log: {e}")
                print(f"Error in generate_log: {e}")


# ======== Main entry (CLI or GUI) ========

def main():
    conn = initialize_db()
    print('DB initialized at', DB_FILENAME)
    if QtWidgets is None:
        print('PyQt6 not available. Use the programmatic API: create_sku_record, export_skus_to_csv, create_spreadsheet_template')
        return
    app = QtWidgets.QApplication([])
    w = MainWindow()
    w.show()
    app.exec()


if __name__ == '__main__':
    main()
