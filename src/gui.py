import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from automaton import Automaton, EPSILON_SYMBOLS
from parsing import parse_json_automaton, parse_xml_automaton, automaton_to_json_dict, automaton_to_xml_element
from conversion import nfa_to_dfa, hopcroft_minimize
from visualization import AutomatonVisualizer

def write_automaton(a: Automaton, path: str, fmt: str = None) -> None:
    import os, json, xml.etree.ElementTree as ET
    def detect_format_from_ext(path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".json", ".jsn"):
            return "json"
        if ext in (".xml",):
            return "xml"
        return "json"
    fmt = fmt or detect_format_from_ext(path)
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    if fmt == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(automaton_to_json_dict(a), f, ensure_ascii=False, indent=2)
    elif fmt == "xml":
        root = automaton_to_xml_element(a)
        tree = ET.ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

class AutomatonGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor de AFN a AFD")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.nfa = None
        self.dfa = None
        self.minimized_dfa = None
        self.setup_ui()
    def on_closing(self):
        try:
            plt.close('all')
        except:
            pass
        self.root.quit()
        self.root.destroy()
    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        control_frame = ttk.LabelFrame(main_frame, text="Controles")
        control_frame.pack(fill='x', pady=(0, 10))
        ttk.Button(control_frame, text="Cargar AFN (JSON)", command=lambda: self.load_file('json')).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Cargar AFN (XML)", command=lambda: self.load_file('xml')).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Convertir a AFD", command=self.convert_to_dfa).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Minimizar AFD", command=self.minimize_dfa).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Guardar resultado (JSON)", command=lambda: self.save_file('json')).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Guardar resultado (XML)", command=lambda: self.save_file('xml')).pack(side='left', padx=5, pady=5)
        self.string_var = tk.StringVar()
        ttk.Label(control_frame, text="Cadena:").pack(side='left', padx=5)
        ttk.Entry(control_frame, textvariable=self.string_var, width=20).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Validar Cadena", command=self.on_validate_string).pack(side='left', padx=5, pady=5)
        self.use_readable_names = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Mostrar nombres legibles de estados", variable=self.use_readable_names, command=self.refresh_visualization).pack(side='right', padx=5, pady=5)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        self.setup_info_tab()
        self.setup_visualization_tab()
    def setup_info_tab(self):
        info_frame = ttk.Frame(self.notebook)
        self.notebook.add(info_frame, text="Información")
        self.info_text = tk.Text(info_frame, wrap='word', font=('Courier', 10))
        info_scrollbar = ttk.Scrollbar(info_frame, orient='vertical', command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scrollbar.set)
        self.info_text.pack(side='left', fill='both', expand=True)
        info_scrollbar.pack(side='right', fill='y')
    def setup_visualization_tab(self):
        viz_frame = ttk.Frame(self.notebook)
        self.notebook.add(viz_frame, text="Visualización")
        self.fig, self.axes = plt.subplots(1, 3, figsize=(15, 5))
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, viz_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
    def load_file(self, file_format):
        file_types = [("Archivos JSON", "*.json")] if file_format == 'json' else [("Archivos XML", "*.xml")]
        file_path = filedialog.askopenfilename(filetypes=file_types)
        if not file_path:
            return
        try:
            if file_format == 'json':
                self.nfa = parse_json_automaton(file_path)
            else:
                self.nfa = parse_xml_automaton(file_path)
            self.dfa = None
            self.minimized_dfa = None
            self.update_info()
            self.refresh_visualization()
            messagebox.showinfo("Éxito", f"AFN cargado correctamente desde {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar el archivo: {str(e)}")
    def convert_to_dfa(self):
        if not self.nfa:
            messagebox.showwarning("Advertencia", "Por favor, carga un AFN primero")
            return
        try:
            self.dfa = nfa_to_dfa(self.nfa)
            self.minimized_dfa = None
            self.update_info()
            self.refresh_visualization()
            messagebox.showinfo("Éxito", "AFN convertido a AFD correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error al convertir: {str(e)}")
    def minimize_dfa(self):
        if not self.dfa:
            messagebox.showwarning("Advertencia", "Por favor, convierte a AFD primero")
            return
        try:
            self.minimized_dfa = hopcroft_minimize(self.dfa)
            self.update_info()
            self.refresh_visualization()
            messagebox.showinfo("Éxito", "AFD minimizado correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error al minimizar: {str(e)}")
    def save_file(self, file_format):
        if not self.minimized_dfa and not self.dfa:
            messagebox.showwarning("Advertencia", "No hay autómata para guardar")
            return
        result_automaton = self.minimized_dfa if self.minimized_dfa else self.dfa
        file_types = [("Archivos JSON", "*.json")] if file_format == 'json' else [("Archivos XML", "*.xml")]
        file_path = filedialog.asksaveasfilename(filetypes=file_types, defaultextension=f".{file_format}")
        if not file_path:
            return
        try:
            write_automaton(result_automaton, file_path, file_format)
            messagebox.showinfo("Éxito", f"Autómata guardado en {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    def update_info(self):
        self.info_text.delete(1.0, tk.END)
        info_lines = []
        if self.nfa:
            info_lines.append("=== AFN ORIGINAL ===")
            info_lines.append(f"Nombre: {self.nfa.name}")
            stats = self.nfa.get_stats()
            info_lines.append(f"Estados: {stats['states']}")
            info_lines.append(f"Alfabeto: {sorted(self.nfa.alphabet)}")
            info_lines.append(f"Estado inicial: {self.nfa.start_state}")
            info_lines.append(f"Estados de aceptación: {sorted(self.nfa.accept_states)}")
            info_lines.append(f"Transiciones totales: {stats['total_transitions']}")
            info_lines.append(f"Transiciones épsilon: {stats['epsilon_transitions']}")
            info_lines.append(f"¿Es AFD?: {stats['is_dfa']}")
            info_lines.append("")
            info_lines.append("Transiciones:")
            for state in sorted(self.nfa.states):
                if state in self.nfa.transitions:
                    for symbol, destinations in sorted(self.nfa.transitions[state].items()):
                        dest_str = ", ".join(sorted(destinations))
                        symbol_display = symbol if symbol not in EPSILON_SYMBOLS else "ε"
                        info_lines.append(f"  {state} --{symbol_display}--> {dest_str}")
            info_lines.append("")
        if self.dfa:
            info_lines.append("=== AFD CONVERTIDO ===")
            info_lines.append(f"Nombre: {self.dfa.name}")
            stats = self.dfa.get_stats()
            info_lines.append(f"Estados: {stats['states']}")
            info_lines.append(f"Alfabeto: {sorted(self.dfa.alphabet)}")
            info_lines.append(f"Estado inicial: {self.dfa.start_state}")
            info_lines.append(f"Estados de aceptación: {sorted(self.dfa.accept_states)}")
            info_lines.append(f"Transiciones totales: {stats['total_transitions']}")
            info_lines.append("")
            if self.dfa.state_composition:
                info_lines.append("Composición de estados (estado AFD -> estados originales AFN):")
                for dfa_state in sorted(self.dfa.states):
                    if dfa_state in self.dfa.state_composition:
                        nfa_states = sorted(self.dfa.state_composition[dfa_state])
                        readable_name = self.dfa.get_readable_state_name(dfa_state)
                        info_lines.append(f"  {readable_name}: {{{', '.join(nfa_states)}}}")
                info_lines.append("")
            info_lines.append("Transiciones del AFD:")
            for state in sorted(self.dfa.states):
                if state in self.dfa.transitions:
                    for symbol, destinations in sorted(self.dfa.transitions[state].items()):
                        dest_str = ", ".join(sorted(destinations))
                        readable_from = self.dfa.get_readable_state_name(state)
                        readable_to = ", ".join([self.dfa.get_readable_state_name(d) for d in sorted(destinations)])
                        info_lines.append(f"  {readable_from} --{symbol}--> {readable_to}")
            info_lines.append("")
        if self.minimized_dfa:
            info_lines.append("=== AFD MINIMIZADO ===")
            info_lines.append(f"Nombre: {self.minimized_dfa.name}")
            stats = self.minimized_dfa.get_stats()
            info_lines.append(f"Estados: {stats['states']}")
            info_lines.append(f"Alfabeto: {sorted(self.minimized_dfa.alphabet)}")
            info_lines.append(f"Estado inicial: {self.minimized_dfa.start_state}")
            info_lines.append(f"Estados de aceptación: {sorted(self.minimized_dfa.accept_states)}")
            info_lines.append(f"Transiciones totales: {stats['total_transitions']}")
            info_lines.append("")
            if self.minimized_dfa.state_composition:
                info_lines.append("Composición de estados minimizados (estado MIN -> estados originales AFN):")
                for min_state in sorted(self.minimized_dfa.states):
                    if min_state in self.minimized_dfa.state_composition:
                        nfa_states = sorted(self.minimized_dfa.state_composition[min_state])
                        readable_name = self.minimized_dfa.get_readable_state_name(min_state)
                        info_lines.append(f"  {readable_name}: {{{', '.join(nfa_states)}}}")
                info_lines.append("")
            info_lines.append("Transiciones del AFD minimizado:")
            for state in sorted(self.minimized_dfa.states):
                if state in self.minimized_dfa.transitions:
                    for symbol, destinations in sorted(self.minimized_dfa.transitions[state].items()):
                        readable_from = self.minimized_dfa.get_readable_state_name(state)
                        readable_to = ", ".join([self.minimized_dfa.get_readable_state_name(d) for d in sorted(destinations)])
                        info_lines.append(f"  {readable_from} --{symbol}--> {readable_to}")
        self.info_text.insert(tk.END, "\n".join(info_lines))
    def refresh_visualization(self):
        for ax in self.axes:
            ax.clear()
        use_readable = self.use_readable_names.get()
        if self.nfa:
            visualizer = AutomatonVisualizer(self.nfa)
            visualizer.plot(self.axes[0], "AFN original", use_readable)
        if self.dfa:
            visualizer = AutomatonVisualizer(self.dfa)
            visualizer.plot(self.axes[1], "AFD convertido", use_readable)
        if self.minimized_dfa:
            visualizer = AutomatonVisualizer(self.minimized_dfa)
            visualizer.plot(self.axes[2], "AFD minimizado", use_readable)
        if not self.minimized_dfa:
            self.axes[2].text(0.5, 0.5, "Aún no hay AFD minimizado", ha='center', va='center', transform=self.axes[2].transAxes)
            self.axes[2].set_title("AFD minimizado")
        self.fig.tight_layout()
        self.canvas.draw()

    def on_validate_string(self):
        input_string = self.string_var.get().strip()
        if not input_string:
            messagebox.showwarning("Advertencia", "Por favor, ingresa una cadena para validar.")
            return

        # Usar el autómata más avanzado disponible
        automaton_to_use = self.minimized_dfa or self.dfa or self.nfa
        if not automaton_to_use:
            messagebox.showwarning("Advertencia", "No hay un autómata cargado para validar la cadena.")
            return

        try:
            result = self.validate_string(automaton_to_use, input_string)
            if result:
                messagebox.showinfo("Resultado", f"La cadena '{input_string}' ES ACEPTADA por el autómata.")
            else:
                messagebox.showinfo("Resultado", f"La cadena '{input_string}' NO es aceptada por el autómata.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def validate_string(self, automaton: Automaton, input_string: str) -> bool:
        current_state = automaton.start_state
        for symbol in input_string:
            if symbol not in automaton.alphabet:
                raise ValueError(f"Símbolo '{symbol}' no está en el alfabeto del autómata.")
            if current_state in automaton.transitions and symbol in automaton.transitions[current_state]:
                current_state = next(iter(automaton.transitions[current_state][symbol]))
            else:
                return False  # No hay transición válida
        return current_state in automaton.accept_states




   
