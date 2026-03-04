def make_style(dark: bool) -> str:
    if dark:
        return """
        QMainWindow, QWidget#root { background: #0F172A; }
        QScrollArea { background: transparent; border: none; }
        QScrollArea > QWidget > QWidget { background: transparent; }
        QWidget { color: #F1F5F9; }
        QFrame#card { background: #1E293B; border-radius: 12px; border: 1px solid #334155; }
        QLabel#sectionLabel { color: #3B82F6; font-size: 13px; font-weight: bold; }
        QLabel#hint  { color: #64748B; font-size: 11px; }
        QLabel#dim   { color: #94A3B8; }
        QPushButton#primary {
            background: #3B82F6; color: white; border-radius: 10px;
            font-size: 15px; font-weight: bold; padding: 14px 28px; border: none; }
        QPushButton#primary:hover    { background: #2563EB; }
        QPushButton#primary:disabled { background: #334155; color: #64748B; }
        QPushButton#danger {
            background: #EF4444; color: white; border-radius: 10px;
            font-size: 13px; font-weight: bold; padding: 14px 20px; border: none; }
        QPushButton#danger:hover { background: #DC2626; }
        QPushButton#secondary {
            background: #1E293B; color: #F1F5F9; border-radius: 8px;
            font-size: 11px; padding: 5px 14px; border: 1px solid #334155; }
        QPushButton#secondary:hover    { background: #334155; }
        QPushButton#secondary:disabled { color: #475569; }
        QPushButton#iconBtn {
            background: #334155; color: #F1F5F9; border-radius: 6px;
            font-size: 13px; padding: 3px 8px; border: none;
            min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; }
        QPushButton#iconBtn:hover { background: #EF4444; color: white; }
        QPushButton#stepper {
            background: #334155; color: #F1F5F9; border-radius: 6px;
            font-size: 15px; font-weight: bold; padding: 0px; border: none;
            min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; }
        QPushButton#stepper:hover { background: #3B82F6; }
        QPushButton#themeBtn {
            background: #1E293B; color: #F1F5F9; border-radius: 10px;
            font-size: 12px; font-weight: bold; padding: 8px 18px;
            border: 1px solid #334155; }
        QPushButton#themeBtn:hover { background: #3B82F6; border-color: #3B82F6; }
        QPushButton#saveBtn {
            background: #1E293B; color: #22C55E; border-radius: 10px;
            font-size: 11px; font-weight: bold; padding: 8px 14px;
            border: 1px solid #22C55E; }
        QPushButton#saveBtn:hover { background: #22C55E; color: white; }
        QPushButton#resetBtn {
            background: #1E293B; color: #94A3B8; border-radius: 10px;
            font-size: 11px; padding: 8px 14px; border: 1px solid #334155; }
        QPushButton#resetBtn:hover { background: #EF4444; color: white; border-color: #EF4444; }
        QPushButton#colorBtn {
            border-radius: 8px; font-size: 11px; font-weight: bold;
            padding: 5px 14px; border: 1px solid rgba(255,255,255,0.3); }
        QTextEdit {
            background: #0F172A; color: #F1F5F9; border-radius: 8px;
            border: 1px solid #334155; font-size: 12px; padding: 6px; }
        /* Slider image list — dark mode */
        QListWidget {
            background: #0F172A; color: #F1F5F9; border-radius: 8px;
            border: 1px solid #334155; font-size: 12px; padding: 4px;
            outline: none; }
        QListWidget::item {
            color: #F1F5F9; background: transparent;
            padding: 4px 6px; border-radius: 6px; }
        QListWidget::item:selected {
            background: #3B82F6; color: #FFFFFF; }
        QListWidget::item:hover:!selected {
            background: #1E293B; }
        QProgressBar {
            background: #0F172A; border-radius: 6px;
            border: 1px solid #334155; min-height: 14px; max-height: 14px; }
        QProgressBar::chunk { background: #3B82F6; border-radius: 6px; }
        QFrame#header    { background: #1E293B; border-bottom: 1px solid #334155; }
        QFrame#bottomBar { background: #1E293B; border-top:    1px solid #334155; }
        QLabel#pathLabel {
            background: #0F172A; color: #94A3B8; border-radius: 6px;
            border: 1px solid #334155; padding: 0 8px; }
        FontPickerWidget { background: #1E293B; border-radius: 12px; border: 1px solid #334155; }
        QComboBox {
            background: #0F172A; color: #F1F5F9; border-radius: 8px;
            border: 1px solid #334155; padding: 5px 10px; font-size: 11px; }
        QComboBox::drop-down { border: none; width: 20px; }
        QComboBox QAbstractItemView {
            background: #1E293B; color: #F1F5F9;
            selection-background-color: #3B82F6; border: 1px solid #334155; }
        QScrollBar:vertical {
            background: transparent; width: 6px;
            margin: 4px 2px 4px 0px; border-radius: 3px; }
        QScrollBar::handle:vertical {
            background: #334155; border-radius: 3px; min-height: 40px; }
        QScrollBar::handle:vertical:hover { background: #3B82F6; }
        QScrollBar::handle:vertical:pressed { background: #2563EB; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        QScrollBar:horizontal { height: 0px; }
        """
    else:
        return """
        QMainWindow, QWidget#root { background: #F8FAFC; }
        QScrollArea { background: transparent; border: none; }
        QScrollArea > QWidget > QWidget { background: transparent; }
        QWidget { color: #0F172A; }
        QFrame#card { background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; }
        QLabel#sectionLabel { color: #2563EB; font-size: 13px; font-weight: bold; }
        QLabel#hint  { color: #64748B; font-size: 11px; }
        QLabel#dim   { color: #64748B; }
        QPushButton#primary {
            background: #2563EB; color: white; border-radius: 10px;
            font-size: 15px; font-weight: bold; padding: 14px 28px; border: none; }
        QPushButton#primary:hover    { background: #1D4ED8; }
        QPushButton#primary:disabled { background: #CBD5E1; color: #94A3B8; }
        QPushButton#danger {
            background: #EF4444; color: white; border-radius: 10px;
            font-size: 13px; font-weight: bold; padding: 14px 20px; border: none; }
        QPushButton#danger:hover { background: #DC2626; }
        QPushButton#secondary {
            background: #F1F5F9; color: #0F172A; border-radius: 8px;
            font-size: 11px; padding: 5px 14px; border: 1px solid #CBD5E1; }
        QPushButton#secondary:hover    { background: #E2E8F0; }
        QPushButton#secondary:disabled { color: #94A3B8; }
        QPushButton#iconBtn {
            background: #E2E8F0; color: #0F172A; border-radius: 6px;
            font-size: 13px; padding: 3px 8px; border: none;
            min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; }
        QPushButton#iconBtn:hover { background: #EF4444; color: white; }
        QPushButton#stepper {
            background: #E2E8F0; color: #0F172A; border-radius: 6px;
            font-size: 15px; font-weight: bold; padding: 0px; border: none;
            min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; }
        QPushButton#stepper:hover { background: #2563EB; color: white; }
        QPushButton#themeBtn {
            background: #F1F5F9; color: #0F172A; border-radius: 10px;
            font-size: 12px; font-weight: bold; padding: 8px 18px;
            border: 1px solid #CBD5E1; }
        QPushButton#themeBtn:hover { background: #2563EB; color: white; border-color: #2563EB; }
        QPushButton#saveBtn {
            background: #F0FDF4; color: #16A34A; border-radius: 10px;
            font-size: 11px; font-weight: bold; padding: 8px 14px;
            border: 1px solid #16A34A; }
        QPushButton#saveBtn:hover { background: #16A34A; color: white; }
        QPushButton#resetBtn {
            background: #F1F5F9; color: #64748B; border-radius: 10px;
            font-size: 11px; padding: 8px 14px; border: 1px solid #CBD5E1; }
        QPushButton#resetBtn:hover { background: #EF4444; color: white; border-color: #EF4444; }
        QPushButton#colorBtn {
            border-radius: 8px; font-size: 11px; font-weight: bold;
            padding: 5px 14px; border: 1px solid rgba(0,0,0,0.2); }
        QTextEdit {
            background: #F1F5F9; color: #0F172A; border-radius: 8px;
            border: 1px solid #CBD5E1; font-size: 12px; padding: 6px; }
        /* Slider image list — light mode */
        QListWidget {
            background: #F1F5F9; color: #0F172A; border-radius: 8px;
            border: 1px solid #CBD5E1; font-size: 12px; padding: 4px;
            outline: none; }
        QListWidget::item {
            color: #0F172A; background: transparent;
            padding: 4px 6px; border-radius: 6px; }
        QListWidget::item:selected {
            background: #2563EB; color: #FFFFFF; }
        QListWidget::item:hover:!selected {
            background: #E2E8F0; }
        QProgressBar {
            background: #E2E8F0; border-radius: 6px;
            border: 1px solid #CBD5E1; min-height: 14px; max-height: 14px; }
        QProgressBar::chunk { background: #2563EB; border-radius: 6px; }
        QFrame#header    { background: #F1F5F9; border-bottom: 1px solid #E2E8F0; }
        QFrame#bottomBar { background: #F1F5F9; border-top:    1px solid #E2E8F0; }
        QLabel#pathLabel {
            background: #F1F5F9; color: #64748B; border-radius: 6px;
            border: 1px solid #E2E8F0; padding: 0 8px; }
        FontPickerWidget { background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; }
        QComboBox {
            background: #F8FAFC; color: #0F172A; border-radius: 8px;
            border: 1px solid #CBD5E1; padding: 5px 10px; font-size: 11px; }
        QComboBox::drop-down { border: none; width: 20px; }
        QComboBox QAbstractItemView {
            background: #FFFFFF; color: #0F172A;
            selection-background-color: #2563EB; selection-color: white;
            border: 1px solid #E2E8F0; }
        QScrollBar:vertical {
            background: transparent; width: 6px;
            margin: 4px 2px 4px 0px; border-radius: 3px; }
        QScrollBar::handle:vertical {
            background: #CBD5E1; border-radius: 3px; min-height: 40px; }
        QScrollBar::handle:vertical:hover { background: #2563EB; }
        QScrollBar::handle:vertical:pressed { background: #1D4ED8; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        QScrollBar:horizontal { height: 0px; }
        """