"""Settings Page.

Application settings page with data source, appearance, and column visibility.
Implements Requirements 5.1, 5.2, 5.3, 5.4, 5.5.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, List, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QPushButton,
    QCheckBox,
    QScrollArea,
    QFrame,
    QColorDialog,
    QListWidget,
    QAbstractItemView,
    QInputDialog,
    QMessageBox,
)

from app.storage.storage import IStorageService


@dataclass
class AppSettings:
    """Application settings model."""
    data_source: str = "auto"  # "auto", "binance-ws", "binance", "coingecko", "coinbase"
    theme_mode: str = "dark"  # "dark", "light"
    accent_color: str = "#0A84FF"  # hex color
    visible_columns: List[str] = None  # List of visible column names
    minimize_to_tray: bool = True
    
    def __post_init__(self):
        if self.visible_columns is None:
            self.visible_columns = [
                "Last", "Bid", "Ask", "24h %", 
                "24h High", "24h Low", "24h Vol", "Turnover", "Time"
            ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        """Create from dictionary."""
        return cls(
            data_source=data.get("data_source", "auto"),
            theme_mode=data.get("theme_mode", "dark"),
            accent_color=data.get("accent_color", "#0A84FF"),
            visible_columns=data.get("visible_columns"),
            minimize_to_tray=data.get("minimize_to_tray", True),
        )


SETTINGS_STORAGE_KEY = "app_settings"
SYMBOLS_STORAGE_KEY = "tracked_symbols"
DEFAULT_TRACKED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

# Column names for visibility toggles
COLUMN_NAMES = [
    "Last", "Bid", "Ask", "24h %", 
    "24h High", "24h Low", "24h Vol", "Turnover", "Time"
]

# Data source options
DATA_SOURCES = [
    ("auto", "Auto (WS→REST)"),
    ("binance-ws", "Binance WebSocket"),
    ("binance", "Binance REST"),
    ("coingecko", "CoinGecko REST"),
    ("coinbase", "Coinbase REST"),
]


class SettingsPage(QWidget):
    """Application settings page.
    
    Provides UI for configuring data source, appearance, and column visibility.
    Changes are applied immediately and persisted to storage.
    
    Signals:
        settingChanged: Emitted when any setting changes (key, value)
        themeChanged: Emitted when theme mode changes
        accentColorChanged: Emitted when accent color changes
        dataSourceChanged: Emitted when data source changes
        columnVisibilityChanged: Emitted when column visibility changes
    """
    
    settingChanged = Signal(str, object)  # key, value
    themeChanged = Signal(str)  # "dark" or "light"
    accentColorChanged = Signal(QColor)
    dataSourceChanged = Signal(str)
    columnVisibilityChanged = Signal(str, bool)  # column_name, visible
    symbolsChanged = Signal(list)  # List[str]
    
    def __init__(
        self,
        storage: Optional[IStorageService] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the settings page.
        
        Args:
            storage: Storage service for persisting settings
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._storage = storage
        self._settings = AppSettings()
        self._column_checkboxes: dict[str, QCheckBox] = {}
        self._tracked_symbols: List[str] = []
        
        self._load_settings()
        self._load_tracked_symbols()
        self._setup_ui()
        self._apply_settings_to_ui()
    
    def _setup_ui(self) -> None:
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        
        # Data Source section
        data_source_group = self._create_data_source_section()
        scroll_layout.addWidget(data_source_group)

        # Tracked symbols section
        symbols_group = self._create_symbols_section()
        scroll_layout.addWidget(symbols_group)
        
        # Appearance section
        appearance_group = self._create_appearance_section()
        scroll_layout.addWidget(appearance_group)
        
        # Column Visibility section
        columns_group = self._create_columns_section()
        scroll_layout.addWidget(columns_group)
        
        # Behavior section
        behavior_group = self._create_behavior_section()
        scroll_layout.addWidget(behavior_group)
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
    
    def _create_data_source_section(self) -> QGroupBox:
        """Create the data source configuration section."""
        group = QGroupBox("Data Source")
        layout = QVBoxLayout(group)
        
        desc = QLabel("Select the data source for cryptocurrency prices.")
        desc.setStyleSheet("color: #888;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source:"))
        
        self._source_combo = QComboBox()
        for value, label in DATA_SOURCES:
            self._source_combo.addItem(label, value)
        self._source_combo.currentIndexChanged.connect(self._on_data_source_changed)
        source_layout.addWidget(self._source_combo, 1)
        
        layout.addLayout(source_layout)
        
        return group

    def _create_symbols_section(self) -> QGroupBox:
        """Create the tracked symbols section."""
        group = QGroupBox("Tracked Symbols")
        layout = QVBoxLayout(group)

        desc = QLabel("Add/remove symbols shown in Market Overview and Chart (e.g., BTCUSDT).")
        desc.setStyleSheet("color: #888;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._symbols_list = QListWidget()
        self._symbols_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self._symbols_list)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton("Add...")
        add_btn.clicked.connect(self._on_add_symbol)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._on_remove_selected_symbols)
        btn_layout.addWidget(remove_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._refresh_symbols_list()
        return group
    
    def _create_appearance_section(self) -> QGroupBox:
        """Create the appearance settings section."""
        group = QGroupBox("Appearance")
        layout = QVBoxLayout(group)
        
        # Theme mode
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Dark", "dark")
        self._theme_combo.addItem("Light", "light")
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self._theme_combo, 1)
        
        layout.addLayout(theme_layout)
        
        # Accent color
        accent_layout = QHBoxLayout()
        accent_layout.addWidget(QLabel("Accent Color:"))
        
        self._accent_preview = QFrame()
        self._accent_preview.setFixedSize(32, 32)
        self._accent_preview.setStyleSheet(
            f"background-color: {self._settings.accent_color}; border-radius: 4px;"
        )
        accent_layout.addWidget(self._accent_preview)
        
        accent_btn = QPushButton("Choose...")
        accent_btn.clicked.connect(self._on_choose_accent)
        accent_layout.addWidget(accent_btn)
        accent_layout.addStretch()
        
        layout.addLayout(accent_layout)
        
        return group
    
    def _create_columns_section(self) -> QGroupBox:
        """Create the column visibility section."""
        group = QGroupBox("Column Visibility")
        layout = QVBoxLayout(group)
        
        desc = QLabel("Select which columns to display in the price table.")
        desc.setStyleSheet("color: #888;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Create checkboxes for each column
        for col_name in COLUMN_NAMES:
            cb = QCheckBox(col_name)
            cb.setChecked(col_name in self._settings.visible_columns)
            cb.toggled.connect(lambda checked, name=col_name: self._on_column_toggled(name, checked))
            self._column_checkboxes[col_name] = cb
            layout.addWidget(cb)
        
        # Select/Deselect all buttons
        btn_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_columns)
        btn_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all_columns)
        btn_layout.addWidget(deselect_all_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _create_behavior_section(self) -> QGroupBox:
        """Create the behavior settings section."""
        group = QGroupBox("Behavior")
        layout = QVBoxLayout(group)
        
        self._tray_checkbox = QCheckBox("Minimize to system tray on close")
        self._tray_checkbox.setChecked(self._settings.minimize_to_tray)
        self._tray_checkbox.toggled.connect(self._on_tray_toggled)
        layout.addWidget(self._tray_checkbox)
        
        return group
    
    def _apply_settings_to_ui(self) -> None:
        """Apply current settings to UI controls."""
        # Data source
        for i in range(self._source_combo.count()):
            if self._source_combo.itemData(i) == self._settings.data_source:
                self._source_combo.setCurrentIndex(i)
                break
        
        # Theme
        for i in range(self._theme_combo.count()):
            if self._theme_combo.itemData(i) == self._settings.theme_mode:
                self._theme_combo.setCurrentIndex(i)
                break
        
        # Accent color
        self._accent_preview.setStyleSheet(
            f"background-color: {self._settings.accent_color}; border-radius: 4px;"
        )
        
        # Column visibility
        for col_name, cb in self._column_checkboxes.items():
            cb.setChecked(col_name in self._settings.visible_columns)
        
        # Tray behavior
        self._tray_checkbox.setChecked(self._settings.minimize_to_tray)
    
    def _on_data_source_changed(self, index: int) -> None:
        """Handle data source change."""
        value = self._source_combo.itemData(index)
        if value != self._settings.data_source:
            self._settings.data_source = value
            self._save_settings()
            self.settingChanged.emit("data_source", value)
            self.dataSourceChanged.emit(value)
    
    def _on_theme_changed(self, index: int) -> None:
        """Handle theme change."""
        value = self._theme_combo.itemData(index)
        if value != self._settings.theme_mode:
            self._settings.theme_mode = value
            self._save_settings()
            self.settingChanged.emit("theme_mode", value)
            self.themeChanged.emit(value)
    
    def _on_choose_accent(self) -> None:
        """Handle accent color selection."""
        current = QColor(self._settings.accent_color)
        color = QColorDialog.getColor(current, self, "Choose Accent Color")
        
        if color.isValid():
            hex_color = color.name()
            self._settings.accent_color = hex_color
            self._accent_preview.setStyleSheet(
                f"background-color: {hex_color}; border-radius: 4px;"
            )
            self._save_settings()
            self.settingChanged.emit("accent_color", hex_color)
            self.accentColorChanged.emit(color)
    
    def _on_column_toggled(self, column_name: str, checked: bool) -> None:
        """Handle column visibility toggle."""
        if checked:
            if column_name not in self._settings.visible_columns:
                self._settings.visible_columns.append(column_name)
        else:
            if column_name in self._settings.visible_columns:
                self._settings.visible_columns.remove(column_name)
        
        self._save_settings()
        self.settingChanged.emit("visible_columns", self._settings.visible_columns)
        self.columnVisibilityChanged.emit(column_name, checked)
    
    def _select_all_columns(self) -> None:
        """Select all columns."""
        for cb in self._column_checkboxes.values():
            cb.setChecked(True)
    
    def _deselect_all_columns(self) -> None:
        """Deselect all columns."""
        for cb in self._column_checkboxes.values():
            cb.setChecked(False)
    
    def _on_tray_toggled(self, checked: bool) -> None:
        """Handle tray behavior toggle."""
        self._settings.minimize_to_tray = checked
        self._save_settings()
        self.settingChanged.emit("minimize_to_tray", checked)
    
    def _load_settings(self) -> None:
        """Load settings from storage."""
        if self._storage:
            data = self._storage.load(SETTINGS_STORAGE_KEY)
            if data:
                self._settings = AppSettings.from_dict(data)

    def _normalize_symbol(self, s: str) -> str:
        return s.replace("/", "").replace("-", "").replace(" ", "").upper()

    def _load_tracked_symbols(self) -> None:
        """Load tracked symbols from storage."""
        symbols: List[str] = []
        if self._storage:
            data = self._storage.load(SYMBOLS_STORAGE_KEY)
            if isinstance(data, list):
                symbols = [self._normalize_symbol(x) for x in data if isinstance(x, str)]

        if not symbols:
            symbols = DEFAULT_TRACKED_SYMBOLS.copy()
            if self._storage:
                self._storage.save(SYMBOLS_STORAGE_KEY, symbols)

        # De-dupe while preserving order
        seen: set[str] = set()
        cleaned: List[str] = []
        for sym in symbols:
            if sym and sym not in seen:
                seen.add(sym)
                cleaned.append(sym)
        self._tracked_symbols = cleaned

    def _save_tracked_symbols(self) -> None:
        if self._storage:
            self._storage.save(SYMBOLS_STORAGE_KEY, self._tracked_symbols)

    def _refresh_symbols_list(self) -> None:
        if not hasattr(self, "_symbols_list"):
            return
        self._symbols_list.clear()
        for sym in self._tracked_symbols:
            self._symbols_list.addItem(sym)

    def _emit_symbols_changed(self) -> None:
        self.symbolsChanged.emit(self._tracked_symbols.copy())

    def _on_add_symbol(self) -> None:
        """Add a symbol to the tracked list."""
        text, ok = QInputDialog.getText(self, "Add Symbol", "Symbol (e.g., BTCUSDT):")
        if not ok:
            return

        sym = self._normalize_symbol(text.strip())
        if not sym:
            return

        if sym in self._tracked_symbols:
            return

        self._tracked_symbols.append(sym)
        self._save_tracked_symbols()
        self._refresh_symbols_list()
        self._emit_symbols_changed()

    def _on_remove_selected_symbols(self) -> None:
        """Remove selected symbols from the tracked list."""
        if not hasattr(self, "_symbols_list"):
            return

        selected = [i.text() for i in self._symbols_list.selectedItems()]
        if not selected:
            return

        remaining = [s for s in self._tracked_symbols if s not in set(selected)]
        if not remaining:
            QMessageBox.warning(self, "Tracked Symbols", "At least one symbol must remain.")
            return

        self._tracked_symbols = remaining
        self._save_tracked_symbols()
        self._refresh_symbols_list()
        self._emit_symbols_changed()

    def _save_settings(self) -> None:
        """Save settings to storage."""
        if self._storage:
            self._storage.save(SETTINGS_STORAGE_KEY, self._settings.to_dict())
    
    def get_setting(self, key: str) -> Any:
        """Get a setting value.
        
        Args:
            key: Setting key name
            
        Returns:
            The setting value
        """
        return getattr(self._settings, key, None)
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value.
        
        Args:
            key: Setting key name
            value: Setting value
        """
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)
            self._save_settings()
            self._apply_settings_to_ui()
            self.settingChanged.emit(key, value)
    
    def get_settings(self) -> AppSettings:
        """Get the current settings object.
        
        Returns:
            The current AppSettings instance
        """
        return self._settings
    
    def set_storage(self, storage: IStorageService) -> None:
        """Set the storage service.
        
        Args:
            storage: Storage service for persisting settings
        """
        self._storage = storage
        self._load_settings()
        self._load_tracked_symbols()
        self._apply_settings_to_ui()
        self._refresh_symbols_list()
    
    def on_container_width_changed(self, width: int) -> None:
        """Handle container width changes for responsive layout.
        
        Implements Requirements 7.3, 7.4: Adjust layout based on available width.
        
        Args:
            width: The new available width in pixels
        """
        # Settings page is mostly vertical, so minimal adjustments needed
        # Just ensure the scroll area uses full width efficiently
        pass
