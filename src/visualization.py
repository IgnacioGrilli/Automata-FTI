import matplotlib.pyplot as plt
import networkx as nx
from automaton import Automaton


class AutomatonVisualizer:
    def __init__(self, automaton: Automaton):
        self.automaton = automaton

    def plot(self, ax, title="Automaton", use_readable_names=True):
        G = nx.DiGraph()
        for state in self.automaton.states:
            display_name = (
                self.automaton.get_readable_state_name(state)
                if use_readable_names
                else state
            )
            G.add_node(state, label=display_name)

        edge_labels = {}

        for from_state, transitions in self.automaton.transitions.items():
            for symbol, to_states in transitions.items():
                for to_state in to_states:
                    edge_key = (from_state, to_state)
                    if edge_key in edge_labels:
                        existing_label = edge_labels[edge_key]
                        if symbol not in existing_label.split(","):
                            edge_labels[edge_key] = f"{existing_label},{symbol}"
                    else:
                        G.add_edge(from_state, to_state)
                        edge_labels[edge_key] = symbol

        if len(G.nodes) == 0:
            ax.text(
                0.5,
                0.5,
                "Empty Automaton",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_title(title)
            return

        try:
            if len(G.nodes) <= 6:
                pos = nx.spring_layout(G, k=2.5, iterations=100, seed=42)
            else:
                pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)
        except:
            pos = nx.random_layout(G, seed=42)

        node_colors = []
        node_labels = {}

        for node in G.nodes():
            if node == self.automaton.start_state:
                if node in self.automaton.accept_states:
                    node_colors.append("lightgreen")
                else:
                    node_colors.append("lightblue")
            elif node in self.automaton.accept_states:
                node_colors.append("lightcoral")
            else:
                node_colors.append("lightgray")

            display_name = (
                self.automaton.get_readable_state_name(node)
                if use_readable_names
                else node
            )
            node_labels[node] = display_name

        node_size = min(2000, max(800, 15000 // max(len(G.nodes), 1)))
        nx.draw_networkx_nodes(
            G, pos, node_color=node_colors, node_size=node_size, ax=ax, alpha=0.9
        )

        for node, (x, y) in pos.items():
            ax.text(
                x,
                y,
                node_labels[node],
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="black",
                    alpha=0.9,
                ),
            )

        nx.draw_networkx_edges(
            G,
            pos,
            edge_color="gray",
            arrows=True,
            arrowsize=15,
            arrowstyle="->",
            width=1.2,
            ax=ax,
            alpha=0.7,
        )

        self._draw_edge_labels_smart(ax, pos, edge_labels, G)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.axis("off")

    def _draw_edge_labels_smart(self, ax, pos, edge_labels, G):
        for (from_node, to_node), label in edge_labels.items():
            x1, y1 = pos[from_node]
            x2, y2 = pos[to_node]

            if from_node == to_node:
                label_x, label_y = x1, y1 + 0.15
                ax.text(
                    label_x,
                    label_y,
                    label,
                    ha="center",
                    va="center",
                    fontsize=7,
                    fontweight="bold",
                    bbox=dict(
                        boxstyle="round,pad=0.2",
                        facecolor="yellow",
                        alpha=0.8,
                        edgecolor="orange",
                    ),
                )
            else:
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x2 - x1, y2 - y1
                length = (dx**2 + dy**2) ** 0.5

                if length > 0:
                    perp_x, perp_y = -dy / length, dx / length
                    offset = 0.08
                    label_x = mid_x + perp_x * offset
                    label_y = mid_y + perp_y * offset
                else:
                    label_x, label_y = mid_x, mid_y
                if "," in label:
                    bbox_color = "lightcyan"
                    edge_color = "blue"
                else:
                    bbox_color = "lightyellow"
                    edge_color = "orange"
                ax.text(
                    label_x,
                    label_y,
                    label,
                    ha="center",
                    va="center",
                    fontsize=7,
                    fontweight="bold",
                    bbox=dict(
                        boxstyle="round,pad=0.2",
                        facecolor=bbox_color,
                        alpha=0.9,
                        edgecolor=edge_color,
                    ),
                )
