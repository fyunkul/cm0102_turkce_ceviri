# -*- coding: utf-8 -*-
"""CM0102 English/Turkish translation review editor with dark themes.
Works on CSV files and does not patch binary game files.
"""
import csv, os, re, shutil, datetime, tkinter as tk, json
from tkinter import ttk, filedialog, messagebox, simpledialog

HEAD = ['ID', 'English (Original)', 'Türkçe (Çeviri)', 'Durum']
TAG = re.compile(r'<\s*%[^>]*>|<ARG>')

THEMES = {
    'Okyanus Mavisi': {
        'bg': '#081728', 'surface': '#0c2138', 'surface2': '#102a46', 'surface3': '#123455',
        'fg': '#e8f3ff', 'muted': '#9db6cf', 'accent': '#19c2ff', 'accent2': '#00a4d6',
        'good': '#3ed17a', 'warn': '#ffc34d', 'bad': '#ff6b7a', 'border': '#1c4e79',
        'text_bg': '#07131f', 'select': '#11486f'
    },
    'Gece Laciverti': {
        'bg': '#0b1020', 'surface': '#141b2d', 'surface2': '#17233a', 'surface3': '#1d2b46',
        'fg': '#edf2ff', 'muted': '#9faeca', 'accent': '#6dc7ff', 'accent2': '#4caef5',
        'good': '#51d88a', 'warn': '#f4c15d', 'bad': '#ff7b88', 'border': '#2f4768',
        'text_bg': '#0b1220', 'select': '#22395a'
    },
    'Tam Siyah Pro': {
        'bg': '#080808', 'surface': '#111111', 'surface2': '#181818', 'surface3': '#202020',
        'fg': '#f2f2f2', 'muted': '#b0b0b0', 'accent': '#25c0ff', 'accent2': '#00a4d6',
        'good': '#4fd58d', 'warn': '#f2c15e', 'bad': '#ff6f7d', 'border': '#333333',
        'text_bg': '#0d0d0d', 'select': '#1e3641'
    }
}

class Editor:
    def __init__(self, root):
        self.root = root
        self.root.geometry('1580x980')
        self.root.minsize(1280, 800)
        self.root.title('CM 01/02 Çeviri Editörü')

        self.path = ''
        self.rows = []
        self.filtered = []
        self.selected = None
        self.dirty = False
        self.backup_count = 0
        self.backup_last = "Henüz yok"
        self._loading_record = False
        self.current_theme = 'Okyanus Mavisi'

        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value='Hepsi')
        self.theme_var = tk.StringVar(value=self.current_theme)
        self.save_state_var = tk.StringVar(value='Hazır')
        self.status_var = tk.StringVar(value='Dosya açılmadı')
        self.char_count_var = tk.StringVar(value='0 / 255')
        self.backup_var = tk.StringVar(value='● Otomatik yedek: bekleniyor')
        self.placeholder_var = tk.StringVar(value='Yer tutucular: -')
        self.record_info_var = tk.StringVar(value='Kayıt: -')
        self.match_info_var = tk.StringVar(value='')

        self._build_styles()
        self._build_ui()
        self.apply_theme(self.current_theme)

        self.search_var.trace_add('write', lambda *_: self.refresh())
        self.root.bind('<Control-s>', lambda e: self.save())
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(60000, self._periodic_backup)

        default = os.path.join(os.path.dirname(__file__), 'language_EN_TR_v66_ESLESMELI.csv')
        if os.path.isfile(default):
            self.open_file(default)

    # ---------- UI ----------
    def _build_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

    def _build_ui(self):
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.topbar = tk.Frame(self.root)
        self.topbar.grid(row=0, column=0, sticky='ew')
        self.topbar.grid_columnconfigure(1, weight=1)

        title_wrap = tk.Frame(self.topbar)
        title_wrap.grid(row=0, column=0, sticky='w', padx=16, pady=(12, 6))
        self.title_label = tk.Label(title_wrap, text='CM 01/02 Çeviri Editörü', font=('Segoe UI', 17, 'bold'))
        self.title_label.pack(anchor='w')
        self.subtitle_label = tk.Label(title_wrap, text='İngilizce–Türkçe kontrol, alternatif çeviriler ve tema seçenekleri', font=('Segoe UI', 9))
        self.subtitle_label.pack(anchor='w', pady=(2, 0))

        toolbar = tk.Frame(self.topbar)
        toolbar.grid(row=1, column=0, columnspan=2, sticky='ew', padx=12, pady=(0, 10))
        toolbar.grid_columnconfigure(20, weight=1)

        self._btn(toolbar, '📂 CSV Aç', self.open_dialog).grid(row=0, column=0, padx=4, pady=4)
        self._btn(toolbar, '💾 Kaydet', self.save).grid(row=0, column=1, padx=4, pady=4)
        self._btn(toolbar, '📄 Farklı Kaydet', self.save_as).grid(row=0, column=2, padx=4, pady=4)
        self._btn(toolbar, '◀ Önceki', lambda: self.step(-1), small=True).grid(row=0, column=3, padx=4, pady=4)
        self._btn(toolbar, 'Sonraki ▶', lambda: self.step(1), small=True).grid(row=0, column=4, padx=4, pady=4)

        self.save_state_label = tk.Label(toolbar, textvariable=self.save_state_var, font=('Segoe UI', 10, 'bold'))
        self.save_state_label.grid(row=0, column=20, sticky='e', padx=(20, 10))
        self.backup_label = tk.Label(toolbar, textvariable=self.backup_var, font=('Segoe UI', 9))
        self.backup_label.grid(row=0, column=19, sticky='e', padx=(8, 10))

        theme_lbl = tk.Label(toolbar, text='Tema:', font=('Segoe UI', 10, 'bold'))
        theme_lbl.grid(row=0, column=21, padx=(10, 6))
        self.theme_box = ttk.Combobox(toolbar, textvariable=self.theme_var, state='readonly', values=list(THEMES.keys()), width=16)
        self.theme_box.grid(row=0, column=22, padx=(0, 8))
        self.theme_box.bind('<<ComboboxSelected>>', lambda e: self.apply_theme(self.theme_var.get()))

        main = tk.PanedWindow(self.root, orient='horizontal', sashwidth=8, bd=0)
        main.grid(row=2, column=0, sticky='nsew', padx=10, pady=(0, 8))
        self.main = main

        # Left panel
        self.left_panel = tk.Frame(main)
        main.add(self.left_panel, minsize=350, width=430)
        self.left_panel.grid_rowconfigure(3, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        left_head = tk.Frame(self.left_panel)
        left_head.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 8))
        self.search_entry = ttk.Entry(left_head, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        left_head.grid_columnconfigure(0, weight=1)
        self.filter_box = ttk.Combobox(left_head, textvariable=self.filter_var, state='readonly', width=22,
            values=['Hepsi','Çevrildi','Korundu (özel ad/kod)','Kontrol edildi','Kontrol edilecek',
                    'Etiket uyumsuzluğu','İngilizceyle aynı','v65 tam eşleşme','v65 inceleme gerekli',
                    'v65 güvenli aday','v65 riskli aday','v65 alternatifsiz','Kaynak tam','Kaynak belirsiz'])
        self.filter_box.grid(row=1, column=0, sticky='ew', pady=(8, 0), padx=(0,8))
        self.filter_box.bind('<<ComboboxSelected>>', lambda e: self.refresh())

        self.left_stats = tk.Label(self.left_panel, text='Kayıt listesi', anchor='w', font=('Segoe UI', 10, 'bold'))
        self.left_stats.grid(row=1, column=0, sticky='ew', padx=10, pady=(2, 6))

        tree_wrap = tk.Frame(self.left_panel)
        tree_wrap.grid(row=3, column=0, sticky='nsew', padx=10, pady=(0, 10))
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_wrap, columns=('id', 'en', 'state'), show='headings', selectmode='browse')
        self.tree.heading('id', text='#')
        self.tree.heading('en', text='Metin (İngilizce)')
        self.tree.heading('state', text='Durum')
        self.tree.column('id', width=65, stretch=False, anchor='center')
        self.tree.column('en', width=260, stretch=True)
        self.tree.column('state', width=120, stretch=False)
        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_y = ttk.Scrollbar(tree_wrap, orient='vertical', command=self.tree.yview)
        tree_y.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=tree_y.set)
        self.tree.bind('<<TreeviewSelect>>', self.choose)
        self.tree.tag_configure('approved', foreground='#44da91')
        self.tree.tag_configure('review', foreground='#ffc34d')
        self.tree.tag_configure('normal', foreground='#d8edff')

        self.left_footer = tk.Label(self.left_panel, text='Toplam kayıt: 0 | Filtrelenmiş: 0', anchor='w')
        self.left_footer.grid(row=4, column=0, sticky='ew', padx=10, pady=(0, 10))

        # Right panel
        self.right_panel = tk.Frame(main)
        main.add(self.right_panel, minsize=700)
        self.right_panel.grid_rowconfigure(4, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        chipbar = tk.Frame(self.right_panel)
        chipbar.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 8))
        chipbar.grid_columnconfigure(6, weight=1)
        self.chip_status = tk.Label(chipbar, text='Hazır', padx=12, pady=6, font=('Segoe UI', 9, 'bold'))
        self.chip_status.grid(row=0, column=0, padx=(0,8), sticky='w')
        self.record_info = tk.Label(chipbar, textvariable=self.record_info_var, padx=10, pady=6)
        self.record_info.grid(row=0, column=1, padx=(0,8), sticky='w')
        self.source_info = tk.Label(chipbar, text='Kaynak: v66 CSV', padx=10, pady=6)
        self.source_info.grid(row=0, column=2, padx=(0,8), sticky='w')
        self.match_label = tk.Label(chipbar, text='v65 karşılaştırması aktif', padx=10, pady=6)
        self.match_label.grid(row=0, column=3, padx=(0,8), sticky='w')

        eng_frame = self._section(self.right_panel, 'İngilizce Metin (salt okunur)')
        eng_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))
        eng_frame.grid_columnconfigure(0, weight=1)
        self.en_text = tk.Text(eng_frame, wrap='word', height=7, relief='flat', font=('Segoe UI', 12))
        self.en_text.grid(row=0, column=0, sticky='ew', padx=12, pady=(0,12))
        self.en_text.configure(state='disabled')

        tr_frame = self._section(self.right_panel, 'Türkçe Çeviri')
        tr_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 10))
        tr_frame.grid_columnconfigure(0, weight=1)
        tr_head = tk.Frame(tr_frame)
        tr_head.grid(row=0, column=0, sticky='ew', padx=12, pady=(10, 4))
        tr_head.grid_columnconfigure(0, weight=1)
        self.char_label = tk.Label(tr_head, textvariable=self.char_count_var)
        self.char_label.grid(row=0, column=1, sticky='e')
        self.tr_text = tk.Text(tr_frame, wrap='word', height=8, relief='flat', font=('Segoe UI', 12), undo=True)
        self.tr_text.grid(row=1, column=0, sticky='ew', padx=12, pady=(0,12))
        self.tr_text.bind('<<Modified>>', self._translation_modified)
        self.placeholder_label = tk.Label(tr_frame, textvariable=self.placeholder_var, anchor='w', font=('Segoe UI', 10, 'bold'))
        self.placeholder_label.grid(row=2, column=0, sticky='ew', padx=12, pady=(0, 12))

        alt_frame = self._section(self.right_panel, 'Alternatif Çeviriler')
        alt_frame.grid(row=3, column=0, sticky='nsew', padx=10, pady=(0, 10))
        alt_frame.grid_rowconfigure(1, weight=1)
        alt_frame.grid_columnconfigure(0, weight=1)

        info_row = tk.Frame(alt_frame)
        info_row.grid(row=0, column=0, sticky='ew', padx=12, pady=(10, 6))
        info_row.grid_columnconfigure(0, weight=1)
        self.match_info = tk.Label(info_row, textvariable=self.match_info_var, justify='left', anchor='w')
        self.match_info.grid(row=0, column=0, sticky='w')

        alt_body = tk.Frame(alt_frame)
        alt_body.grid(row=1, column=0, sticky='nsew', padx=12, pady=(0,12))
        alt_body.grid_rowconfigure(0, weight=1)
        alt_body.grid_columnconfigure(0, weight=1)

        self.alt_tree = ttk.Treeview(alt_body, columns=('no','src','score','safety','tr'), show='headings', selectmode='browse', height=6)
        for col, txt, width in [
            ('no', '#', 40), ('src', 'Kaynak', 90), ('score', 'Benzerlik', 80), ('safety', 'Denetim', 160), ('tr', 'Alternatif Çeviri', 420)
        ]:
            self.alt_tree.heading(col, text=txt)
            self.alt_tree.column(col, width=width, stretch=(col=='tr'))
        self.alt_tree.grid(row=0, column=0, sticky='nsew')
        alt_y = ttk.Scrollbar(alt_body, orient='vertical', command=self.alt_tree.yview)
        alt_y.grid(row=0, column=1, sticky='ns')
        self.alt_tree.configure(yscrollcommand=alt_y.set)
        self.alt_tree.bind('<Double-1>', lambda e: self.apply_selected_alt())

        action_row = tk.Frame(alt_frame)
        action_row.grid(row=2, column=0, sticky='ew', padx=12, pady=(0, 12))
        self._btn(action_row, '⬇ Alternatifi uygula', self.apply_selected_alt).pack(side='left', padx=(0, 8))
        self._btn(action_row, '☰ Diğer adaylar', self.more_candidates).pack(side='left', padx=(0, 8))
        self._btn(action_row, '✓ v65 onayla', self.approve_v65).pack(side='left', padx=(0, 8))
        self._btn(action_row, '✓ Değişikliği uygula', self.commit, accent=True).pack(side='right', padx=(8, 0))

        note_frame = self._section(self.right_panel, 'Notlar ve İşlemler')
        note_frame.grid(row=4, column=0, sticky='nsew', padx=10, pady=(0, 10))
        note_frame.grid_columnconfigure(0, weight=1)
        btnrow = tk.Frame(note_frame)
        btnrow.grid(row=0, column=0, sticky='ew', padx=12, pady=(10,8))
        self._btn(btnrow, 'Kontrol edildi', lambda: self.set_status('Kontrol edildi'), small=True).pack(side='left', padx=(0, 8))
        self._btn(btnrow, 'Kontrol edilecek', lambda: self.set_status('Kontrol edilecek'), small=True).pack(side='left', padx=(0, 8))
        self._btn(btnrow, 'Çevrildi', lambda: self.set_status('Çevrildi'), small=True).pack(side='left', padx=(0, 8))
        self._btn(btnrow, 'Eski çeviriyi kopyala', self.copy_alt, small=True).pack(side='left', padx=(0, 8))
        self.note_label = tk.Label(note_frame, textvariable=self.status_var, justify='left', anchor='w')
        self.note_label.grid(row=1, column=0, sticky='ew', padx=12, pady=(0,12))

        self.statusbar = tk.Frame(self.root)
        self.statusbar.grid(row=3, column=0, sticky='ew')
        self.status_label = tk.Label(self.statusbar, text='Hazır', anchor='w', padx=12, pady=8)
        self.status_label.pack(fill='x')

    def _section(self, parent, title):
        outer = tk.Frame(parent, highlightthickness=1)
        title_lbl = tk.Label(outer, text=title, font=('Segoe UI', 12, 'bold'))
        title_lbl.grid(row=0, column=0, sticky='w', padx=12, pady=(10, 8))
        return outer

    def _btn(self, parent, text, command, small=False, accent=False):
        btn = tk.Button(parent, text=text, command=command, cursor='hand2', relief='flat', bd=0,
                        font=('Segoe UI', 9 if small else 10, 'bold' if accent else 'normal'), padx=12, pady=8)
        return btn

    # ---------- Theme ----------
    def apply_theme(self, name):
        self.current_theme = name
        c = THEMES[name]
        self.style.configure('TCombobox', fieldbackground=c['surface2'], background=c['surface2'],
                             foreground=c['fg'], bordercolor=c['border'], arrowcolor=c['accent'])
        self.style.map('TCombobox', fieldbackground=[('readonly', c['surface2'])], foreground=[('readonly', c['fg'])])
        self.style.configure('Treeview', background=c['text_bg'], foreground=c['fg'], fieldbackground=c['text_bg'],
                             bordercolor=c['border'], rowheight=32, font=('Segoe UI', 10))
        self.style.map('Treeview', background=[('selected', c['accent2'])], foreground=[('selected', '#ffffff')])
        self.tree.tag_configure('approved', foreground=c['good'])
        self.tree.tag_configure('review', foreground=c['warn'])
        self.tree.tag_configure('normal', foreground=c['fg'])
        self.style.configure('Treeview.Heading', background=c['surface3'], foreground=c['fg'], relief='flat')
        self.style.configure('Vertical.TScrollbar', background=c['surface2'], troughcolor=c['bg'], arrowcolor=c['accent'])

        self.root.configure(bg=c['bg'])
        for frame in [self.topbar, self.left_panel, self.right_panel, self.statusbar, self.main]:
            try: frame.configure(bg=c['bg'])
            except Exception: pass
        for widget in [self.title_label, self.subtitle_label, self.left_stats, self.left_footer,
                       self.save_state_label, self.record_info, self.source_info, self.match_label,
                       self.char_label, self.note_label, self.status_label, self.statusbar,
                       self.left_panel, self.right_panel, self.topbar]:
            try: widget.configure(bg=c['bg'], fg=c['fg'])
            except Exception: pass
        self.subtitle_label.configure(fg=c['muted'])
        self.save_state_label.configure(fg=c['good'])
        self.backup_label.configure(fg=c['accent'])
        self.placeholder_label.configure(fg=c['good'])
        self.left_stats.configure(bg=c['bg'], fg=c['fg'])
        self.left_footer.configure(bg=c['bg'], fg=c['muted'])
        self.status_label.configure(bg=c['surface'], fg=c['muted'])

        # recursively color frames/labels/buttons
        self._paint_recursive(self.root, c)

        # text widgets
        for txt in [self.en_text, self.tr_text]:
            txt.configure(bg=c['text_bg'], fg=c['fg'], insertbackground=c['accent'],
                          selectbackground=c['select'], selectforeground=c['fg'],
                          highlightthickness=1, highlightbackground=c['border'], highlightcolor=c['accent'])
        self.en_text.configure(state='disabled')

        # custom chips
        self.chip_status.configure(bg=c['warn'], fg='#202020')
        for chip in [self.record_info, self.source_info, self.match_label]:
            chip.configure(bg=c['surface2'], fg=c['fg'])

    def _paint_recursive(self, parent, c):
        for child in parent.winfo_children():
            cls = child.winfo_class()
            try:
                if cls in ('Frame', 'Labelframe', 'Panedwindow'):
                    child.configure(bg=c['bg'], highlightbackground=c['border'])
                elif cls == 'Label':
                    if child is self.chip_status:
                        pass
                    elif child in (self.record_info, self.source_info, self.match_label):
                        pass
                    else:
                        child.configure(bg=child.master.cget('bg') if hasattr(child.master, 'cget') else c['bg'], fg=c['fg'])
                elif cls == 'Button':
                    accent = ('uygula' in child.cget('text').lower() or child.cget('text') == 'Kaydet')
                    child.configure(bg=c['accent2'] if accent else c['surface2'], fg='white',
                                    activebackground=c['accent'] if accent else c['surface3'], activeforeground='white',
                                    highlightthickness=1, highlightbackground=c['border'])
                elif cls == 'Entry':
                    child.configure(bg=c['text_bg'], fg=c['fg'], insertbackground=c['accent'], relief='flat',
                                    highlightthickness=1, highlightbackground=c['border'])
                elif cls == 'Text':
                    child.configure(bg=c['text_bg'], fg=c['fg'], insertbackground=c['accent'])
            except Exception:
                pass
            self._paint_recursive(child, c)

    # ---------- Data / actions ----------
    def open_dialog(self):
        p = filedialog.askopenfilename(filetypes=[('CSV', '*.csv')])
        if p:
            self.open_file(p)

    def open_file(self, p):
        if self.dirty and not messagebox.askyesno('Kaydedilmemiş değişiklikler', 'Değişiklikler kaydedilmedi. Devam edilsin mi?'):
            return
        try:
            with open(p, encoding='utf-8-sig', newline='') as f:
                rd = csv.DictReader(f, delimiter=';')
                data = list(rd)
                assert all(k in rd.fieldnames for k in HEAD), 'Gerekli sütunlar yok'
        except Exception as e:
            messagebox.showerror('CSV açılamadı', str(e))
            return
        self.rows = data
        self.path = p
        self.dirty = False
        self.selected = None
        self.refresh()
        self.root.title(f'CM 01/02 Çeviri Editörü - {os.path.basename(p)}')
        self.backup_var.set('● Otomatik yedek: 60 sn aralıkla')
        self.status_var.set(f'Açılan dosya: {p}')
        self.status_label.configure(text=f'Açık dosya: {p}')
        self.save_state_var.set('Değişiklik yok')

    def problems(self, r):
        en = TAG.findall(r.get('English (Original)', ''))
        tr = TAG.findall(r.get('Türkçe (Çeviri)', ''))
        msg = []
        if len(en) != len(tr):
            msg.append(f'Etiket sayısı uyuşmuyor: EN {len(en)}, TR {len(tr)}')
        if not r.get('Türkçe (Çeviri)', '').strip():
            msg.append('Türkçe boş')
        return '; '.join(msg) or 'Etiket sayısı uygun'

    def refresh(self):
        if not self.rows:
            return
        q = self.search_var.get().casefold().strip()
        flt = self.filter_var.get()
        self.filtered = []
        for i, r in enumerate(self.rows):
            hay = ' '.join([
                r.get('ID', ''), r.get('English (Original)', ''), r.get('Türkçe (Çeviri)', ''),
                r.get('v65 Alternatif v6', ''), r.get('v65 İngilizce', ''), r.get('v65 Alternatif Durumu', '')
            ]).casefold()
            if q and q not in hay:
                continue
            if flt == 'Etiket uyumsuzluğu' and len(TAG.findall(r.get('English (Original)', ''))) == len(TAG.findall(r.get('Türkçe (Çeviri)', ''))):
                continue
            if flt == 'Kaynak tam' and r.get('v65 Kaynak Eşleştirme') != 'Tam kaynak':
                continue
            if flt == 'Kaynak belirsiz' and r.get('v65 Kaynak Eşleştirme') == 'Tam kaynak':
                continue
            if flt == 'v65 güvenli aday' and r.get('v65 Güvenlik Kontrolü') != 'İncelenebilir aday':
                continue
            if flt == 'v65 riskli aday' and r.get('v65 Güvenlik Kontrolü') not in ('Eksik/fazla değişken','Değişken türü farklı','Bozuk/kontrol karakteri'):
                continue
            if flt == 'v65 alternatifsiz' and r.get('v65 Güvenlik Kontrolü') != 'Alternatif yok':
                continue
            if flt == 'v65 tam eşleşme' and r.get('v65 Alternatif Durumu') != 'Tam kaynak eşleşmesi / Türkçe aday':
                continue
            if flt == 'v65 inceleme gerekli' and r.get('v65 Alternatif Durumu') == 'Tam kaynak eşleşmesi / Türkçe aday':
                continue
            if flt == 'İngilizceyle aynı' and r.get('English (Original)', '').strip() != r.get('Türkçe (Çeviri)', '').strip():
                continue
            simple = ('Hepsi','Etiket uyumsuzluğu','İngilizceyle aynı','v65 tam eşleşme','v65 inceleme gerekli','v65 güvenli aday','v65 riskli aday','v65 alternatifsiz','Kaynak tam','Kaynak belirsiz')
            if flt not in simple and r.get('Durum') != flt:
                continue
            self.filtered.append(i)

        cur = self.selected
        self.tree.delete(*self.tree.get_children())
        for idx in self.filtered:
            r = self.rows[idx]
            preview = ' '.join(r.get('English (Original)', '').split())[:85]
            state=r.get('Durum','')
            tag = 'approved' if state == 'Kontrol edildi' else ('review' if state == 'Kontrol edilecek' or 'belirsiz' in r.get('v65 Kaynak Eşleştirme','').lower() else 'normal')
            icon = '✓ ' if tag == 'approved' else ('● ' if tag == 'review' else '• ')
            self.tree.insert('', 'end', iid=str(idx), tags=(tag,), values=(r.get('ID', ''), preview, icon + state))

        self.left_stats.configure(text='Kayıt Listesi')
        self.left_footer.configure(text=f'Toplam kayıt: {len(self.rows):,} | Filtrelenmiş: {len(self.filtered):,}')
        self.status_label.configure(text=f'Görüntülenen {len(self.filtered):,} / Toplam {len(self.rows):,}')

        if cur is not None and str(cur) in self.tree.get_children():
            self.tree.selection_set(str(cur))
            self.tree.see(str(cur))
            self.choose()
        elif self.filtered:
            first = self.filtered[0]
            self.tree.selection_set(str(first))
            self.tree.see(str(first))
            self.choose()

    def choose(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if self.selected is not None and idx != self.selected:
            self.commit(refresh=False)
        self.selected = idx
        r = self.rows[idx]

        self.en_text.configure(state='normal')
        self.en_text.delete('1.0', 'end')
        self.en_text.insert('1.0', r.get('English (Original)', ''))
        self.en_text.configure(state='disabled')

        self._loading_record = True
        self.tr_text.delete('1.0', 'end')
        self.tr_text.insert('1.0', r.get('Türkçe (Çeviri)', ''))
        self.tr_text.edit_modified(False)
        self._loading_record = False
        self.update_char_count()
        self.populate_alt(r)
        self.record_info_var.set(f"Kayıt: {r.get('ID', '')}")
        self.status_var.set(f"ID {r.get('ID', '')} · {self.problems(r)}")
        self.chip_status.configure(text=r.get('Durum', 'Durum yok'))
        self.save_state_var.set('Değişiklik yok' if not self.dirty else 'Kaydedilmedi')

    def update_char_count(self):
        value = self.tr_text.get('1.0', 'end-1c')
        self.char_count_var.set(f'{len(value)} karakter (önerilen sınır: 255)')
        en = self.rows[self.selected].get('English (Original)', '') if self.selected is not None and self.rows else ''
        en_tags = TAG.findall(en)
        tr_tags = TAG.findall(value)
        valid = sorted(en_tags) == sorted(tr_tags)
        self.placeholder_var.set(('✓ Yer tutucular eşleşiyor' if valid else '⚠ YER TUTUCU UYUMSUZLUĞU') + f'  |  EN: {len(en_tags)} / TR: {len(tr_tags)}')
        self.placeholder_label.configure(fg=THEMES[self.current_theme]['good' if valid else 'bad'])
        self.char_label.configure(fg=THEMES[self.current_theme]['warn' if len(value)>255 else 'muted'])

    def _translation_modified(self, event=None):
        if self.tr_text.edit_modified():
            self.tr_text.edit_modified(False)
            if not self._loading_record and self.selected is not None:
                self.save_state_var.set('● Kaydedilmemiş değişiklik')
                self.update_char_count()

    def _snapshot_rows(self):
        # Save the text currently being edited into the in-memory table.
        self.commit(refresh=False)

    def _backup(self):
        if not self.rows or not self.path:
            return False
        self._snapshot_rows()
        directory = os.path.join(os.path.dirname(self.path), 'yedekler')
        os.makedirs(directory, exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        target = os.path.join(directory, f'{os.path.splitext(os.path.basename(self.path))[0]}_{ts}.csv')
        with open(target, 'w', encoding='utf-8-sig', newline='') as f:
            writer=csv.DictWriter(f, fieldnames=list(self.rows[0]), delimiter=';', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.rows)
        self.backup_count += 1
        self.backup_last = datetime.datetime.now().strftime('%H:%M:%S')
        self.backup_var.set(f'● Yedek: {self.backup_last} (#{self.backup_count})')
        return True

    def _periodic_backup(self):
        try:
            if self.dirty or (self.selected is not None and self.tr_text.get('1.0','end-1c') != self.rows[self.selected].get('Türkçe (Çeviri)', '')):
                self._backup()
        except Exception as e:
            self.backup_var.set('⚠ Yedekleme hatası')
            self.status_var.set(f'Otomatik yedekleme hatası: {e}')
        finally:
            self.root.after(60000, self._periodic_backup)

    def populate_alt(self, r):
        self.alt_tree.delete(*self.alt_tree.get_children())
        candidates = self._get_candidates(r)
        safety = r.get('v65 Güvenlik Kontrolü', '')
        score = r.get('v65 Benzerlik (%)', '')
        source_match = r.get('v65 Kaynak Eşleştirme', '')
        self.match_info_var.set(f'Kaynak eşleştirme: {source_match}    |    Güvenlik: {safety}    |    Benzerlik: {score}%')
        if not candidates:
            alt = r.get('v65 Alternatif v6', '').strip()
            if alt:
                candidates = [{'id': r.get('v65 Kaynak ID', ''), 'en': r.get('v65 İngilizce', ''), 'tr': alt, 'score': score}]
        for i, a in enumerate(candidates, start=1):
            tr = ' '.join((a.get('tr') or '').split())
            label_score = f"%{a.get('score', '')}" if a.get('score', '') != '' else ''
            self.alt_tree.insert('', 'end', iid=f'alt{i}', values=(i, f"v65 #{a.get('id','')}", label_score, safety, tr[:200]))

    def _get_candidates(self, r):
        try:
            arr = json.loads(r.get('v65 Alternatif Seçenekleri', '[]'))
            if isinstance(arr, list):
                return arr
        except Exception:
            pass
        return []

    def apply_selected_alt(self):
        if self.selected is None:
            return
        r = self.rows[self.selected]
        candidates = self._get_candidates(r)
        sel = self.alt_tree.selection()
        if not sel:
            if candidates:
                self.alt_tree.selection_set(self.alt_tree.get_children()[0])
                sel = self.alt_tree.selection()
            else:
                return
        try:
            row_index = int(self.alt_tree.item(sel[0], 'values')[0]) - 1
            cand = candidates[row_index]
            value = (cand.get('tr') or '').strip()
        except Exception:
            value = r.get('v65 Alternatif v6', '').strip()
        if not value:
            messagebox.showinfo('Alternatif yok', 'Seçili adayda kullanılabilir Türkçe metin bulunmuyor.')
            return
        self.tr_text.delete('1.0', 'end')
        self.tr_text.insert('1.0', value)
        self.update_char_count()
        self.save_state_var.set('Kaydedilmedi')
        self.status_var.set('Alternatif çeviri düzenleme alanına kopyalandı.')

    def copy_alt(self):
        if self.selected is None:
            return
        r = self.rows[self.selected]
        value = r.get('v65 Alternatif v6', '').strip()
        if not value:
            messagebox.showinfo('Alternatif yok', 'Bu kayıtta ayrıştırılmış eski Türkçe metin bulunmuyor.')
            return
        self.tr_text.delete('1.0', 'end')
        self.tr_text.insert('1.0', value)
        self.update_char_count()
        self.save_state_var.set('Kaydedilmedi')

    def more_candidates(self):
        if self.selected is None:
            return
        r = self.rows[self.selected]
        candidates = self._get_candidates(r)
        w = tk.Toplevel(self.root)
        w.title(f'v65 Adayları - ID {r.get("ID", "")}')
        w.geometry('980x560')
        c = THEMES[self.current_theme]
        w.configure(bg=c['bg'])
        text = tk.Text(w, wrap='word', bg=c['text_bg'], fg=c['fg'], insertbackground=c['accent'])
        text.pack(fill='both', expand=True, padx=12, pady=12)
        if not candidates:
            text.insert('1.0', 'Başka aday bulunamadı.')
        else:
            blocks = []
            for i, a in enumerate(candidates, start=1):
                blocks.append(f"{i}. v65 #{a.get('id','')} | Benzerlik %{a.get('score','')}\nİngilizce: {a.get('en','')}\nTürkçe: {a.get('tr','')}")
            text.insert('1.0', '\n\n'.join(blocks))
        text.configure(state='disabled')
        bar = tk.Frame(w, bg=c['bg'])
        bar.pack(fill='x', padx=12, pady=(0, 12))
        tk.Button(bar, text='Aday numarasıyla uygula', command=lambda: self.choose_candidate(candidates, w),
                  bg=c['accent2'], fg='white', relief='flat', padx=12, pady=8).pack(side='left')

    def choose_candidate(self, candidates, w):
        if not candidates:
            return
        number = simpledialog.askinteger('Aday seçimi', 'Uygulanacak aday sıra numarası:', parent=w, minvalue=1, maxvalue=len(candidates))
        if number is None:
            return
        cand = candidates[number - 1]
        value = (cand.get('tr') or '').strip()
        if not value:
            messagebox.showwarning('Türkçe yok', 'Bu adayın kullanılabilir Türkçe metni yok.', parent=w)
            return
        self.tr_text.delete('1.0', 'end')
        self.tr_text.insert('1.0', value)
        self.update_char_count()
        self.save_state_var.set('Kaydedilmedi')
        self.status_var.set(f'v65 aday #{cand.get("id", "")} kopyalandı.')
        w.destroy()

    def commit(self, refresh=True):
        if self.selected is None:
            return
        r = self.rows[self.selected]
        value = self.tr_text.get('1.0', 'end-1c')
        if value != r.get('Türkçe (Çeviri)', ''):
            r['Türkçe (Çeviri)'] = value
            self.dirty = True
            self.save_state_var.set('Kaydedilmedi')
        self.status_var.set(f"ID {r.get('ID', '')} · {self.problems(r)}")
        if refresh:
            self.refresh()

    def set_status(self, s):
        if self.selected is None:
            return
        self.commit(refresh=False)
        self.rows[self.selected]['Durum'] = s
        self.dirty = True
        self.save_state_var.set('Kaydedilmedi')
        self.refresh()

    def approve_v65(self):
        if self.selected is None:
            return
        self.rows[self.selected]['v65 Onay'] = 'İnsan tarafından onaylandı'
        self.dirty = True
        self.save_state_var.set('Kaydedilmedi')
        self.status_var.set('v65 alternatifi onaylandı.')

    def step(self, d):
        self.commit(refresh=False)
        if not self.filtered:
            return
        try:
            ix = self.filtered.index(self.selected)
        except ValueError:
            ix = 0
        idx = self.filtered[min(max(ix + d, 0), len(self.filtered) - 1)]
        self.tree.selection_set(str(idx))
        self.tree.see(str(idx))
        self.choose()

    def save_as(self):
        p = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if p:
            self.save(p)

    def save(self, p=None):
        self.commit(refresh=False)
        if not self.rows:
            return
        p = p or self.path
        try:
            if os.path.exists(p):
                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                shutil.copy2(p, p + '.' + ts + '.bak')
            with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=list(self.rows[0].keys()), delimiter=';', extrasaction='ignore')
                w.writeheader()
                w.writerows(self.rows)
            self.path = p
            self.dirty = False
            self._backup()
            self.save_state_var.set('Kaydedildi')
            self.status_var.set(f'Kaydedildi: {p}')
            self.status_label.configure(text=f'Kaydedildi: {p}')
        except Exception as e:
            messagebox.showerror('Kayıt hatası', str(e))

    def close(self):
        self.commit(refresh=False)
        if self.dirty:
            choice = messagebox.askyesnocancel('Kaydedilmemiş değişiklikler', 'Değişiklikler kaydedilsin mi?')
            if choice is None:
                return
            if choice:
                self.save()
                if self.dirty:return
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    Editor(root)
    root.mainloop()
