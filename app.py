
from flask import Flask, request, send_from_directory, jsonify
import os
import traceback

app = Flask(__name__, static_folder='.', static_url_path='')

# try to enable CORS if flask_cors is available (helps if you load files from other origins)
try:
    from flask_cors import CORS
    CORS(app)
except Exception:
    pass

# Import functions from protein.py
try:
    from protein import load_foods_from_excel, suggest_meal, format_meal
except Exception as e:
    load_foods_from_excel = None
    suggest_meal = None
    format_meal = None
    _import_error = str(e)
else:
    _import_error = None


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


@app.route('/suggest', methods=['POST'])
def suggest():
    if _import_error:
        return jsonify(success=False, error='Failed to import protein module: ' + _import_error), 500

    data = request.get_json() or {}
    path = data.get('path', 'Windsor-20250922.xlsx')
    try:
        calorie_goal = float(data.get('calorie_goal', 0))
        protein_goal = float(data.get('protein_goal', 0))
    except Exception:
        return jsonify(success=False, error='Invalid numeric inputs'), 400
    vegan = bool(data.get('vegan', False))
    allergen = data.get('allergen') or None

    # ensure path is server-side and exists
    if not os.path.exists(path):
        return jsonify(success=False, error=f'File not found on server: {path}'), 400

    try:
        foods = load_foods_from_excel(path)
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error='Error loading Excel: ' + str(e) + '\n' + tb), 500

    try:
        meal = suggest_meal(foods, calorie_goal, protein_goal, vegan=vegan, allergen=allergen)
        if not meal:
            return jsonify(success=False, error='No suitable meal found.'), 200
        text = format_meal(meal, foods)
        return jsonify(success=True, text=text), 200
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error='Error computing suggestion: ' + str(e) + '\n' + tb), 500


if __name__ == '__main__':
    # run server; open http://127.0.0.1:5000 in your browser (do not open index.html via file://)
    app.run(host='127.0.0.1', port=5000, debug=True)

    