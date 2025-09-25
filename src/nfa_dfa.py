"""
Este archivo ha sido migrado a una estructura modular.
Usa los archivos automaton.py, parsing.py, conversion.py, visualization.py, gui.py y main.py.
"""

# =====================
# Parsing / Serialization
# =====================

def parse_json_automaton(path: str) -> Automaton:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    states = set(data["states"])
    alphabet = set(data.get("alphabet", []))
    start_state = data["start_state"]
    accept_states = set(data["accept_states"])

    raw_trans = data.get("transitions", {})
    transitions: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

    for s, symbol_map in raw_trans.items():
        for sym, dests in symbol_map.items():
            if isinstance(dests, str):
                dests = [dests]
            for d in dests:
                transitions[s][sym].add(d)
            if sym not in EPSILON_SYMBOLS:
                alphabet.add(sym)

    name = data.get("name", os.path.splitext(os.path.basename(path))[0])
    
    # Normalizar estados mencionados en transiciones
    mentioned_states = set(transitions.keys())
    for s in list(transitions.keys()):
        for sym in transitions[s].keys():
            mentioned_states.update(transitions[s][sym])
    states |= mentioned_states

    # Detectar si es DFA
    is_dfa = all(
        (sym not in EPSILON_SYMBOLS) and len(dests) == 1
        for s in transitions
        for sym, dests in transitions[s].items()
    )

    return Automaton(states, alphabet, start_state, accept_states, transitions, is_dfa, name)


def parse_xml_automaton(path: str) -> Automaton:
    tree = ET.parse(path)
    root = tree.getroot()

    def findall(elem, *names):
        for n in names:
            found = elem.findall(n)
            if found:
                return found
        return []

    def findone(elem, *names):
        for n in names:
            f = elem.find(n)
            if f is not None:
                return f
        return None

    name = root.attrib.get("name") or os.path.splitext(os.path.basename(path))[0]

    state_nodes = findall(root, "states/state", "States/State", "stateSet/state")
    states = {n.text.strip() for n in state_nodes if n.text}

    alpha_nodes = findall(root, "alphabet/symbol", "Alphabet/Symbol", "alphabet/char", "Alphabet/Char")
    alphabet = {n.text.strip() for n in alpha_nodes if n is not None and n.text}

    start_node = findone(root, "start", "Start")
    if start_node is None or not start_node.text:
        raise ValueError("XML missing <start> node with start state text")
    start_state = start_node.text.strip()

    accept_nodes = findall(root, "accept/state", "Accept/State", "finals/state")
    accept_states = {n.text.strip() for n in accept_nodes if n.text}

    transitions: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    t_nodes = findall(root, "transitions/t", "Transitions/T", "transitions/transition", "Transitions/Transition")

    for t in t_nodes:
        frm = t.attrib.get("from") or (t.findtext("from") or t.findtext("From"))
        sym = t.attrib.get("symbol") or (t.findtext("symbol") or t.findtext("Symbol"))
        to = t.attrib.get("to") or (t.findtext("to") or t.findtext("To"))
        if frm is None or to is None:
            continue
        frm, to = frm.strip(), to.strip()
        sym = (sym or "").strip()
        transitions[frm][sym].add(to)
        if sym and sym not in EPSILON_SYMBOLS:
            alphabet.add(sym)

    # Normalizar estados mencionados
    mentioned_states = set(transitions.keys())
    for s in list(transitions.keys()):
        for sym in transitions[s].keys():
            mentioned_states.update(transitions[s][sym])
    states |= mentioned_states

    is_dfa = all(
        (sym not in EPSILON_SYMBOLS) and len(dests) == 1
        for s in transitions
        for sym, dests in transitions[s].items()
    )

    return Automaton(states, alphabet, start_state, accept_states, transitions, is_dfa, name)


def automaton_to_json_dict(a: Automaton) -> dict:
    # Convertir transiciones a listas/strings para JSON
    trans_dict = {}
    for s in sorted(a.states):
        sym_map = a.transitions.get(s, {})
        if not sym_map:
            continue
        out = {}
        for sym, dests in sym_map.items():
            if len(dests) == 1:
                out[sym] = sorted(dests)[0]
            else:
                out[sym] = sorted(dests)
        trans_dict[s] = out

    result = {
        "name": a.name,
        "states": sorted(a.states),
        "alphabet": sorted(a.alphabet),
        "start_state": a.start_state,
        "accept_states": sorted(a.accept_states),
        "is_dfa": a.is_dfa,
        "transitions": trans_dict,
    }
    
    # Agregar composición de estados si existe
    if a.state_composition:
        result["state_composition"] = {
            state: sorted(composition) 
            for state, composition in a.state_composition.items()
        }
    
    return result


def automaton_to_xml_element(a: Automaton) -> ET.Element:
    root = ET.Element("automaton", attrib={"name": a.name})
    states_el = ET.SubElement(root, "states")
    for s in sorted(a.states):
        state_el = ET.SubElement(states_el, "state")
        state_el.text = s
        # Agregar composición como atributo si existe
        if s in a.state_composition:
            state_el.set("composition", ",".join(sorted(a.state_composition[s])))

    alpha_el = ET.SubElement(root, "alphabet")
    for sym in sorted(a.alphabet):
        ET.SubElement(alpha_el, "symbol").text = sym

    ET.SubElement(root, "start").text = a.start_state

    accept_el = ET.SubElement(root, "accept")
    for s in sorted(a.accept_states):
        ET.SubElement(accept_el, "state").text = s

    trans_el = ET.SubElement(root, "transitions")
    for s in sorted(a.states):
        sym_map = a.transitions.get(s, {})
        for sym, dests in sorted(sym_map.items()):
            for d in sorted(dests):
                t = ET.SubElement(trans_el, "t")
                t.set("from", s)
                t.set("symbol", sym)
                t.set("to", d)

    return root


# =====================
# NFA -> DFA Conversion with readable state names
# =====================

def epsilon_closure(state_set: Set[str], transitions: Dict[str, Dict[str, Set[str]]]) -> Set[str]:
    stack = list(state_set)
    closure = set(state_set)
    while stack:
        s = stack.pop()
        for eps_sym in EPSILON_SYMBOLS:
            for nxt in transitions.get(s, {}).get(eps_sym, set()):
                if nxt not in closure:
                    closure.add(nxt)
                    stack.append(nxt)
    return closure


def move(state_set: Set[str], symbol: str, transitions: Dict[str, Dict[str, Set[str]]]) -> Set[str]:
    result = set()
    for s in state_set:
        result |= transitions.get(s, {}).get(symbol, set())
    return result


def nfa_to_dfa(nfa: Automaton, name_suffix="__DFA") -> Automaton:
    if nfa.is_dfa and all(sym not in EPSILON_SYMBOLS for s in nfa.transitions for sym in nfa.transitions[s]):
        dfa = nfa.copy()
        dfa.name = f"{dfa.name}{name_suffix}"
        return dfa

    alphabet = set([sym for sym in nfa.alphabet if sym not in EPSILON_SYMBOLS])

    start_closure = frozenset(sorted(epsilon_closure({nfa.start_state}, nfa.transitions)))
    
    # Mapeo de conjuntos de estados NFA a nombres de estados DFA
    state_name = {start_closure: "S0"}
    state_composition = {"S0": set(start_closure)}  # Para nombres legibles

    queue = deque([start_closure])
    dfa_states: Set[str] = {"S0"}
    dfa_trans: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    dfa_accepts: Set[str] = set()

    if any(s in nfa.accept_states for s in start_closure):
        dfa_accepts.add("S0")

    idx = 1
    while queue:
        T = queue.popleft()
        T_name = state_name[T]
        for a in alphabet:
            U = set()
            U |= move(set(T), a, nfa.transitions)
            U = epsilon_closure(U, nfa.transitions)
            U_f = frozenset(sorted(U))
            if not U_f:
                continue
            if U_f not in state_name:
                new_name = f"S{idx}"
                state_name[U_f] = new_name
                state_composition[new_name] = set(U_f)
                dfa_states.add(new_name)
                queue.append(U_f)
                if any(s in nfa.accept_states for s in U_f):
                    dfa_accepts.add(new_name)
                idx += 1
            dfa_trans[T_name][a].add(state_name[U_f])

    # Asegurar determinismo
    for s in dfa_trans:
        for a in list(dfa_trans[s].keys()):
            dests = dfa_trans[s][a]
            if len(dests) > 1:
                dfa_trans[s][a] = {sorted(dests)[0]}

    dfa = Automaton(
        states=dfa_states,
        alphabet=alphabet,
        start_state="S0",
        accept_states=dfa_accepts,
        transitions=dfa_trans,
        is_dfa=True,
        name=f"{nfa.name}{name_suffix}",
        state_composition=state_composition,
    )
    dfa = remove_unreachable_states(dfa)
    return dfa


def remove_unreachable_states(dfa: Automaton) -> Automaton:
    reachable = set()
    stack = [dfa.start_state]
    while stack:
        s = stack.pop()
        if s in reachable:
            continue
        reachable.add(s)
        for a in dfa.alphabet:
            for d in dfa.transitions.get(s, {}).get(a, set()):
                if d not in reachable:
                    stack.append(d)
    
    # Filtrar
    dfa.states &= reachable
    dfa.accept_states &= reachable
    dfa.transitions = {
        s: {
            a: {d for d in dfa.transitions.get(s, {}).get(a, set()) if d in reachable}
            for a in dfa.alphabet if a in dfa.transitions.get(s, {})
        }
        for s in dfa.states
    }
    
    # Filtrar composición de estados
    dfa.state_composition = {
        s: comp for s, comp in dfa.state_composition.items() if s in reachable
    }
    
    return dfa


# =====================
# DFA Minimization (Hopcroft)
# =====================

def hopcroft_minimize(dfa: Automaton, name_suffix="__MIN") -> Automaton:
    if not dfa.is_dfa:
        raise ValueError("hopcroft_minimize requiere un DFA")

    dfa = remove_unreachable_states(dfa)

    # Partición inicial: aceptadores vs no-aceptadores
    P = [set(dfa.accept_states), set(dfa.states - dfa.accept_states)]
    P = [p for p in P if p]

    from collections import deque as _deque
    W = _deque()
    if P:
        if len(P) == 2 and len(P[0]) > len(P[1]):
            W.append(P[1])
        else:
            W.append(P[0])

    def get_transition(state: str, symbol: str) -> str:
        dests = dfa.transitions.get(state, {}).get(symbol, set())
        return next(iter(dests), None)

    while W:
        A = W.popleft()
        for c in dfa.alphabet:
            X = set(s for s in dfa.states if get_transition(s, c) in A)
            new_P = []
            for Y in P:
                inter = Y & X
                diff = Y - X
                if inter and diff:
                    new_P.extend([inter, diff])
                    if Y in W:
                        W.remove(Y)
                        W.append(inter)
                        W.append(diff)
                    else:
                        if len(inter) <= len(diff):
                            W.append(inter)
                        else:
                            W.append(diff)
                else:
                    new_P.append(Y)
            P = new_P

    # Construir nuevo DFA desde P
    block_names = {}
    block_composition = {}
    for i, block in enumerate(P):
        name = f"M{i}"
        # La composición del bloque incluye todas las composiciones originales
        combined_composition = set()
        for s in block:
            block_names[s] = name
            if s in dfa.state_composition:
                combined_composition.update(dfa.state_composition[s])
            else:
                combined_composition.add(s)
        block_composition[name] = combined_composition

    new_states = set(block_names.values())
    new_start = block_names[dfa.start_state]
    new_accepts = {block_names[s] for s in dfa.accept_states}

    new_trans: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    for s in dfa.states:
        s2 = block_names[s]
        for a in dfa.alphabet:
            d = next(iter(dfa.transitions.get(s, {}).get(a, set())), None)
            if d is not None:
                new_trans[s2][a].add(block_names[d])

    minimized = Automaton(
        states=new_states,
        alphabet=set(dfa.alphabet),
        start_state=new_start,
        accept_states=new_accepts,
        transitions=new_trans,
        is_dfa=True,
        name=f"{dfa.name}{name_suffix}",
        state_composition=block_composition,
    )
    return minimized


# =====================
# Visualization
# =====================

class AutomatonVisualizer:
    def __init__(self, automaton: Automaton):
        self.automaton = automaton

    def plot(self, ax, title="Automaton", use_readable_names=True):
        """Dibuja el autómata usando matplotlib y networkx"""
        G = nx.DiGraph()
        
        # Agregar nodos
        for state in self.automaton.states:
            display_name = (self.automaton.get_readable_state_name(state) 
                          if use_readable_names else state)
            G.add_node(state, label=display_name)

        # Agregar aristas con mejor manejo de etiquetas múltiples
        edge_labels = {}
        for from_state, transitions in self.automaton.transitions.items():
            for symbol, to_states in transitions.items():
                for to_state in to_states:
                    edge_key = (from_state, to_state)
                    if edge_key in edge_labels:
                        # Combinar etiquetas de múltiples transiciones
                        existing_label = edge_labels[edge_key]
                        if symbol not in existing_label.split(','):
                            edge_labels[edge_key] = f"{existing_label},{symbol}"
                    else:
                        G.add_edge(from_state, to_state)
                        edge_labels[edge_key] = symbol

        # Layout del grafo
        if len(G.nodes) == 0:
            ax.text(0.5, 0.5, "Empty Automaton", ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title)
            return

        try:
            # Usar layout que distribuye mejor los nodos
            if len(G.nodes) <= 6:
                pos = nx.spring_layout(G, k=2.5, iterations=100, seed=42)
            else:
                pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)
        except:
            pos = nx.random_layout(G, seed=42)

        # Calcular colores de nodos
        node_colors = []
        node_labels = {}
        for node in G.nodes():
            if node == self.automaton.start_state:
                if node in self.automaton.accept_states:
                    node_colors.append('lightgreen')  # Start + Accept
                else:
                    node_colors.append('lightblue')   # Start
            elif node in self.automaton.accept_states:
                node_colors.append('lightcoral')     # Accept
            else:
                node_colors.append('lightgray')      # Normal
            
            display_name = (self.automaton.get_readable_state_name(node) 
                          if use_readable_names else node)
            node_labels[node] = display_name

        # Dibujar nodos (más grandes para mejor visibilidad)
        node_size = min(2000, max(800, 15000 // max(len(G.nodes), 1)))
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=node_size, ax=ax, alpha=0.9)
        
        # Dibujar etiquetas de nodos (con fondo blanco para mejor visibilidad)
        for node, (x, y) in pos.items():
            ax.text(x, y, node_labels[node], ha='center', va='center', 
                   fontsize=8, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", 
                           edgecolor="black", alpha=0.9))

        # Dibujar aristas
        nx.draw_networkx_edges(G, pos, edge_color='gray', 
                              arrows=True, arrowsize=15, 
                              arrowstyle='->', width=1.2, ax=ax, alpha=0.7)

        # Dibujar etiquetas de aristas de forma más inteligente
        self._draw_edge_labels_smart(ax, pos, edge_labels, G)

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.axis('off')

    def _draw_edge_labels_smart(self, ax, pos, edge_labels, G):
        """Dibuja etiquetas de aristas evitando superposición con nodos"""
        for (from_node, to_node), label in edge_labels.items():
            x1, y1 = pos[from_node]
            x2, y2 = pos[to_node]
            
            # Si es un self-loop
            if from_node == to_node:
                # Posicionar la etiqueta arriba del nodo
                label_x, label_y = x1, y1 + 0.15
                ax.text(label_x, label_y, label, ha='center', va='center', 
                       fontsize=7, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", 
                               alpha=0.8, edgecolor="orange"))
            else:
                # Para aristas normales, posicionar en el punto medio pero desplazado
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                
                # Calcular vector perpendicular para desplazar la etiqueta
                dx, dy = x2 - x1, y2 - y1
                length = (dx**2 + dy**2)**0.5
                if length > 0:
                    # Vector perpendicular normalizado
                    perp_x, perp_y = -dy / length, dx / length
                    # Desplazar la etiqueta
                    offset = 0.08
                    label_x = mid_x + perp_x * offset
                    label_y = mid_y + perp_y * offset
                else:
                    label_x, label_y = mid_x, mid_y
                
                # Verificar si hay múltiples símbolos y ajustar el estilo
                if ',' in label:
                    bbox_color = "lightcyan"
                    edge_color = "blue"
                else:
                    bbox_color = "lightyellow" 
                    edge_color = "orange"
                
                ax.text(label_x, label_y, label, ha='center', va='center', 
                       fontsize=7, fontweight='bold',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor=bbox_color, 
                               alpha=0.9, edgecolor=edge_color))


# =====================
# GUI Application
# =====================

class AutomatonGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NFA to DFA Converter")
        self.root.geometry("1200x800")
        
        # Configurar cierre correcto de la aplicación
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.nfa = None
        self.dfa = None
        self.minimized_dfa = None
        
        self.setup_ui()

    def on_closing(self):
        """Maneja el cierre correcto de la aplicación"""
        try:
            # Cerrar matplotlib figures para evitar warnings
            plt.close('all')
        except:
            pass
        
        # Destruir la ventana y salir del programa
        self.root.quit()
        self.root.destroy()

    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Frame de controles
        control_frame = ttk.LabelFrame(main_frame, text="Controls")
        control_frame.pack(fill='x', pady=(0, 10))

        # Botones de carga
        ttk.Button(control_frame, text="Load NFA (JSON)", 
                  command=lambda: self.load_file('json')).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Load NFA (XML)", 
                  command=lambda: self.load_file('xml')).pack(side='left', padx=5, pady=5)
        
        # Botones de conversión
        ttk.Button(control_frame, text="Convert to DFA", 
                  command=self.convert_to_dfa).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Minimize DFA", 
                  command=self.minimize_dfa).pack(side='left', padx=5, pady=5)
        
        # Botones de guardado
        ttk.Button(control_frame, text="Save Result (JSON)", 
                  command=lambda: self.save_file('json')).pack(side='left', padx=5, pady=5)
        ttk.Button(control_frame, text="Save Result (XML)", 
                  command=lambda: self.save_file('xml')).pack(side='left', padx=5, pady=5)

        # Checkbox para nombres legibles
        self.use_readable_names = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Show readable state names", 
                       variable=self.use_readable_names,
                       command=self.refresh_visualization).pack(side='right', padx=5, pady=5)

        # Notebook para pestañas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)

        # Pestaña de información
        self.setup_info_tab()
        
        # Pestaña de visualización
        self.setup_visualization_tab()

    def setup_info_tab(self):
        info_frame = ttk.Frame(self.notebook)
        self.notebook.add(info_frame, text="Information")

        # Text widget para mostrar información
        self.info_text = tk.Text(info_frame, wrap='word', font=('Courier', 10))
        info_scrollbar = ttk.Scrollbar(info_frame, orient='vertical', command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scrollbar.set)

        self.info_text.pack(side='left', fill='both', expand=True)
        info_scrollbar.pack(side='right', fill='y')

    def setup_visualization_tab(self):
        viz_frame = ttk.Frame(self.notebook)
        self.notebook.add(viz_frame, text="Visualization")

        # Matplotlib figure
        self.fig, self.axes = plt.subplots(1, 3, figsize=(15, 5))
        self.fig.tight_layout()
        
        self.canvas = FigureCanvasTkAgg(self.fig, viz_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    def load_file(self, file_format):
        file_types = [("JSON files", "*.json")] if file_format == 'json' else [("XML files", "*.xml")]
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
            messagebox.showinfo("Success", f"NFA loaded successfully from {file_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def convert_to_dfa(self):
        if not self.nfa:
            messagebox.showwarning("Warning", "Please load an NFA first")
            return

        try:
            self.dfa = nfa_to_dfa(self.nfa)
            self.minimized_dfa = None
            self.update_info()
            self.refresh_visualization()
            messagebox.showinfo("Success", "NFA converted to DFA successfully")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert: {str(e)}")

    def minimize_dfa(self):
        if not self.dfa:
            messagebox.showwarning("Warning", "Please convert to DFA first")
            return

        try:
            self.minimized_dfa = hopcroft_minimize(self.dfa)
            self.update_info()
            self.refresh_visualization()
            messagebox.showinfo("Success", "DFA minimized successfully")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to minimize: {str(e)}")

    def save_file(self, file_format):
        if not self.minimized_dfa and not self.dfa:
            messagebox.showwarning("Warning", "No automaton to save")
            return

        result_automaton = self.minimized_dfa if self.minimized_dfa else self.dfa
        
        file_types = [("JSON files", "*.json")] if file_format == 'json' else [("XML files", "*.xml")]
        file_path = filedialog.asksaveasfilename(
            filetypes=file_types,
            defaultextension=f".{file_format}"
        )
        
        if not file_path:
            return

        try:
            write_automaton(result_automaton, file_path, file_format)
            messagebox.showinfo("Success", f"Automaton saved to {file_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def update_info(self):
        self.info_text.delete(1.0, tk.END)
        
        info_lines = []
        
        if self.nfa:
            info_lines.append("=== ORIGINAL NFA ===")
            info_lines.append(f"Name: {self.nfa.name}")
            stats = self.nfa.get_stats()
            info_lines.append(f"States: {stats['states']}")
            info_lines.append(f"Alphabet: {sorted(self.nfa.alphabet)}")
            info_lines.append(f"Start state: {self.nfa.start_state}")
            info_lines.append(f"Accept states: {sorted(self.nfa.accept_states)}")
            info_lines.append(f"Total transitions: {stats['total_transitions']}")
            info_lines.append(f"Epsilon transitions: {stats['epsilon_transitions']}")
            info_lines.append(f"Is DFA: {stats['is_dfa']}")
            info_lines.append("")

            # Mostrar transiciones
            info_lines.append("Transitions:")
            for state in sorted(self.nfa.states):
                if state in self.nfa.transitions:
                    for symbol, destinations in sorted(self.nfa.transitions[state].items()):
                        dest_str = ", ".join(sorted(destinations))
                        symbol_display = symbol if symbol not in EPSILON_SYMBOLS else "ε"
                        info_lines.append(f"  {state} --{symbol_display}--> {dest_str}")
            info_lines.append("")

        if self.dfa:
            info_lines.append("=== CONVERTED DFA ===")
            info_lines.append(f"Name: {self.dfa.name}")
            stats = self.dfa.get_stats()
            info_lines.append(f"States: {stats['states']}")
            info_lines.append(f"Alphabet: {sorted(self.dfa.alphabet)}")
            info_lines.append(f"Start state: {self.dfa.start_state}")
            info_lines.append(f"Accept states: {sorted(self.dfa.accept_states)}")
            info_lines.append(f"Total transitions: {stats['total_transitions']}")
            info_lines.append("")

            # Mostrar composición de estados
            if self.dfa.state_composition:
                info_lines.append("State composition (DFA state -> Original NFA states):")
                for dfa_state in sorted(self.dfa.states):
                    if dfa_state in self.dfa.state_composition:
                        nfa_states = sorted(self.dfa.state_composition[dfa_state])
                        readable_name = self.dfa.get_readable_state_name(dfa_state)
                        info_lines.append(f"  {readable_name}: {{{', '.join(nfa_states)}}}")
                info_lines.append("")

            # Mostrar transiciones del DFA
            info_lines.append("DFA Transitions:")
            for state in sorted(self.dfa.states):
                if state in self.dfa.transitions:
                    for symbol, destinations in sorted(self.dfa.transitions[state].items()):
                        dest_str = ", ".join(sorted(destinations))
                        readable_from = self.dfa.get_readable_state_name(state)
                        readable_to = ", ".join([self.dfa.get_readable_state_name(d) for d in sorted(destinations)])
                        info_lines.append(f"  {readable_from} --{symbol}--> {readable_to}")
            info_lines.append("")

        if self.minimized_dfa:
            info_lines.append("=== MINIMIZED DFA ===")
            info_lines.append(f"Name: {self.minimized_dfa.name}")
            stats = self.minimized_dfa.get_stats()
            info_lines.append(f"States: {stats['states']}")
            info_lines.append(f"Alphabet: {sorted(self.minimized_dfa.alphabet)}")
            info_lines.append(f"Start state: {self.minimized_dfa.start_state}")
            info_lines.append(f"Accept states: {sorted(self.minimized_dfa.accept_states)}")
            info_lines.append(f"Total transitions: {stats['total_transitions']}")
            info_lines.append("")

            # Mostrar composición de estados minimizados
            if self.minimized_dfa.state_composition:
                info_lines.append("Minimized state composition (MIN state -> Original NFA states):")
                for min_state in sorted(self.minimized_dfa.states):
                    if min_state in self.minimized_dfa.state_composition:
                        nfa_states = sorted(self.minimized_dfa.state_composition[min_state])
                        readable_name = self.minimized_dfa.get_readable_state_name(min_state)
                        info_lines.append(f"  {readable_name}: {{{', '.join(nfa_states)}}}")
                info_lines.append("")

            # Mostrar transiciones del DFA minimizado
            info_lines.append("Minimized DFA Transitions:")
            for state in sorted(self.minimized_dfa.states):
                if state in self.minimized_dfa.transitions:
                    for symbol, destinations in sorted(self.minimized_dfa.transitions[state].items()):
                        readable_from = self.minimized_dfa.get_readable_state_name(state)
                        readable_to = ", ".join([self.minimized_dfa.get_readable_state_name(d) for d in sorted(destinations)])
                        info_lines.append(f"  {readable_from} --{symbol}--> {readable_to}")

        self.info_text.insert(tk.END, "\n".join(info_lines))

    def refresh_visualization(self):
        # Limpiar axes
        for ax in self.axes:
            ax.clear()

        use_readable = self.use_readable_names.get()

        # Visualizar NFA
        if self.nfa:
            visualizer = AutomatonVisualizer(self.nfa)
            visualizer.plot(self.axes[0], "Original NFA", use_readable)

        # Visualizar DFA
        if self.dfa:
            visualizer = AutomatonVisualizer(self.dfa)
            visualizer.plot(self.axes[1], "Converted DFA", use_readable)

        # Visualizar DFA minimizado
        if self.minimized_dfa:
            visualizer = AutomatonVisualizer(self.minimized_dfa)
            visualizer.plot(self.axes[2], "Minimized DFA", use_readable)

        # Si no hay DFA minimizado, limpiar el tercer eje
        if not self.minimized_dfa:
            self.axes[2].text(0.5, 0.5, "No minimized DFA yet", 
                            ha='center', va='center', transform=self.axes[2].transAxes)
            self.axes[2].set_title("Minimized DFA")

        self.fig.tight_layout()
        self.canvas.draw()


# =====================
# I/O Helpers & CLI
# =====================

def detect_format_from_ext(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".json", ".jsn"):
        return "json"
    if ext in (".xml",):
        return "xml"
    return "json"  # default


def read_automaton(path: str, fmt: str = None) -> Automaton:
    fmt = fmt or detect_format_from_ext(path)
    if fmt == "json":
        return parse_json_automaton(path)
    elif fmt == "xml":
        return parse_xml_automaton(path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def write_automaton(a: Automaton, path: str, fmt: str = None) -> None:
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


def build_arg_parser():
    p = argparse.ArgumentParser(
        description="Convierte un AFN (JSON/XML) a AFD y, opcionalmente, lo minimiza."
    )
    p.add_argument("input", nargs='?', help="Archivo de entrada (.json o .xml) con un AFN (ε permitido)")
    p.add_argument("-o", "--output", help="Archivo de salida (.json o .xml). Por defecto, junto a la entrada")
    p.add_argument("--in-format", choices=["json", "xml"], help="Forzar formato de entrada (auto por extensión)")
    p.add_argument("--out-format", choices=["json", "xml"], help="Forzar formato de salida (auto por extensión)")
    p.add_argument("--no-minimize", action="store_true", help="No minimizar (emitir AFD crudo)")
    p.add_argument("--name", help="Nombre del autómata de salida")
    p.add_argument("--gui", action="store_true", help="Abrir interfaz gráfica")
    return p


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = build_arg_parser().parse_args(argv)

    # Si se especifica --gui o no hay archivo de entrada, abrir GUI
    if args.gui or not args.input:
        try:
            import tkinter as tk
            import matplotlib.pyplot as plt
            import networkx as nx
            
            root = tk.Tk()
            app = AutomatonGUI(root)
            
            try:
                root.mainloop()
            except KeyboardInterrupt:
                print("\nProgram interrupted by user")
            finally:
                # Asegurar cierre limpio
                try:
                    plt.close('all')
                    root.quit()
                except:
                    pass
            
            return
        except ImportError as e:
            print(f"Error: Missing required GUI dependencies: {e}")
            print("Please install: pip install matplotlib networkx")
            if not args.input:
                return
            print("Falling back to command line mode...")

    if not args.input:
        print("Error: No input file specified and GUI not available")
        return

    # Modo línea de comandos
    in_fmt = args.in_format or detect_format_from_ext(args.input)
    a = read_automaton(args.input, in_fmt)

    print(f"Original NFA loaded: {a.name}")
    print(f"States: {len(a.states)}, Alphabet: {sorted(a.alphabet)}")
    
    # Mostrar composición si la tiene
    if a.state_composition:
        print("State composition:")
        for state in sorted(a.states):
            if state in a.state_composition:
                readable_name = a.get_readable_state_name(state)
                print(f"  {readable_name}")

    dfa = nfa_to_dfa(a)
    print(f"\nDFA conversion complete: {dfa.name}")
    print(f"States: {len(dfa.states)}, Alphabet: {sorted(dfa.alphabet)}")
    
    # Mostrar estados DFA con su composición
    if dfa.state_composition:
        print("DFA state composition:")
        for state in sorted(dfa.states):
            readable_name = dfa.get_readable_state_name(state)
            print(f"  {readable_name}")

    out_auto = dfa if args.no_minimize else hopcroft_minimize(dfa)

    if not args.no_minimize:
        print(f"\nMinimization complete: {out_auto.name}")
        print(f"States: {len(out_auto.states)}, Alphabet: {sorted(out_auto.alphabet)}")
        
        # Mostrar estados minimizados con su composición
        if out_auto.state_composition:
            print("Minimized DFA state composition:")
            for state in sorted(out_auto.states):
                readable_name = out_auto.get_readable_state_name(state)
                print(f"  {readable_name}")

    if args.name:
        out_auto.name = args.name

    out_path = args.output
    if not out_path:
        base, ext = os.path.splitext(args.input)
        suffix = "_dfa" if args.no_minimize else "_dfa_min"
        # Si no hay extensión, usar formato de salida o el de entrada
        chosen_ext = (args.out_format or (ext.lstrip(".") if ext else in_fmt) or "json")
        out_path = f"{base}{suffix}.{chosen_ext}"

    out_fmt = args.out_format or detect_format_from_ext(out_path)
    write_automaton(out_auto, out_path, out_fmt)

    # Resumen por stdout
    print(f"\nInput: {args.input} ({in_fmt})  ->  Output: {out_path} ({out_fmt})")
    print(f"Final States: {len(out_auto.states)} | Start: {out_auto.start_state}")
    print(f"Accepting: {sorted(out_auto.accept_states)}")
    cnt = sum(len(v) for v in out_auto.transitions.values())
    print(f"Transitions (state->symbol edges): {cnt}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        # argparse puede llamar a sys.exit()
        pass
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        sys.exit(0)