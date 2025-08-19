# Automata-FTI

https://github.com/IgnacioGrilli/Automata-FTI.git


Lee un AFN (con o sin ε‑transiciones) en JSON o XML.

Lo convierte a AFD (construcción por subconjuntos + clausura‑ε).

Opcionalmente minimiza el AFD con Hopcroft.

Escribe el resultado en JSON o XML (mismo formato que entrada por defecto).


==============================================
nfa_dfa.py — NFA a DFA + minimización (Python)
==============================================

Uso básico (desde terminal):

  python nfa_dfa.py samples/sample_nfa.json
  # Genera: samples/sample_nfa_dfa_min.json

Opciones útiles:
  --no-minimize            # Sólo determiniza, sin minimizar
  --in-format json|xml     # Forzar formato de entrada
  --out-format json|xml    # Forzar formato de salida
  -o salida.json           # Elegir archivo de salida
  --name NOMBRE            # Renombrar el autómata de salida

Formato JSON esperado:
{
  "name": "mi_nfa",
  "states": ["q0","q1"],
  "alphabet": ["a","b"],               # opcional: se infiere de transiciones
  "start_state": "q0",
  "accept_states": ["q1"],
  "transitions": {
    "q0": {"a": ["q0","q1"], "epsilon": ["q0"]},
    "q1": {"b": ["q1"]}
  }
}

Notas sobre epsilon: se aceptan claves "", "ε", "eps", o "epsilon".

Formato XML esperado (flexible):
<automaton name="mi_nfa">
  <states><state>q0</state>...</states>
  <alphabet><symbol>a</symbol>...</alphabet>  <!-- opcional -->
  <start>q0</start>
  <accept><state>q1</state></accept>
  <transitions>
    <t from="q0" symbol="a" to="q1"/>
    <!-- o bien con subetiquetas <from>, <symbol>, <to> -->
  </transitions>
</automaton>

Algoritmos:
- Construcción por subconjuntos + clausura-ε para NFA→DFA.
- Minimización de DFA con Hopcroft.
- Se eliminan estados inalcanzables antes de minimizar.

Salida:
- Por defecto conserva el formato de entrada, pero se puede forzar con --out-format.
- En JSON, las transiciones deterministas se serializan como string (un único destino),
  y como lista cuando hay varias (no debería ocurrir en DFA, pero el parser soporta ambos).

