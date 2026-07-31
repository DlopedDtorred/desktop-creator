#!/usr/bin/env python3
"""
Desktop Creator - Creador y gestor de archivos .desktop para GNOME / Fedora
"""

import os
import sys
import subprocess
import shlex
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gdk, Gio, GLib, Adw
from desktop_parser import (
    get_user_applications_dir,
    build_desktop_content,
    save_desktop_file,
    parse_desktop_file,
    STANDARD_CATEGORIES,
    validate_desktop_file,
)


class DesktopCreatorWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Creador de Accesos Directos (.desktop)")
        self.set_default_size(800, 720)

        self.current_filepath = None
        self.category_checks = {}

        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toast_overlay.set_child(main_box)

        # Header bar
        self.header_bar = Adw.HeaderBar()
        main_box.append(self.header_bar)

        # Title / View switcher in HeaderBar
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)
        self.view_stack.set_hexpand(True)

        switcher_title = Adw.ViewSwitcherTitle()
        switcher_title.set_stack(self.view_stack)
        switcher_title.set_title("Creador .desktop")
        self.header_bar.set_title_widget(switcher_title)

        view_switcher_bar = Adw.ViewSwitcherBar()
        view_switcher_bar.set_stack(self.view_stack)
        switcher_title.connect("notify::title-visible", lambda widget, pspec: view_switcher_bar.set_reveal(widget.get_title_visible()))

        # Header Bar buttons
        open_btn = Gtk.Button(icon_name="document-open-symbolic")
        open_btn.set_tooltip_text("Abrir archivo .desktop existente")
        open_btn.connect("clicked", self.on_open_clicked)
        self.header_bar.pack_start(open_btn)

        new_btn = Gtk.Button(icon_name="document-new-symbolic")
        new_btn.set_tooltip_text("Nuevo acceso directo (limpiar)")
        new_btn.connect("clicked", self.on_new_clicked)
        self.header_bar.pack_start(new_btn)

        save_sys_btn = Gtk.Button(label="Guardar en Sistema")
        save_sys_btn.add_css_class("suggested-action")
        save_sys_btn.set_tooltip_text("Guardar directamente en ~/.local/share/applications/")
        save_sys_btn.connect("clicked", self.on_save_system_clicked)
        self.header_bar.pack_end(save_sys_btn)

        export_btn = Gtk.Button(icon_name="document-save-as-symbolic")
        export_btn.set_tooltip_text("Exportar como...")
        export_btn.connect("clicked", self.on_export_clicked)
        self.header_bar.pack_end(export_btn)

        # Construct Pages
        self.setup_form_page()
        self.setup_preview_page()
        self.setup_manager_page()

        # Append view stack and switcher bar to main container
        main_box.append(self.view_stack)
        main_box.append(view_switcher_bar)

        # Connect stack changes to update preview
        self.view_stack.connect("notify::visible-child", self.on_stack_changed)

    def show_toast(self, message):
        toast = Adw.Toast.new(message)
        self.toast_overlay.add_toast(toast)

    def setup_form_page(self):
        pref_page = Adw.PreferencesPage()

        # --- GRUPO 1: Información Básica ---
        grp_basic = Adw.PreferencesGroup(title="Información Principal", description="Datos básicos del acceso directo")
        pref_page.add(grp_basic)

        self.row_name = Adw.EntryRow(title="Nombre de la Aplicación (Name)")
        self.row_name.set_tooltip_text("Ejemplo: Mi Juego, Script Útil, Firefox Custom")
        self.row_name.connect("changed", self.on_form_field_changed)
        grp_basic.add(self.row_name)

        self.row_generic = Adw.EntryRow(title="Nombre Genérico (GenericName)")
        self.row_generic.set_tooltip_text("Ejemplo: Navegador Web, Editor de Texto, IDE")
        self.row_generic.connect("changed", self.on_form_field_changed)
        grp_basic.add(self.row_generic)

        self.row_comment = Adw.EntryRow(title="Descripción / Comentario (Comment)")
        self.row_comment.set_tooltip_text("Breve descripción que aparece al pasar el cursor o buscar")
        self.row_comment.connect("changed", self.on_form_field_changed)
        grp_basic.add(self.row_comment)

        # --- GRUPO 2: Comando y Ejecución ---
        grp_exec = Adw.PreferencesGroup(title="Comando y Ejecución", description="Ruta al ejecutable y opciones de lanzamiento")
        pref_page.add(grp_exec)

        # Exec row
        self.row_exec = Adw.EntryRow(title="Comando / Ejecutable (Exec)")
        self.row_exec.set_tooltip_text("Comando o ruta absoluta al ejecutable o script")
        self.row_exec.connect("changed", self.on_form_field_changed)
        
        btn_browse_exec = Gtk.Button(icon_name="folder-open-symbolic")
        btn_browse_exec.set_valign(Gtk.Align.CENTER)
        btn_browse_exec.set_tooltip_text("Buscar ejecutable...")
        btn_browse_exec.connect("clicked", self.on_browse_exec_clicked)
        self.row_exec.add_suffix(btn_browse_exec)

        btn_test_exec = Gtk.Button(icon_name="media-playback-start-symbolic")
        btn_test_exec.set_valign(Gtk.Align.CENTER)
        btn_test_exec.set_tooltip_text("Probar/Ejecutar comando ahora")
        btn_test_exec.connect("clicked", self.on_test_exec_clicked)
        self.row_exec.add_suffix(btn_test_exec)
        grp_exec.add(self.row_exec)

        # Path row
        self.row_path = Adw.EntryRow(title="Directorio de Trabajo (Path) - Opcional")
        self.row_path.set_tooltip_text("Carpeta desde donde se ejecutará el programa")
        self.row_path.connect("changed", self.on_form_field_changed)

        btn_browse_path = Gtk.Button(icon_name="folder-open-symbolic")
        btn_browse_path.set_valign(Gtk.Align.CENTER)
        btn_browse_path.set_tooltip_text("Buscar directorio...")
        btn_browse_path.connect("clicked", self.on_browse_path_clicked)
        self.row_path.add_suffix(btn_browse_path)
        grp_exec.add(self.row_path)

        # Terminal switch
        self.switch_terminal = Adw.SwitchRow(title="Ejecutar en Terminal (Terminal)")
        self.switch_terminal.set_subtitle("Activa esta opción si es una herramienta CLI o script de terminal")
        self.switch_terminal.connect("notify::active", self.on_form_field_changed)
        grp_exec.add(self.switch_terminal)

        # --- GRUPO 3: Icono y Apariencia ---
        grp_icon = Adw.PreferencesGroup(title="Icono y Apariencia")
        pref_page.add(grp_icon)

        self.row_icon = Adw.EntryRow(title="Icono (Icon)")
        self.row_icon.set_tooltip_text("Nombre de icono de sistema (ej: 'utilities-terminal') o ruta a imagen (.png, .svg)")
        self.row_icon.connect("changed", self.on_icon_changed)

        self.img_icon_preview = Gtk.Image.new_from_icon_name("application-x-executable")
        self.img_icon_preview.set_pixel_size(32)
        self.img_icon_preview.set_valign(Gtk.Align.CENTER)
        self.row_icon.add_prefix(self.img_icon_preview)

        btn_browse_icon = Gtk.Button(icon_name="folder-open-symbolic")
        btn_browse_icon.set_valign(Gtk.Align.CENTER)
        btn_browse_icon.set_tooltip_text("Buscar imagen de icono...")
        btn_browse_icon.connect("clicked", self.on_browse_icon_clicked)
        self.row_icon.add_suffix(btn_browse_icon)
        grp_icon.add(self.row_icon)

        self.switch_startup = Adw.SwitchRow(title="Notificación de inicio (StartupNotify)")
        self.switch_startup.set_subtitle("Muestra indicador de carga mientras inicia la aplicación")
        self.switch_startup.set_active(True)
        self.switch_startup.connect("notify::active", self.on_form_field_changed)
        grp_icon.add(self.switch_startup)

        self.switch_nodisplay = Adw.SwitchRow(title="Ocultar en el menú de aplicaciones (NoDisplay)")
        self.switch_nodisplay.set_subtitle("Si está activo, no aparecerá en el menú del sistema")
        self.switch_nodisplay.connect("notify::active", self.on_form_field_changed)
        grp_icon.add(self.switch_nodisplay)

        # --- GRUPO 4: Categorías ---
        grp_cat = Adw.PreferencesGroup(title="Categorías", description="Permite clasificar la aplicación en el menú")
        pref_page.add(grp_cat)

        cat_grid = Gtk.FlowBox()
        cat_grid.set_valign(Gtk.Align.START)
        cat_grid.set_max_children_per_line(2)
        cat_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        cat_grid.set_homogeneous(True)
        cat_grid.set_column_spacing(12)
        cat_grid.set_row_spacing(8)

        for code, label_text in STANDARD_CATEGORIES:
            chk = Gtk.CheckButton(label=label_text)
            chk.connect("toggled", self.on_form_field_changed)
            self.category_checks[code] = chk
            cat_grid.append(chk)

        grp_cat.add(cat_grid)

        self.row_custom_cat = Adw.EntryRow(title="Categorías adicionales / personalizadas")
        self.row_custom_cat.set_tooltip_text("Separadas por coma o punto y coma")
        self.row_custom_cat.connect("changed", self.on_form_field_changed)
        grp_cat.add(self.row_custom_cat)

        # --- GRUPO 5: Avanzado ---
        grp_adv = Adw.PreferencesGroup(title="Opciones Avanzadas", description="Palabras clave para búsqueda y tipos MIME")
        pref_page.add(grp_adv)

        self.row_keywords = Adw.EntryRow(title="Palabras clave (Keywords)")
        self.row_keywords.set_tooltip_text("Separadas por comas (ej: editor, codigo, texto)")
        self.row_keywords.connect("changed", self.on_form_field_changed)
        grp_adv.add(self.row_keywords)

        self.row_mime = Adw.EntryRow(title="Tipos MIME (MimeType)")
        self.row_mime.set_tooltip_text("Tipos de archivo asociados (ej: text/plain;application/pdf)")
        self.row_mime.connect("changed", self.on_form_field_changed)
        grp_adv.add(self.row_mime)

        page_form = self.view_stack.add_titled(pref_page, "form", "Formulario")
        page_form.set_icon_name("document-properties-symbolic")

    def setup_preview_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        # Toolbar above preview
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label="<b>Contenido generado del archivo .desktop</b>", use_markup=True)
        lbl.set_hexpand(True)
        lbl.set_halign(Gtk.Align.START)
        tb.append(lbl)

        btn_copy = Gtk.Button(icon_name="edit-copy-symbolic", label="Copiar")
        btn_copy.connect("clicked", self.on_copy_preview_clicked)
        tb.append(btn_copy)

        box.append(tb)

        # Text View for preview
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        self.text_preview = Gtk.TextView()
        self.text_preview.set_editable(False)
        self.text_preview.set_monospace(True)
        self.text_preview.set_left_margin(12)
        self.text_preview.set_right_margin(12)
        self.text_preview.set_top_margin(12)
        self.text_preview.set_bottom_margin(12)
        scrolled.set_child(self.text_preview)

        box.append(scrolled)

        page_preview = self.view_stack.add_titled(box, "preview", "Vista Previa")
        page_preview.set_icon_name("code-context-symbolic")

    def setup_manager_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl = Gtk.Label(label="<b>Accesos Directos Personales</b> (~/.local/share/applications)", use_markup=True)
        lbl.set_hexpand(True)
        lbl.set_halign(Gtk.Align.START)
        header_box.append(lbl)

        btn_refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Actualizar lista")
        btn_refresh.connect("clicked", lambda b: self.refresh_manager_list())
        header_box.append(btn_refresh)

        box.append(header_box)

        # Search bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar accesos directos...")
        self.search_entry.connect("search-changed", self.on_manager_search_changed)
        box.append(self.search_entry)

        # List box inside scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.manager_listbox = Gtk.ListBox()
        self.manager_listbox.add_css_class("boxed-list")
        self.manager_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.set_child(self.manager_listbox)

        box.append(scrolled)

        page_manager = self.view_stack.add_titled(box, "manager", "Mis Accesos")
        page_manager.set_icon_name("application-x-executable-symbolic")

    def get_form_data(self):
        name = self.row_name.get_text()
        generic = self.row_generic.get_text()
        comment = self.row_comment.get_text()
        exec_cmd = self.row_exec.get_text()
        icon = self.row_icon.get_text()
        path = self.row_path.get_text()
        terminal = self.switch_terminal.get_active()
        startup = self.switch_startup.get_active()
        nodisplay = self.switch_nodisplay.get_active()

        categories = [code for code, chk in self.category_checks.items() if chk.get_active()]
        custom_cat = self.row_custom_cat.get_text()
        if custom_cat:
            for c in custom_cat.replace(";", ",").split(","):
                c_clean = c.strip()
                if c_clean and c_clean not in categories:
                    categories.append(c_clean)

        keywords = [k.strip() for k in self.row_keywords.get_text().replace(";", ",").split(",") if k.strip()]
        mimes = [m.strip() for m in self.row_mime.get_text().replace(";", ",").split(",") if m.strip()]

        return {
            "name": name,
            "generic_name": generic,
            "comment": comment,
            "exec": exec_cmd,
            "icon": icon,
            "path": path,
            "terminal": terminal,
            "startup_notify": startup,
            "no_display": nodisplay,
            "categories": categories,
            "keywords": keywords,
            "mime_types": mimes,
        }

    def update_preview_text(self):
        data = self.get_form_data()
        content = build_desktop_content(data)
        buffer = self.text_preview.get_buffer()
        buffer.set_text(content)

    def load_form_data(self, data):
        self.row_name.set_text(data.get("name", ""))
        self.row_generic.set_text(data.get("generic_name", ""))
        self.row_comment.set_text(data.get("comment", ""))
        self.row_exec.set_text(data.get("exec", ""))
        self.row_icon.set_text(data.get("icon", ""))
        self.row_path.set_text(data.get("path", ""))

        self.switch_terminal.set_active(data.get("terminal", False))
        self.switch_startup.set_active(data.get("startup_notify", True))
        self.switch_nodisplay.set_active(data.get("no_display", False))

        cats = data.get("categories", [])
        custom = []
        for code, chk in self.category_checks.items():
            if code in cats:
                chk.set_active(True)
            else:
                chk.set_active(False)
        for c in cats:
            if c not in self.category_checks:
                custom.append(c)
        self.row_custom_cat.set_text(", ".join(custom))

        self.row_keywords.set_text(", ".join(data.get("keywords", [])))
        self.row_mime.set_text("; ".join(data.get("mime_types", [])))

        self.update_icon_preview()
        self.update_preview_text()

    def update_icon_preview(self):
        icon_str = self.row_icon.get_text().strip()
        if not icon_str:
            self.img_icon_preview.set_from_icon_name("application-x-executable")
        elif os.path.exists(icon_str):
            self.img_icon_preview.set_from_file(icon_str)
        else:
            self.img_icon_preview.set_from_icon_name(icon_str)

    # --- Callbacks ---
    def on_form_field_changed(self, *args):
        self.update_preview_text()

    def on_icon_changed(self, *args):
        self.update_icon_preview()
        self.update_preview_text()

    def on_stack_changed(self, stack, pspec):
        visible_child = stack.get_visible_child_name()
        if visible_child == "preview":
            self.update_preview_text()
        elif visible_child == "manager":
            self.refresh_manager_list()

    def on_copy_preview_clicked(self, btn):
        buffer = self.text_preview.get_buffer()
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True)
        clipboard = self.get_clipboard()
        clipboard.set(text)
        self.show_toast("Contenido copiado al portapapeles")

    def on_new_clicked(self, btn):
        self.current_filepath = None
        self.load_form_data({
            "name": "", "generic_name": "", "comment": "", "exec": "",
            "icon": "", "path": "", "terminal": False, "startup_notify": True,
            "no_display": False, "categories": [], "keywords": [], "mime_types": []
        })
        self.show_toast("Formulario limpiado")

    def on_browse_exec_clicked(self, btn):
        chooser = Gtk.FileChooserNative.new(
            "Seleccionar Ejecutable o Script",
            self,
            Gtk.FileChooserAction.OPEN,
            "Seleccionar",
            "Cancelar"
        )
        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                if file:
                    self.row_exec.set_text(file.get_path())
            dialog.destroy()
        chooser.connect("response", on_response)
        chooser.show()

    def on_browse_path_clicked(self, btn):
        chooser = Gtk.FileChooserNative.new(
            "Seleccionar Directorio de Trabajo",
            self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            "Seleccionar",
            "Cancelar"
        )
        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                if file:
                    self.row_path.set_text(file.get_path())
            dialog.destroy()
        chooser.connect("response", on_response)
        chooser.show()

    def on_browse_icon_clicked(self, btn):
        chooser = Gtk.FileChooserNative.new(
            "Seleccionar Imagen de Icono",
            self,
            Gtk.FileChooserAction.OPEN,
            "Seleccionar",
            "Cancelar"
        )
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Imágenes (*.png, *.svg, *.xpm, *.ico)")
        filter_img.add_mime_type("image/png")
        filter_img.add_mime_type("image/svg+xml")
        filter_img.add_mime_type("image/x-icon")
        filter_img.add_pattern("*.png")
        filter_img.add_pattern("*.svg")
        filter_img.add_pattern("*.ico")
        chooser.add_filter(filter_img)

        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                if file:
                    self.row_icon.set_text(file.get_path())
            dialog.destroy()
        chooser.connect("response", on_response)
        chooser.show()

    def on_test_exec_clicked(self, btn):
        cmd = self.row_exec.get_text().strip()
        if not cmd:
            self.show_toast("Ingresa un comando en Exec para probar")
            return
        work_dir = self.row_path.get_text().strip() or None
        if self.switch_terminal.get_active():
            # Run in gnome-terminal or x-terminal-emulator if possible
            test_cmd = f"gnome-terminal -- bash -c {shlex.quote(cmd + '; echo \"-- Presiona Enter para cerrar --\"; read')}"
        else:
            test_cmd = cmd

        try:
            subprocess.Popen(test_cmd, shell=True, cwd=work_dir)
            self.show_toast(f"Ejecutando: {cmd}")
        except Exception as e:
            self.show_toast(f"Error al ejecutar: {e}")

    def on_open_clicked(self, btn):
        chooser = Gtk.FileChooserNative.new(
            "Abrir Archivo .desktop",
            self,
            Gtk.FileChooserAction.OPEN,
            "Abrir",
            "Cancelar"
        )
        filter_desktop = Gtk.FileFilter()
        filter_desktop.set_name("Archivos Desktop (*.desktop)")
        filter_desktop.add_pattern("*.desktop")
        chooser.add_filter(filter_desktop)

        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                if file:
                    path = file.get_path()
                    try:
                        data = parse_desktop_file(path)
                        self.load_form_data(data)
                        self.current_filepath = path
                        self.show_toast(f"Cargado: {os.path.basename(path)}")
                    except Exception as e:
                        self.show_toast(f"Error al leer archivo: {e}")
            dialog.destroy()

        chooser.connect("response", on_response)
        chooser.show()

    def on_save_system_clicked(self, btn):
        data = self.get_form_data()
        if not data["name"]:
            self.show_toast("¡Error! El campo Nombre es obligatorio")
            return
        if not data["exec"]:
            self.show_toast("¡Error! El campo Comando / Exec es obligatorio")
            return

        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in data["name"]).lower()
        filename = f"{safe_name}.desktop"
        apps_dir = get_user_applications_dir()
        target_path = os.path.join(apps_dir, filename)

        try:
            save_desktop_file(target_path, data)
            valid, msg = validate_desktop_file(target_path)
            self.show_toast(f" Guardado en sistema: {filename}")
            # Refresh desktop database
            subprocess.run(["update-desktop-database", apps_dir], capture_output=True)
        except Exception as e:
            self.show_toast(f"Error al guardar: {e}")

    def on_export_clicked(self, btn):
        data = self.get_form_data()
        if not data["name"]:
            self.show_toast("¡Error! El campo Nombre es obligatorio")
            return

        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in data["name"]).lower()
        chooser = Gtk.FileChooserNative.new(
            "Exportar Archivo .desktop",
            self,
            Gtk.FileChooserAction.SAVE,
            "Guardar",
            "Cancelar"
        )
        chooser.set_current_name(f"{safe_name}.desktop")

        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                if file:
                    path = file.get_path()
                    save_desktop_file(path, data)
                    self.show_toast(f"Exportado correctamente a: {os.path.basename(path)}")
            dialog.destroy()

        chooser.connect("response", on_response)
        chooser.show()

    # --- Manager Tab Logic ---
    def refresh_manager_list(self):
        # Clear existing list
        while True:
            child = self.manager_listbox.get_first_child()
            if not child:
                break
            self.manager_listbox.remove(child)

        apps_dir = get_user_applications_dir()
        search_query = self.search_entry.get_text().lower().strip()

        if not os.path.exists(apps_dir):
            return

        files = sorted(os.listdir(apps_dir))
        count = 0

        for fname in files:
            if not fname.endswith(".desktop"):
                continue

            filepath = os.path.join(apps_dir, fname)
            try:
                data = parse_desktop_file(filepath)
            except Exception:
                continue

            name = data.get("name") or fname
            exec_cmd = data.get("exec", "")
            icon_name = data.get("icon", "application-x-executable")

            # Filter by search
            if search_query and (search_query not in name.lower() and search_query not in exec_cmd.lower() and search_query not in fname.lower()):
                continue

            row = Adw.ActionRow(title=name, subtitle=f"Exec: {exec_cmd}")

            # Icon
            img = Gtk.Image()
            if os.path.exists(icon_name):
                img.set_from_file(icon_name)
            else:
                img.set_from_icon_name(icon_name if icon_name else "application-x-executable")
            img.set_pixel_size(24)
            row.add_prefix(img)

            # Edit button
            btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
            btn_edit.set_valign(Gtk.Align.CENTER)
            btn_edit.set_tooltip_text("Cargar en el formulario para editar")
            btn_edit.connect("clicked", self.make_edit_handler(filepath, data))
            row.add_suffix(btn_edit)

            # Delete button
            btn_delete = Gtk.Button(icon_name="user-trash-symbolic")
            btn_delete.set_valign(Gtk.Align.CENTER)
            btn_delete.add_css_class("destructive-action")
            btn_delete.set_tooltip_text("Eliminar este acceso directo")
            btn_delete.connect("clicked", self.make_delete_handler(filepath, name))
            row.add_suffix(btn_delete)

            self.manager_listbox.append(row)
            count += 1

        if count == 0:
            row_empty = Adw.ActionRow(title="No se encontraron accesos directos", subtitle="Puedes crear uno nuevo usando la pestaña Formulario")
            self.manager_listbox.append(row_empty)

    def make_edit_handler(self, filepath, data):
        def handler(btn):
            self.load_form_data(data)
            self.current_filepath = filepath
            self.view_stack.set_visible_child_name("form")
            self.show_toast(f"Editando: {data.get('name')}")
        return handler

    def make_delete_handler(self, filepath, name):
        def handler(btn):
            try:
                os.remove(filepath)
                self.show_toast(f"Eliminado: {name}")
                self.refresh_manager_list()
                apps_dir = get_user_applications_dir()
                subprocess.run(["update-desktop-database", apps_dir], capture_output=True)
            except Exception as e:
                self.show_toast(f"Error al eliminar: {e}")
        return handler

    def on_manager_search_changed(self, entry):
        self.refresh_manager_list()


class DesktopCreatorApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.desktop_creator",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = DesktopCreatorWindow(application=self)
        win.present()


def main():
    app = DesktopCreatorApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
