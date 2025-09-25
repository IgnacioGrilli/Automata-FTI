# Automata-FTI

Conversor y minimizador de autómatas finitos (NFA → DFA → DFA mínimo) con interfaz gráfica y línea de comandos.

## Estructura del proyecto

- `automaton.py`: Clase principal `Automaton` y constantes.
- `parsing.py`: Funciones para leer y escribir autómatas en JSON/XML.
- `conversion.py`: Algoritmos de conversión NFA→DFA y minimización.
- `visualization.py`: Visualización de autómatas con `matplotlib` y `networkx`.
- `gui.py`: Interfaz gráfica (Tkinter).
- `main.py`: Punto de entrada CLI y GUI.
- `samples/`: Ejemplos de autómatas en JSON/XML.

## Instalación de dependencias

Requiere Python 3.8+

Instala las dependencias:

```sh
pip install -r requirements.txt
```

## Uso por línea de comandos

```sh
python src/main.py <archivo_entrada> [opciones]
```

Opciones principales:
- `-o`, `--output`: Archivo de salida (JSON/XML)
- `--in-format`: Forzar formato de entrada (`json`/`xml`)
- `--out-format`: Forzar formato de salida (`json`/`xml`)
- `--no-minimize`: Solo convierte a DFA, no minimiza
- `--name`: Nombre del autómata de salida
- `--gui`: Abre la interfaz gráfica

Ejemplo:
```sh
python src/main.py samples/sample_nfa.json --out-format xml
```

## Uso de la interfaz gráfica

```sh
python src/main.py
```

Permite cargar archivos JSON/XML, visualizar el NFA, convertir a DFA, minimizar y guardar el resultado.

## Formatos soportados

- **JSON**: Estructura con campos `states`, `alphabet`, `start_state`, `accept_states`, `transitions`.
- **XML**: Estructura con nodos `<states>`, `<alphabet>`, `<start>`, `<accept>`, `<transitions>`.

Ejemplo de transición en JSON:
```json
"transitions": {
  "q0": {"a": "q1", "ε": ["q2", "q3"]},
  "q1": {"b": "q2"}
}
```

## Ejemplos

Archivos de ejemplo en la carpeta `samples/`.

## Requisitos
- Python 3.8+
- Paquetes: `matplotlib`, `networkx`, `numpy`

## Créditos
Desarrollado por Ignacio Grilli y Matias Casteglione.

