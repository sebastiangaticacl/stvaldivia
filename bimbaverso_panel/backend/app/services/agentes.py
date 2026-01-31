import json
import os

STATE_FILE = "agentes_state.json"

# estado inicial si no existe
default_state = {
    "rrss": True,
    "optimizacion": True,
    "mixologia": True
}

def load_state():
    if not os.path.exists(STATE_FILE):
        save_state(default_state)
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def set_estado(agente, estado):
    state = load_state()
    state[agente] = estado
    save_state(state)

def get_estado():
    return load_state()
