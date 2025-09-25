import sys
import argparse
from automaton import Automaton
from parsing import parse_json_automaton, parse_xml_automaton, automaton_to_json_dict, automaton_to_xml_element
from conversion import nfa_to_dfa, hopcroft_minimize
from gui import AutomatonGUI, write_automaton

def detect_format_from_ext(path: str) -> str:
    import os
    ext = os.path.splitext(path)[1].lower()
    if ext in (".json", ".jsn"):
        return "json"
    if ext in (".xml",):
        return "xml"
    return "json"

def read_automaton(path: str, fmt: str = None) -> Automaton:
    fmt = fmt or detect_format_from_ext(path)
    if fmt == "json":
        return parse_json_automaton(path)
    elif fmt == "xml":
        return parse_xml_automaton(path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

def build_arg_parser():
    p = argparse.ArgumentParser(description="Convierte un AFN (JSON/XML) a AFD y, opcionalmente, lo minimiza.")
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
    if args.gui or not args.input:
        try:
            import tkinter as tk
            import matplotlib.pyplot as plt
            root = tk.Tk()
            app = AutomatonGUI(root)
            try:
                root.mainloop()
            except KeyboardInterrupt:
                print("\nProgram interrupted by user")
            finally:
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
    in_fmt = args.in_format or detect_format_from_ext(args.input)
    a = read_automaton(args.input, in_fmt)
    print(f"Original NFA loaded: {a.name}")
    print(f"States: {len(a.states)}, Alphabet: {sorted(a.alphabet)}")
    if a.state_composition:
        print("State composition:")
        for state in sorted(a.states):
            if state in a.state_composition:
                readable_name = a.get_readable_state_name(state)
                print(f"  {readable_name}")
    dfa = nfa_to_dfa(a)
    print(f"\nDFA conversion complete: {dfa.name}")
    print(f"States: {len(dfa.states)}, Alphabet: {sorted(dfa.alphabet)}")
    if dfa.state_composition:
        print("DFA state composition:")
        for state in sorted(dfa.states):
            readable_name = dfa.get_readable_state_name(state)
            print(f"  {readable_name}")
    out_auto = dfa if args.no_minimize else hopcroft_minimize(dfa)
    if not args.no_minimize:
        print(f"\nMinimization complete: {out_auto.name}")
        print(f"States: {len(out_auto.states)}, Alphabet: {sorted(out_auto.alphabet)}")
        if out_auto.state_composition:
            print("Minimized DFA state composition:")
            for state in sorted(out_auto.states):
                readable_name = out_auto.get_readable_state_name(state)
                print(f"  {readable_name}")
    if args.name:
        out_auto.name = args.name
    out_path = args.output
    if not out_path:
        import os
        base, ext = os.path.splitext(args.input)
        suffix = "_dfa" if args.no_minimize else "_dfa_min"
        chosen_ext = (args.out_format or (ext.lstrip(".") if ext else in_fmt) or "json")
        out_path = f"{base}{suffix}.{chosen_ext}"
    out_fmt = args.out_format or detect_format_from_ext(out_path)
    write_automaton(out_auto, out_path, out_fmt)
    print(f"\nInput: {args.input} ({in_fmt})  ->  Output: {out_path} ({out_fmt})")
    print(f"Final States: {len(out_auto.states)} | Start: {out_auto.start_state}")
    print(f"Accepting: {sorted(out_auto.accept_states)}")
    cnt = sum(len(v) for v in out_auto.transitions.values())
    print(f"Transitions (state->symbol edges): {cnt}")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        sys.exit(0)
