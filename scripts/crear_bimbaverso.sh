#!/bin/bash

# Crear carpetas principales
mkdir -p bimbaverso
cd bimbaverso

mkdir -p backend
mkdir -p backend/app
mkdir -p backend/app/routes
mkdir -p backend/app/services
mkdir -p backend/app/models

mkdir -p frontend
mkdir -p frontend/static
mkdir -p frontend/static/css
mkdir -p frontend/static/js

mkdir -p data
mkdir -p logs

# Crear entorno virtual
cd backend
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias backend
pip install flask flask-cors python-dotenv

# Crear archivo backend principal
cat << 'EOF' > app/__init__.py
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)

    from app.routes.chat import chat_bp
    from app.routes.programacion import programacion_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(programacion_bp)

    return app
EOF

# Crear rutas API básicas
cat << 'EOF' > app/routes/chat.py
from flask import Blueprint, request, jsonify

chat_bp = Blueprint("chat", __name__)

@chat_bp.post("/api/chat")
def chat():
    data = request.json
    mensaje = data.get("mensaje","")
    # Aquí llamarías al agente RRSS
    respuesta = f"Bimba responde a: {mensaje}"
    return jsonify({"respuesta": respuesta})
EOF

cat << 'EOF' > app/routes/programacion.py
from flask import Blueprint, jsonify

programacion_bp = Blueprint("programacion", __name__)

@programacion_bp.get("/api/programacion")
def programacion():
    # mock inicial
    return jsonify({
        "programacion": [
            {
                "evento": "Perreo en la Neblina",
                "fecha": "2025-12-23",
                "hora": "23:00",
                "djs": ["Krys", "Nachito Leal"],
                "cover_desde": 5000
            }
        ]
    })
EOF

# Crear servidor run
cat << 'EOF' > run.py
from app import create_app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
EOF

# Crear frontend básico
cd ../frontend
cat << 'EOF' > index.html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>Bimba 💜</title>
  <link rel="stylesheet" href="static/css/style.css" />
</head>
<body>

<h1>Hola, soy BIMBA 💜</h1>

<div id="chat-box"></div>

<input id="msg" placeholder="pregúntame algo..." />

<script src="static/js/app.js"></script>
</body>
</html>
EOF

# JS del chat
cat << 'EOF' > static/js/app.js
document.getElementById("msg").addEventListener("keyup", async (e)=>{
  if(e.key === "Enter"){
    const mensaje = e.target.value;
    const res = await fetch("http://localhost:5001/api/chat",{
      method:"POST",
      headers:{ "Content-Type":"application/json"},
      body:JSON.stringify({mensaje})
    });
    const data = await res.json();
    document.getElementById("chat-box").innerHTML += "<p>"+data.respuesta+"</p>";
  }
});
EOF

# CSS mínimo
cat << 'EOF' > static/css/style.css
body {
  background: black;
  color: white;
  font-family: sans-serif;
}
EOF

echo "✔ BIMBAVERSO base creada"









