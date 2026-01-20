# -*- coding: utf-8 -*-
import os
import io
import zipfile
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS

# --- Configuration du logging ---

# 1. Logger technique (pour le débogage et le suivi du flux de l'application)
tech_logger = logging.getLogger('tech')
tech_logger.setLevel(logging.INFO)
tech_handler = logging.StreamHandler()
tech_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
tech_handler.setFormatter(tech_formatter)
tech_logger.addHandler(tech_handler)

# 2. Logger applicatif (pour le suivi des téléchargements)
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.INFO)
# Créer le fichier de log s'il n'existe pas
if not os.path.exists('download.log'):
    open('download.log', 'a').close()
# Handler pour écrire dans un fichier avec rotation (max 10MB, 5 fichiers backup)
app_handler = RotatingFileHandler('download.log', maxBytes=10*1024*1024, backupCount=5)
app_formatter = logging.Formatter('%(asctime)s - %(message)s')
app_handler.setFormatter(app_formatter)
app_logger.addHandler(app_handler)

# --- Fin de la configuration du logging ---

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
    tech_logger.info(f"Service de la page d'accueil (index.html) à {request.remote_addr}")
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/download-zip', methods=['POST'])
def download_zip():
    """
    Crée une archive ZIP à la volée contenant les images sélectionnées et les CGU.
    """
    tech_logger.info(f"Requête de téléchargement reçue de {request.remote_addr}")
    try:
        data = request.get_json()
        if not data or 'matricules' not in data:
            tech_logger.warning(f"Requête invalide de {request.remote_addr}: aucun matricule fourni.")
            return jsonify({"error": "Aucun matricule fourni"}), 400

        matricules = data['matricules']
        
        # Crée un fichier ZIP en mémoire
        memory_file = io.BytesIO()
        
        nombre_fichiers = 0
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Ajoute les images correspondantes aux matricules
            tech_logger.info("Début du traitement de la sélection de photos.")
            for matricule in matricules:
                # Assainir le nom du fichier pour la sécurité
                if not matricule or '..' in matricule or '/' in matricule or '\\' in matricule:
                    tech_logger.warning(f"Matricule '{matricule}' ignoré (invalide ou potentiellement dangereux).")
                    continue

                image_filename = f"{matricule}.jpg"
                image_path = os.path.join(APERÇUS_DIR, image_filename)
                
                tech_logger.info(f"Recherche de l'image : '{image_path}'")
                
                if os.path.exists(image_path):
                    zf.write(image_path, arcname=image_filename)
                    nombre_fichiers += 1
                    tech_logger.info(f"Image '{image_filename}' trouvée et ajoutée au ZIP.")
                else:
                    tech_logger.warning(f"Image '{image_filename}' non trouvée. Fichier ignoré.")
            
            tech_logger.info("Fin du traitement de la sélection de photos.")

            # 2. Ajoute tous les fichiers du dossier CGU
            tech_logger.info("Traitement des fichiers CGU.")
            if os.path.exists(CGU_DIR):
                for cgu_filename in os.listdir(CGU_DIR):
                    cgu_path = os.path.join(CGU_DIR, cgu_filename)
                    if os.path.isfile(cgu_path):
                         # Ajoute le fichier à l'archive dans un sous-dossier "CGU"
                        zf.write(cgu_path, arcname=os.path.join('CGU', cgu_filename))
                        tech_logger.info(f"Fichier CGU '{cgu_filename}' ajouté au ZIP.")

        # Se positionner au début du fichier en mémoire avant de l'envoyer
        memory_file.seek(0)
        
        # Log applicatif
        app_logger.info(f"IP: {request.remote_addr}, Fichiers téléchargés: {nombre_fichiers}")

        tech_logger.info(f"Envoi du fichier ZIP à {request.remote_addr} avec {nombre_fichiers} fichier(s).")
        return send_file(
            memory_file,
            download_name='selection.zip',
            as_attachment=True,
            mimetype='application/zip'
        )

    except Exception as e:
        # Log l'erreur côté serveur pour le débogage
        tech_logger.error(f"Une erreur est survenue lors de la création du ZIP pour {request.remote_addr}: {e}", exc_info=True)
        return jsonify({"error": "Une erreur interne est survenue sur le serveur."}), 500

if __name__ == '__main__':
    # Lance le serveur sur le port 5000, accessible depuis n'importe quelle IP de la machine
    tech_logger.info("Démarrage du serveur Flask sur le port 5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

