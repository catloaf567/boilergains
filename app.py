
from flask import Flask, request, send_from_directory, jsonify
import os
import traceback
from typing import Tuple

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
        carbs_goal = float(data.get('carbs_goal', 0))
        fat_goal = float(data.get('fat_goal', 0))
        fiber_goal = float(data.get('fiber_goal', 0))
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
        goals = {
            'calorie': calorie_goal,
            'protein': protein_goal,
            'carbs': carbs_goal,
            'fat': fat_goal,
            'fiber': fiber_goal,
        }
        return jsonify(success=True, text=text, meal=meal, goals=goals), 200
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error='Error computing suggestion: ' + str(e) + '\n' + tb), 500


def _activity_multiplier(activity_level: str) -> float:
    key = (activity_level or 'sedentary').strip().lower()
    return {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'athlete': 1.9,
    }.get(key, 1.2)


def _protein_factor_for_activity(age: float, activity_level: str) -> float:
    key = (activity_level or 'sedentary').strip().lower()
    base = {
        'sedentary': 1.1,
        'light': 1.3,
        'moderate': 1.5,
        'active': 1.7,
        'athlete': 1.9,
    }.get(key, 1.2)
    if age >= 60:
        base = max(base, 1.3)
    return base


def _recommended_goals(age: float, gender: str, height_cm: float, weight_kg: float,
                       activity_level: str, meals_per_day: int = 3):
    """Return per-meal and daily goals for calories, protein, carbs, fat, fiber.

    Returns a dict with keys:
      per_meal_cal, per_meal_protein, per_meal_carbs, per_meal_fat, per_meal_fiber,
      daily_cal, daily_protein, daily_carbs, daily_fat, daily_fiber
    """
    if meals_per_day <= 0:
        raise ValueError('meals_per_day must be positive')
    gender_key = (gender or 'unspecified').strip().lower()
    gender_offset = {
        'male': 5,
        'female': -161,
        'unspecified': 5,
    }.get(gender_key, 5)

    # Basal metabolic rate (Mifflin-St Jeor-like)
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + gender_offset
    activity_factor = _activity_multiplier(activity_level)
    daily_calories = max(bmr * activity_factor, 1200.0)

    # Protein: use weight-based recommendation scaled by activity
    protein_factor = _protein_factor_for_activity(age, activity_level)
    daily_protein = max(weight_kg * protein_factor, 45.0)

    # Carbs: 50% of calories, fat: 25% of calories, fiber: 14g per 1000 kcal
    carbs_cal = daily_calories * 0.50
    fat_cal = daily_calories * 0.25
    daily_carbs = carbs_cal / 4.0
    daily_fat = fat_cal / 9.0
    daily_fiber = (daily_calories / 1000.0) * 14.0

    per_meal = lambda v: v / meals_per_day

    return {
        'per_meal_cal': per_meal(daily_calories),
        'per_meal_protein': per_meal(daily_protein),
        'per_meal_carbs': per_meal(daily_carbs),
        'per_meal_fat': per_meal(daily_fat),
        'per_meal_fiber': per_meal(daily_fiber),
        'daily_cal': daily_calories,
        'daily_protein': daily_protein,
        'daily_carbs': daily_carbs,
        'daily_fat': daily_fat,
        'daily_fiber': daily_fiber,
    }


def _format_meal_response(meal: dict, foods: dict, protein_window: float = 5.0, max_options: int = 4) -> str:
    """Return formatted text for the top meal and alternatives within +/-protein_window grams protein."""
    best_lines = ["Top recommendation:", format_meal(meal, foods)]

    base_protein = meal.get('total_protein', 0.0)
    seen_items = {tuple(meal.get('items', []))}
    alt_blocks = []
    for alt in meal.get('alternatives', []):
        items = tuple(alt.get('items', []))
        if items in seen_items:
            continue
        seen_items.add(items)
        total_protein = alt.get('total_protein', 0.0)
        if abs(total_protein - base_protein) > protein_window:
            continue
        alt_blocks.append(format_meal(alt, foods))
        if len(alt_blocks) >= max_options:
            break

    if not alt_blocks:
        return '\n'.join(best_lines)

    lines = best_lines
    lines.append('')
    lines.append(f'Other options within +/-{protein_window:.0f} g protein:')
    for idx, block in enumerate(alt_blocks, start=1):
        lines.append(f'Option {idx}:')
        lines.append(block)
        if idx != len(alt_blocks):
            lines.append('')
    return '\n'.join(lines)


@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json() or {}
    try:
        age = float(data.get('age', 0))
        height_cm = float(data.get('height_cm', 0))
        weight_kg = float(data.get('weight_kg', 0))
    except (TypeError, ValueError):
        return jsonify(success=False, error='Invalid demographic values supplied.'), 400

    if age <= 0 or height_cm <= 0 or weight_kg <= 0:
        return jsonify(success=False, error='Please provide positive numbers for age, height, and weight.'), 400

    if age > 120 or height_cm > 260 or weight_kg > 350:
        return jsonify(success=False, error='Provided age, height, or weight is outside acceptable range.'), 400

    gender = str(data.get('gender', 'unspecified'))
    activity_level = str(data.get('activity_level', 'sedentary'))
    meals_per_day = data.get('meals_per_day', 3)
    try:
        meals_per_day = int(meals_per_day)
    except (TypeError, ValueError):
        return jsonify(success=False, error='meals_per_day must be an integer.'), 400
    if meals_per_day <= 0 or meals_per_day > 8:
        return jsonify(success=False, error='meals_per_day must be between 1 and 8.'), 400
    goals = _recommended_goals(
        age,
        gender,
        height_cm,
        weight_kg,
        activity_level,
        meals_per_day=meals_per_day,
    )
    return jsonify(
        success=True,
        per_meal_calorie=round(goals['per_meal_cal'], 1),
        per_meal_protein=round(goals['per_meal_protein'], 1),
        per_meal_carbs=round(goals['per_meal_carbs'], 1),
        per_meal_fat=round(goals['per_meal_fat'], 1),
        per_meal_fiber=round(goals['per_meal_fiber'], 1),
        daily_calorie_goal=round(goals['daily_cal'], 1),
        daily_protein_goal=round(goals['daily_protein'], 1),
        daily_carbs=round(goals['daily_carbs'], 1),
        daily_fat=round(goals['daily_fat'], 1),
        daily_fiber=round(goals['daily_fiber'], 1),
        meals_per_day=meals_per_day,
    )


if __name__ == '__main__':
    # run server; open http://127.0.0.1:5000 in your browser (do not open index.html via file://)
    app.run(host='127.0.0.1', port=5000, debug=True)

    
