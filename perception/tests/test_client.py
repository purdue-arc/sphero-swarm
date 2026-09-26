from flask import Flask, render_template_string, jsonify
import zmq
import pickle
import json

app = Flask(__name__)
print("Starting connection attempts")

# --- Setup ZeroMQ connection ---
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")
socket.send_string("init")
msg = socket.recv_string()
if msg.split(" - ")[0] != "connected":
    raise Exception("Failed to connect to sphero_spotter")

print("Connected!")

# --- Simple HTML page ---
HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Sphero Spotter Client</title>
    <script>
      async function getCoords() {
        const res = await fetch('/coords');
        const data = await res.json();
        
        if (data.error) {
          document.getElementById('output').innerHTML =
            '<div style="color:red;">Error: ' + data.error + '</div>';
          return;
        }

        // Build table dynamically
        const container = document.getElementById('output');
        if (!data.spheros || data.spheros.length === 0) {
          container.innerHTML = "<p>No spheros found.</p>";
          return;
        }

        const keys = Object.keys(data.spheros[0]);
        let html = '<table><thead><tr>';
        for (const key of keys) {
          html += `<th>${key}</th>`;
        }
        html += '</tr></thead><tbody>';

        for (const sphero of data.spheros) {
          html += '<tr>';
          for (const key of keys) {
            html += `<td>${sphero[key]}</td>`;
          }
          html += '</tr>';
        }

        html += '</tbody></table>';
        container.innerHTML = html;
      }
    </script>
    <style>
      body { font-family: sans-serif; margin: 2em; }
      button { padding: 10px 20px; font-size: 16px; cursor: pointer; margin-bottom: 1em; }
      table { border-collapse: collapse; width: 100%; max-width: 800px; }
      th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
      th { background: #0078D7; color: white; }
      tr:nth-child(even) { background: #f9f9f9; }
      pre { background: #f4f4f4; padding: 1em; border-radius: 8px; }
    </style>
  </head>
  <body>
    <h1>Sphero Spotter Interface</h1>
    <button onclick="getCoords()">Get Coords</button>
    <div id="output">Click the button to request coordinates...</div>
  </body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/coords")
def coords():
    try:
        socket.send_string("coords")
        raw = socket.recv_json() 
        return jsonify(raw)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("Flask app running at http://127.0.0.1:5000")
    app.run(debug=True)
