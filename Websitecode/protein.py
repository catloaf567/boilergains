import math
import itertools
from typing import Dict, Any, List, Tuple, Optional

try:
    import pandas as pd
except Exception:  # pandas may not be installed in user's environment
    pd = None  # type: ignore


def _normalize_columns(df: "pd.DataFrame") -> Dict[str, str]:
    """Map common column names to canonical keys used by the loader.

    Returns a dict mapping canonical keys to actual column names in the dataframe.
    Canonical keys: name, calories, protein, carbs, fat, serving, vegan, allergens
    """
    colmap = {}
    lower_map = {c.lower(): c for c in df.columns}

    def find(*options):
        for o in options:
            key = o.lower()
            if key in lower_map:
                return lower_map[key]
        return None

    colmap['name'] = find('food', 'item', 'name') or df.columns[0]
    colmap['calories'] = find('calories', 'kcal', 'energy')
    colmap['protein'] = find('protein', 'prot', 'proteins')
    colmap['carbs'] = find('carbs', 'carbohydrates', 'carb')
    colmap['fat'] = find('fat', 'fats')
    colmap['serving'] = find('serving size', 'serving', 'portion')
    colmap['vegan'] = find('vegan', 'is_vegan', 'vegan?')
    colmap['allergens'] = find('allergens', 'allergy', 'contains')
    return colmap


def load_foods_from_excel(path: str) -> Dict[str, Dict[str, Any]]:
    """Load foods from an Excel file into a dictionary.

    The returned dict maps food name -> {calories, protein, carbs, fat, serving, vegan, allergens}
    The loader is forgiving: it searches for common column name variants.
    """
    if pd is None:
        raise RuntimeError('pandas is required to read Excel files. Install with: pip install -r requirements.txt')

    df = pd.read_excel(path)
    if df.empty:
        return {}

    cols = _normalize_columns(df)
    foods: Dict[str, Dict[str, Any]] = {}

    for _, row in df.iterrows():
        name = str(row.get(cols['name'], '')).strip()
        if not name:
            continue

        def _get(key, as_type=float, default=0):
            col = cols.get(key)
            if not col or col not in row:
                return default
            v = row[col]
            if pd.isna(v):
                return default
            try:
                return as_type(v)
            except Exception:
                # fallback for textual numbers like '12 g'
                s = str(v)
                num = ''.join(ch for ch in s if (ch.isdigit() or ch == '.' or ch == '-'))
                try:
                    return as_type(num) if num else default
                except Exception:
                    return default

        calories = _get('calories', float, 0.0)
        protein = _get('protein', float, 0.0)
        carbs = _get('carbs', float, 0.0)
        fat = _get('fat', float, 0.0)

        serving = None
        s_col = cols.get('serving')
        if s_col and s_col in row and not pd.isna(row[s_col]):
            serving = str(row[s_col])

        vegan_val = False
        v_col = cols.get('vegan')
        if v_col and v_col in row and not pd.isna(row[v_col]):
            vv = str(row[v_col]).strip().lower()
            vegan_val = vv in ('y', 'yes', 'true', '1', 'vegan')

        allergens = ''
        a_col = cols.get('allergens')
        if a_col and a_col in row and not pd.isna(row[a_col]):
            allergens = str(row[a_col]).strip()

        foods[name] = {
            'calories': float(calories),
            'protein': float(protein),
            'carbs': float(carbs),
            'fat': float(fat),
            'serving': serving,
            'vegan': bool(vegan_val),
            'allergens': allergens,
        }

    return foods


def sort_by_protein(foods: Dict[str, Dict[str, Any]]) -> List[Tuple[str, float]]:
    return sorted(((name, info.get('protein', 0.0)) for name, info in foods.items()), key=lambda x: x[1], reverse=True)


def sort_by_carbs(foods: Dict[str, Dict[str, Any]]) -> List[Tuple[str, float]]:
    return sorted(((name, info.get('carbs', 0.0)) for name, info in foods.items()), key=lambda x: x[1], reverse=True)


def sort_by_fat(foods: Dict[str, Dict[str, Any]]) -> List[Tuple[str, float]]:
    return sorted(((name, info.get('fat', 0.0)) for name, info in foods.items()), key=lambda x: x[1], reverse=True)


def _filter_candidates(foods: Dict[str, Dict[str, Any]], vegan: bool, allergen: Optional[str]) -> List[Tuple[str, Dict[str, Any]]]:
    allergen = (allergen or '').strip().lower() if allergen else ''
    result = []
    for name, info in foods.items():
        if vegan and not info.get('vegan', False):
            continue
        if allergen:
            a = str(info.get('allergens', '')).lower()
            if allergen in a:
                continue
        result.append((name, info))
    return result


def suggest_meal(foods: Dict[str, Dict[str, Any]], calorie_goal: float, protein_goal: float,
                 vegan: bool = False, allergen: Optional[str] = None,
                 tolerance: float = 0.07, max_items: int = 3, max_servings: int = 3,
                 top_k: int = 30) -> Optional[Dict[str, Any]]:
    """Suggest a meal (combination of items and integer servings) that meets calorie and protein goals.

    Strategy:
    - Filter candidates by vegan/allergen
    - Rank candidates by protein per serving (or protein/calorie)
    - Greedy/brute-force search over small combinations of items and integer servings
    - Return best match minimizing normalized distance to both goals
    """
    candidates = _filter_candidates(foods, vegan, allergen)
    if not candidates:
        return None

    # compute protein density to pick top candidates
    scored = []
    for name, info in candidates:
        protein = info.get('protein', 0.0)
        calories = info.get('calories', 0.0) or 1.0
        scored.append((name, info, protein / calories if calories else protein))

    scored.sort(key=lambda x: x[2], reverse=True)
    scored = scored[:top_k]

    names = [s[0] for s in scored]

    # iterative tolerance relaxation
    tolerances = [tolerance, tolerance * 2, tolerance * 3]
    best = None
    best_score = float('inf')

    for tol in tolerances:
        low_cal = calorie_goal * (1 - tol)
        high_cal = calorie_goal * (1 + tol)
        low_pro = protein_goal * (1 - tol)
        high_pro = protein_goal * (1 + tol)

        # try combinations of 1..max_items items
        for r in range(1, min(max_items, len(names)) + 1):
            for combo in itertools.combinations(names, r):
                # iterate through possible servings for each item
                ranges = [range(1, max_servings + 1)] * r
                for servings in itertools.product(*ranges):
                    total_cal = 0.0
                    total_pro = 0.0
                    items = []
                    for name_i, s in zip(combo, servings):
                        info = foods[name_i]
                        total_cal += info.get('calories', 0.0) * s
                        total_pro += info.get('protein', 0.0) * s
                        items.append((name_i, s))

                    if not (low_cal <= total_cal <= high_cal and low_pro <= total_pro <= high_pro):
                        continue

                    # compute a score for tie-breaking (normalized distance)
                    cal_diff = abs(total_cal - calorie_goal) / (calorie_goal or 1)
                    pro_diff = abs(total_pro - protein_goal) / (protein_goal or 1)
                    score = cal_diff + pro_diff
                    if score < best_score:
                        best_score = score
                        best = {
                            'items': items,
                            'total_calories': total_cal,
                            'total_protein': total_pro,
                            'tolerance_used': tol,
                        }
        if best:
            break

    return best


def format_meal(meal: Dict[str, Any], foods: Dict[str, Dict[str, Any]]) -> str:
    if not meal:
        return 'No suitable meal found.'
    lines = []
    for name, servings in meal['items']:
        info = foods.get(name, {})
        c = info.get('calories', 0.0) * servings
        p = info.get('protein', 0.0) * servings
        lines.append(f"{servings} x {name} — {c:.0f} kcal, {p:.1f} g protein")
    lines.append(f"Total: {meal['total_calories']:.0f} kcal, {meal['total_protein']:.1f} g protein (tol {meal['tolerance_used']*100:.0f}% )")
    return '\n'.join(lines)


def _safe_float_input(prompt: str) -> float:
    while True:
        try:
            v = input(prompt)
            return float(v)
        except Exception:
            print('Please enter a number (e.g., 2000 or 50).')


def main():
    import os
    print('Meal suggestion assistant')
    path = 'Windsor-20250922.xlsx'


    cal_goal = _safe_float_input('Enter calorie goal (kcal): ')
    pro_goal = _safe_float_input('Enter protein goal (g): ')
    veg = input('Are you vegan? (y/n): ').strip().lower() in ('y', 'yes')
    allergen = input('Allergen to avoid (leave blank if none): ').strip()

    meal = suggest_meal(foods, cal_goal, pro_goal, vegan=veg, allergen=allergen or None)
    print('\nSuggested meal:')
    print(format_meal(meal, foods) if meal else 'No matching meal found.')


if __name__ == '__main__':
    main()
