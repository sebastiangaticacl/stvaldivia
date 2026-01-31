insumos = {
    "ron": 3000,
    "vodka": 2500,
    "limon": 1500,
    "jarabe": 1800
}

recetas = {
    "mojito": {"ron":60,"limon":30,"jarabe":20},
    "pisco sour": {"vodka":60,"limon":30,"jarabe":25}
}

def descontar(producto, cantidad=1):
    if producto not in recetas:
        return False

    for insumo, ml in recetas[producto].items():
        insumos[insumo] -= ml*cantidad
        
    return True
