import sys
import argparse
from automaton import Automaton
from parsing import parse_json_automaton, automaton_to_json_dict
from conversion import nfa_to_dfa, hopcroft_minimize
from gui import AutomatonGUI, write_automaton


def read_automaton(path: str) -> Automaton:
    return parse_json_automaton(path)


def build_arg_parser():
    p = argparse.ArgumentParser(description="Convierte un AFN (JSON) a AFD y lo minimiza.")
    p.add_argument("input", nargs='?', help="Archivo de entrada (.json) con un AFN (ε permitido)")
    p.add_argument("-o", "--output", help="Archivo de salida (.json).")
    p.add_argument("--no-minimize", action="store_true", help="No minimizar (emitir AFD crudo)")
    p.add_argument("--name", help="Nombre del autómata de salida")
    p.add_argument("--gui", action="store_true", help="Abrir interfaz gráfica")
    return p


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = build_arg_parser().parse_args(argv)

    if args.gui or not args.input:
        try:
            import tkinter as tk
            import matplotlib.pyplot as plt
            root = tk.Tk()
            app = AutomatonGUI(root)
            root.mainloop()
            return
        except ImportError as e:
            print(f"Error: Dependencias gráficas faltantes: {e}")
            if not args.input:
                return
            print("Falling back to command line mode...")

    if not args.input:
        print("Error: No se especificó archivo de entrada")
        return

    a = read_automaton(args.input)
    print(f"AFN original cargado: {a.name}")

    dfa = nfa_to_dfa(a)
    out_auto = dfa if args.no_minimize else hopcroft_minimize(dfa)

    if args.name:
        out_auto.name = args.name

    out_path = args.output if args.output else args.input.replace(".json", "_dfa_min.json")
    write_automaton(out_auto, out_path)
    print(f"Archivo generado: {out_path}")


if __name__ == "__main__":
    main()
