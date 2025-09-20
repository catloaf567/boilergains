import math
import itertools
import json
import difflib
from typing import Dict, Any, List, Tuple, Optional

try:
    import pandas as pd
except Exception:  # pandas may not be installed in user's environment
    pd = None  # type: ignore


def _normalize_columns(df) -> Dict[str, str]:
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
    colmap['fiber'] = find('fiber', 'fibre')
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
        fiber = _get('fiber', float, 0.0)

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
            'fiber': float(fiber),
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

    # Load pairings from external config if available (pairings.json) for easy editing.
    PAIRS = {}
    try:
        with open('pairings.json', 'r', encoding='utf-8') as f:
            PAIRS = json.load(f)
    except Exception:
        # fallback built-in map if file missing or invalid
        PAIRS = {
            'hamburger': ['bun', 'bread', 'roll', 'fries'],
            'burger': ['bun', 'bread', 'roll', 'fries'],
            'hot dog': ['bun', 'ketchup', 'mustard'],
            'taco': ['shell', 'tortilla', 'salsa'],
            'chicken': ['rice', 'salad', 'wrap', 'bread'],
            'steak': ['potato', 'rice', 'salad'],
            'yogurt': ['granola', 'berries', 'fruit'],
            'granola': ['yogurt', 'milk', 'berries'],
            'oatmeal': ['milk', 'berries', 'banana'],
            'pancake': ['syrup', 'butter'],
            'eggs': ['toast', 'bacon', 'sausage'],
            'bacon': ['eggs', 'toast'],
            'salad': ['dressing', 'bread', 'chicken', 'tofu'],
            'rice': ['chicken', 'beans', 'tofu'],
            'beans': ['rice', 'tortilla'],
            'pizza': ['bread', 'cheese'],
            'sushi': ['soy', 'wasabi', 'ginger'],
            'bagel': ['cream cheese', 'lox', 'butter'],
        }

    # fuzzy pair detection using difflib to handle synonyms/typos
    def companion_present(lower_combo: List[str], companion: str) -> bool:
        # exact substring match
        if any(companion in item for item in lower_combo):
            return True
        # token-level fuzzy match using difflib on words
        words = set()
        for it in lower_combo:
            for w in it.replace('-', ' ').split():
                words.add(w)
        # find close matches for the companion among tokens
        matches = difflib.get_close_matches(companion, list(words), n=1, cutoff=0.8)
        return bool(matches)

    def pairs_ok(combo: Tuple[str, ...]) -> bool:
        lower = [c.lower() for c in combo]
        for key, companions in PAIRS.items():
            if any(key in item for item in lower):
                found = False
                for companion in companions:
                    if companion_present(lower, companion):
                        found = True
                        break
                if not found:
                    # allow single-item combos if that item is calorically substantial (heuristic)
                    for item in lower:
                        if key in item:
                            # find the canonical food name in foods matching this lowered item
                            canonical = next((n for n in foods if n.lower() == item), None)
                            if canonical:
                                info = foods.get(canonical)
                                if info and info.get('calories', 0) >= 400:
                                    found = True
                                    break
                    if not found:
                        return False
        return True

    # iterative tolerance relaxation
    tolerances = [tolerance, tolerance * 2, tolerance * 3]
    best = None
    best_score = float('inf')
    solutions: List[Dict[str, Any]] = []

    # helper: cap servings for very-high-protein items; default max 1 serving for items >20g protein
    def max_servings_for_item(info: Dict[str, Any]) -> int:
        base = max_servings
        if info.get('protein', 0.0) > 20:
            return min(base, 1)
        return base

    for tol in tolerances:
        low_cal = calorie_goal * (1 - tol)
        high_cal = calorie_goal * (1 + tol)
        low_pro = protein_goal * (1 - tol)
        high_pro = protein_goal * (1 + tol)

        # try combinations of 1..max_items items
        for r in range(1, min(max_items, len(names)) + 1):
            for combo in itertools.combinations(names, r):
                # determine per-item serving ranges honoring high-protein cap
                per_item_ranges = []
                for name_i in combo:
                    info = foods[name_i]
                    m = max_servings_for_item(info)
                    per_item_ranges.append(range(1, m + 1))

                # iterate through possible servings for each item
                for servings in itertools.product(*per_item_ranges):
                    total_cal = 0.0
                    total_pro = 0.0
                    total_carbs = 0.0
                    total_fiber = 0.0
                    items = []
                    for name_i, s in zip(combo, servings):
                        info = foods[name_i]
                        total_cal += info.get('calories', 0.0) * s
                        total_pro += info.get('protein', 0.0) * s
                        total_carbs += info.get('carbs', 0.0) * s
                        total_fiber += info.get('fiber', 0.0) * s
                        items.append((name_i, s))

                    # skip combos that violate simple pairing rules
                    if not pairs_ok(combo):
                        continue

                    if not (low_cal <= total_cal <= high_cal and low_pro <= total_pro <= high_pro):
                        continue

                    # compute a score for tie-breaking (normalized distance)
                    cal_diff = abs(total_cal - calorie_goal) / (calorie_goal or 1)
                    pro_diff = abs(total_pro - protein_goal) / (protein_goal or 1)
                    score = cal_diff + pro_diff
                    sol = {
                        'items': items,
                        'total_calories': total_cal,
                        'total_protein': total_pro,
                        'total_carbs': total_carbs,
                        'total_fiber': total_fiber,
                        'tolerance_used': tol,
                        'score': score,
                    }
                    solutions.append(sol)
                    if score < best_score:
                        best_score = score
                        best = sol
        if best:
            break

    # sort solutions and attach top alternatives
    if not best:
        return None
    solutions.sort(key=lambda x: x.get('score', float('inf')))
    best['alternatives'] = solutions[:6]
    return best


def format_meal(meal: Dict[str, Any], foods: Dict[str, Dict[str, Any]]) -> str:
    if not meal:
        return 'No suitable meal found.'
    lines = []
    for name, servings in meal['items']:
        info = foods.get(name, {})
        c = info.get('calories', 0.0) * servings
        p = info.get('protein', 0.0) * servings
        carbs = info.get('carbs', 0.0) * servings
        fiber = info.get('fiber', 0.0) * servings
        serving_desc = info.get('serving') or '1 serving'
        lines.append(f"{servings} x {name} ({serving_desc}) — {c:.0f} kcal, {p:.1f} g protein, {carbs:.1f} g carbs, {fiber:.1f} g fiber")
    lines.append(f"Total: {meal['total_calories']:.0f} kcal, {meal['total_protein']:.1f} g protein, {meal.get('total_carbs', 0.0):.1f} g carbs, {meal.get('total_fiber', 0.0):.1f} g fiber (tol {meal['tolerance_used']*100:.0f}% )")
    return '\n'.join(lines)


def list_available_items(foods: Dict[str, Dict[str, Any]], vegan: bool = False, allergen: Optional[str] = None) -> List[str]:
    """Return a sorted list of available food item names after applying vegan/allergen filters."""
    candidates = _filter_candidates(foods, vegan, allergen)
    names = sorted([name for name, _ in candidates])
    for idx, n in enumerate(names, 1):
        info = foods.get(n, {})
        print(f"{idx}. {n} — {info.get('calories',0):.0f} kcal, {info.get('protein',0):.1f} g protein, serving: {info.get('serving')}")
    return names


def suggest_from_shortlist(foods: Dict[str, Dict[str, Any]], shortlist: List[str], calorie_goal: float, protein_goal: float,
                           tolerance: float = 0.07, max_items: int = 3, max_servings: int = 3) -> Optional[Dict[str, Any]]:
    """Similar to suggest_meal but restricts candidate set to the provided shortlist of names."""
    subfoods = {n: foods[n] for n in shortlist if n in foods}
    return suggest_meal(subfoods, calorie_goal, protein_goal, vegan=False, allergen=None,
                        tolerance=tolerance, max_items=max_items, max_servings=max_servings, top_k=len(subfoods))


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
    path = input('Path to Excel dataset (press Enter for Windsor-20250922.xlsx): ').strip() or 'Windsor-20250922.xlsx'
    pairings_path = input('Path to pairing JSON (press Enter for pairings.json in repo): ').strip() or 'pairings.json'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    try:
        foods = load_foods_from_excel(path)
    except Exception as e:
        print('Error loading file:', e)
        return

    # if a custom pairing file was specified and exists, inform the user and it will be used by suggest_meal
    if pairings_path and os.path.exists(pairings_path):
        print(f'Using pairing config: {pairings_path}')
        # copy to default name so suggest_meal picks it up (simple approach)
        try:
            import shutil
            shutil.copy(pairings_path, 'pairings.json')
        except Exception:
            # ignore failure; suggest_meal will fallback to built-in map
            pass

    cal_goal = _safe_float_input('Enter calorie goal (kcal): ')
    pro_goal = _safe_float_input('Enter protein goal (g): ')
    veg = input('Are you vegan? (y/n): ').strip().lower() in ('y', 'yes')
    allergen = input('Allergen to avoid (leave blank if none): ').strip()

    use_shortlist = input('Would you like to shortlist items to choose from first? (y/n): ').strip().lower() in ('y', 'yes')
    chosen_shortlist: Optional[List[str]] = None
    if use_shortlist:
        print('\nAvailable items:')
        names = list_available_items(foods, vegan=veg, allergen=allergen or None)
        sel = input('\nEnter the numbers of items you want to consider (comma separated), or press Enter to use all: ').strip()
        if sel:
            try:
                idxs = [int(s.strip()) - 1 for s in sel.split(',') if s.strip()]
                chosen_shortlist = [names[i] for i in idxs if 0 <= i < len(names)]
            except Exception:
                print('Invalid selection; using all items')
                chosen_shortlist = names
        else:
            chosen_shortlist = names

    if chosen_shortlist:
        meal = suggest_from_shortlist(foods, chosen_shortlist, cal_goal, pro_goal)
    else:
        meal = suggest_meal(foods, cal_goal, pro_goal, vegan=veg, allergen=allergen or None)

    if not meal:
        print('\nNo matching meal found.')
        return

    # Present alternatives if available
    alts = meal.get('alternatives', []) if isinstance(meal, dict) else []
    print('\nSuggested meal (best match):')
    print(format_meal(meal, foods))
    if alts:
        print('\nOther close options:')
        for i, a in enumerate(alts, 1):
            print(f'\nOption {i}:')
            print(format_meal(a, foods))
        pick = input('\nEnter option number to accept (or press Enter to keep best): ').strip()
        if pick:
            try:
                p = int(pick) - 1
                if 0 <= p < len(alts):
                    chosen = alts[p]
                    print('\nYou selected:')
                    print(format_meal(chosen, foods))
            except Exception:
                print('Invalid choice; keeping best match.')


if __name__ == '__main__':
    main()
