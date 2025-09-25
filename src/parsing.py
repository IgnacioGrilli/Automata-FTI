import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, Set
from automaton import Automaton, EPSILON_SYMBOLS

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
