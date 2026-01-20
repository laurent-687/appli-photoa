# -*- coding: utf-8 -*-
import os
import io
import zipfile
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APERÇUS_DIR = os.path.join(BASE_DIR, 'Apercus')
CGU_DIR = os.path.join(BASE_DIR, 'CGU')

# Initialisation de l'application Flask
app = Flask(__name__)
# Activation de CORS pour autoriser les requêtes depuis le fichier HTML local
CORS(app)

@app.route('/')
def serve_index():
    """Sert la page principale de l'application."""
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/download-zip', methods=['POST'])
def download_zip():
    """
    Crée une archive ZIP à la volée contenant les images sélectionnées et les CGU.
    """
    try:
        data = request.get_json()
        if not data or 'matricules' not in data:
            return jsonify({"error": "Aucun matricule fourni"}), 400

        matricules = data['matricules']
        
        # Crée un fichier ZIP en mémoire
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Ajoute les images correspondantes aux matricules
            print("\n--- Début du traitement de la sélection ---")
            for matricule in matricules:
                # Assainir le nom du fichier pour la sécurité
                if not matricule or '..' in matricule or '/' in matricule or '\\' in matricule:
                    print(f"-> Matricule '{matricule}' ignoré (invalide ou potentiellement dangereux).")
                    continue

                image_filename = f"{matricule}.jpg"
                image_path = os.path.join(APERÇUS_DIR, image_filename)
                
                print(f"-> Recherche de l'image : '{image_path}'")
                
                if os.path.exists(image_path):
                    zf.write(image_path, arcname=image_filename)
                    print(f"   [✓] Trouvé et ajouté au ZIP.")
                else:
                    print(f"   [✗] NON TROUVÉ. Fichier ignoré.")
            
            print("--- Fin du traitement de la sélection ---\n")

            # 2. Ajoute tous les fichiers du dossier CGU
            print("--- Traitement des fichiers CGU ---")
            if os.path.exists(CGU_DIR):
                for cgu_filename in os.listdir(CGU_DIR):
                    cgu_path = os.path.join(CGU_DIR, cgu_filename)
                    if os.path.isfile(cgu_path):
                         # Ajoute le fichier à l'archive dans un sous-dossier "CGU"
                        zf.write(cgu_path, arcname=os.path.join('CGU', cgu_filename))

        # Se positionner au début du fichier en mémoire avant de l'envoyer
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            download_name='selection.zip',
            as_attachment=True,
            mimetype='application/zip'
        )

    except Exception as e:
        # Log l'erreur côté serveur pour le débogage
        print(f"Une erreur est survenue: {e}")
        return jsonify({"error": "Une erreur interne est survenue sur le serveur."}), 500

if __name__ == '__main__':
    # Lance le serveur sur le port 5000, accessible depuis n'importe quelle IP de la machine
    # L'URL du service sera http://127.0.0.1:5000
    app.run(host='0.0.0.0', port=5000, debug=True)
