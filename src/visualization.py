import matplotlib.pyplot as plt
import networkx as nx
import math
from automaton import Automaton
from matplotlib.patches import FancyArrowPatch


class AutomatonVisualizer:
    def __init__(self, automaton: Automaton):
        self.automaton = automaton

    def plot(self, ax, title="Automaton", use_readable_names=True):
        G = nx.DiGraph()

        # Agregar nodos
        for state in self.automaton.states:
            display_name = (
                self.automaton.get_readable_state_name(state)
                if use_readable_names else state
            )
            G.add_node(state, label=display_name)

        # Agregar transiciones
        edge_labels = {}
        for from_state, transitions in self.automaton.transitions.items():
            for symbol, to_states in transitions.items():
                for to_state in to_states:
                    edge_key = (from_state, to_state)
                    if edge_key in edge_labels:
                        # Combinar etiquetas si hay varias transiciones
                        if symbol not in edge_labels[edge_key].split(','):
                            edge_labels[edge_key] += f",{symbol}"
                    else:
                        G.add_edge(from_state, to_state)
                        edge_labels[edge_key] = symbol

        if len(G.nodes) == 0:
            ax.text(0.5, 0.5, "Empty Automaton", ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title)
            return

        # Layout con más separación
        pos = nx.spring_layout(G, k=2.5, iterations=100, seed=42)

        # Determinar colores
        node_colors = []
        node_labels = {}
        for node in G.nodes():
            if node == self.automaton.start_state:
                if node in self.automaton.accept_states:
                    node_colors.append('#A8E6A1')  # Verde claro (inicio + aceptación)
                else:
                    node_colors.append('#ADD8E6')  # Azul claro (inicio)
            elif node in self.automaton.accept_states:
                node_colors.append('#FFB6B6')  # Rojo claro (aceptación)
            else:
                node_colors.append('#D3D3D3')  # Gris claro
            node_labels[node] = (
                self.automaton.get_readable_state_name(node)
                if use_readable_names else node
            )

        node_size = min(2200, max(1000, 16000 // max(len(G.nodes), 1)))

        # --- DIBUJAR ---
        ax.clear()

        # Dibujar aristas primero
        self._draw_adjusted_edges(ax, pos, G, node_size)

        # Luego dibujar nodos por encima
        nx.draw_networkx_nodes(
            G, pos,
            node_color=node_colors,
            node_size=node_size,
            edgecolors='black',
            linewidths=1.5,
            ax=ax,
            alpha=0.95
        )

        # Etiquetas de nodos
        nx.draw_networkx_labels(
            G, pos, labels=node_labels,
            font_size=9, font_weight='bold', ax=ax
        )

        # Etiquetas de aristas
        self._draw_edge_labels_smart(ax, pos, edge_labels)

        # Ajustes visuales
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.axis('off')
        ax.margins(0.2)  # Margen extra para evitar cortes
        ax.set_xlim(min(x for x, y in pos.values()) - 0.3, max(x for x, y in pos.values()) + 0.3)
        ax.set_ylim(min(y for x, y in pos.values()) - 0.3, max(y for x, y in pos.values()) + 0.3)

    def _draw_adjusted_edges(self, ax, pos, G, node_size):
     """Dibuja flechas ajustadas para terminar en el borde del nodo y dibuja self-loops visibles."""
     radius = math.sqrt(node_size) / 355.0  # Radio aproximado del nodo

     for u, v in G.edges():
        x1, y1 = pos[u]
        x2, y2 = pos[v]

        if u == v:
            # ===== SELF-LOOP =====
            loop_radius = 0.15  # controla qué tan grande es el bucle
            loop = FancyArrowPatch(
                (x1, y1), (x1 + 0.001, y1 + 0.001),
                connectionstyle=f"arc3,rad={loop_radius}",
                arrowstyle='-|>',
                mutation_scale=15,    # Tamaño de la cabeza
                lw=1.8,
                color='black',
                shrinkA=radius * 40,  # Despegar desde el nodo
                shrinkB=radius * 40,
                zorder=4
            )
            ax.add_patch(loop)
            continue

        # ===== TRANSICIONES NORMALES =====
        dx, dy = x2 - x1, y2 - y1
        dist = math.sqrt(dx ** 2 + dy ** 2)
        if dist == 0:
            continue

        # Ajustar final para que no entre en el centro del nodo
        adj_x2 = x1 + (dx * (dist - radius)) / dist
        adj_y2 = y1 + (dy * (dist - radius)) / dist

        ax.annotate(
            "",
            xy=(adj_x2, adj_y2), xycoords='data',
            xytext=(x1 + dx * radius / dist, y1 + dy * radius / dist),
            textcoords='data',
            arrowprops=dict(
                arrowstyle='-|>',
                color='black',
                lw=1.5,
                shrinkA=0,
                shrinkB=0,
                connectionstyle="arc3,rad=0.1"
            )
        )

    def _draw_edge_labels_smart(self, ax, pos, edge_labels):
        """Dibuja etiquetas para las aristas, evitando superposición."""
        for (from_node, to_node), label in edge_labels.items():
            x1, y1 = pos[from_node]
            x2, y2 = pos[to_node]

            if from_node == to_node:
                # Bucle sobre el mismo estado
                ax.text(
                    x1, y1 + 0.25, label,
                    ha='center', va='center',
                    fontsize=8, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow",
                              edgecolor="orange", alpha=0.8)
                )
            else:
                # Punto medio entre origen y destino
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x2 - x1, y2 - y1
                length = math.sqrt(dx**2 + dy**2)

                if length > 0:
                    perp_x, perp_y = -dy / length, dx / length
                    offset = 0.1
                    label_x = mid_x + perp_x * offset
                    label_y = mid_y + perp_y * offset
                else:
                    label_x, label_y = mid_x, mid_y

                ax.text(
                    label_x, label_y, label,
                    ha='center', va='center',
                    fontsize=8, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                              edgecolor="black", alpha=0.9)
                )
