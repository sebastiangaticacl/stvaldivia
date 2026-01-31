import json, os

CONFIG_FILE = "config_prompts.json"

default_config = {
    "rrss": None,
    "optimizacion": None,
    "mixologia": None,
    "cerebro": None
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
    with open(CONFIG_FILE,"r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE,"w") as f:
        json.dump(cfg,f,indent=2)

def set_prompt_agente(agente, prompt_id):
    cfg = load_config()
    cfg[agente] = prompt_id
    save_config(cfg)
    return cfg

def get_prompt_activo(agente=None):
    cfg = load_config()
    if agente:
        return cfg.get(agente)
    return cfg
