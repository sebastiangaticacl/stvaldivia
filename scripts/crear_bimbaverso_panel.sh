#!/bin/bash

mkdir -p bimbaverso_panel
cd bimbaverso_panel

# BACKEND
mkdir -p backend/app/routes backend/app/services backend/app/models

cd backend
python3 -m venv venv
source venv/bin/activate
pip install flask flask-cors python-dotenv

# app factory
cat << 'EOF' > app/__init__.py
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)

    from app.routes.panel import panel_bp
    app.register_blueprint(panel_bp)

    return app
EOF

# PANEL ROUTES
cat << 'EOF' > app/routes/panel.py
from flask import Blueprint, jsonify

panel_bp = Blueprint("panel_bp", __name__)

@panel_bp.get("/api/panel/status")
def status():
    # mock para demo inicial del panel
    return jsonify({
        "bimbaverso": "OK",
        "agentes": {
            "rrss": "activo",
            "optimizacion": "activo",
            "mixologia": "activo"
        }
    })
EOF

cat << 'EOF' > run.py
from app import create_app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
EOF

cd ..

# FRONTEND PANEL
mkdir -p frontend static/js static/css

cat << 'EOF' > frontend/index.html
<!DOCTYPE html>
<html>
<head>
<title>PANEL BIMBAVERSO</title>
<link rel="stylesheet" href="../static/css/style.css" />
</head>
<body>

<h1>PANEL DE CONTROL - BIMBA 💜</h1>

<button onclick="loadStatus()">Ver estado</button>

<div id="status"></div>

<script src="../static/js/panel.js"></script>
</body>
</html>
EOF

cat << 'EOF' > static/js/panel.js
async function loadStatus(){
  const res = await fetch("http://localhost:5002/api/panel/status");
  const data = await res.json();
  document.getElementById("status").innerHTML =
    "<pre>"+JSON.stringify(data,null,2)+"</pre>";
}
EOF

cat << 'EOF' > static/css/style.css
body{
  background:#111;
  color:white;
  font-family: Arial, sans-serif;
  padding:20px;
}
button{
  background:#a74cf2;
  color:white;
  padding:10px;
  border:none;
  border-radius:8px;
}
EOF

echo "✔ PANEL BIMBAVERSO creado con éxito"









