import math
import itertools
import json
import difflib
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional


EXCLUSION_TOKEN_MAP: Dict[str, List[str]] = {
    'beef': ['beef', 'meat', 'hamburger', 'burger', 'sausage', 'pepperoni', 'peperoni'],
    'pork': ['pork', 'ham'],
    'chicken': ['chicken'],
    'turkey': ['turkey'],
    'lamb': ['lamb'],
    'fish': ['fish'],
    'seafood': ['seafood'],
    'shellfish': ['shellfish', 'shrimp', 'crab', 'lobster', 'clam', 'oyster', 'scallop'],
    'milk': ['milk', 'dairy', 'cheese', 'cream', 'butter', 'yogurt'],
    'egg': ['egg', 'eggs'],
}
def expand_excluded_items(selected: Optional[List[str]]) -> List[str]:
    """Return normalized tokens for exclusion selections from the UI."""
    tokens: List[str] = []
    if not selected:
        return tokens
    for item in selected:
        key = str(item or '').strip().lower()
        if not key:
            continue
        mapped = EXCLUSION_TOKEN_MAP.get(key)
        if mapped:
            tokens.extend(mapped)
        else:
            tokens.append(key)
    # de-duplicate while preserving order
    seen = set()
    unique_tokens: List[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique_tokens.append(token)
    return unique_tokens


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


def _filter_candidates(foods: Dict[str, Dict[str, Any]], vegan: bool, allergen: Optional[str], excluded_meats: Optional[List[str]] = None) -> List[Tuple[str, Dict[str, Any]]]:
    """Filter candidate foods by vegan/allergen/explicit meat exclusions.

    excluded_meats: optional list of lowercase meat tokens to exclude (e.g., ['beef', 'pork']).
    If a food's name or allergens mention any excluded meat, it will be filtered out.
    """
    allergen = (allergen or '').strip().lower() if allergen else ''
    excluded_meats = [m.lower() for m in (excluded_meats or [])]
    result = []
    for name, info in foods.items():
        lname = name.lower()
        if vegan and not info.get('vegan', False):
            continue
        if allergen:
            a = str(info.get('allergens', '')).lower()
            if allergen in a:
                continue
        # meat exclusions: check name and allergens for tokens
        skip = False
        if excluded_meats:
            a = str(info.get('allergens', '')).lower()
            for m in excluded_meats:
                if m in lname or m in a:
                    skip = True
                    break
        if skip:
            continue
        result.append((name, info))
    return result


def suggest_meal(foods: Dict[str, Dict[str, Any]], calorie_goal: float, protein_goal: float,
                 vegan: bool = False, allergen: Optional[str] = None,
                 excluded_meats: Optional[List[str]] = None,
                 tolerance: float = 0.1, max_items: int = 4, max_servings: float = 3.0,
                 serving_step: float = 0.5, top_k: int = 10, protein_window: float = 10.0,
                 max_alternatives: int = 5) -> Optional[Dict[str, Any]]:
    """Suggest a meal (combination of items and fractional servings) that meets calorie and protein goals.

    Strategy:
    - Filter candidates by vegan/allergen
    - Rank candidates by protein per serving (or protein/calorie)
    - Greedy/brute-force search over small combinations of up to `max_items` using configurable serving steps
    - Return best match minimizing normalized distance to both goals
    """
    candidates = _filter_candidates(foods, vegan, allergen, excluded_meats=excluded_meats)
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
    all_candidates: List[Dict[str, Any]] = []

    serving_step = max(0.1, float(serving_step))

    # helper: cap servings for very-high-protein items; default max 1 serving for items >20g protein
    def max_servings_for_item(info: Dict[str, Any]) -> int:
        base = float(max_servings)
        if info.get('protein', 0.0) > 20:
            base = min(base, 1.0)
        max_units = int(math.floor(base + 1e-9))
        return max(1, max_units)

    def serving_values_for_item(info: Dict[str, Any]) -> List[float]:
        max_serv = max_servings_for_item(info)
        return [float(i) for i in range(1, max_serv + 1)]

    def _solution_signature(entry: Dict[str, Any]) -> Tuple[str, ...]:
        items = entry.get('items', [])
        names = sorted(name for name, _ in items)
        return tuple(names)

    for tol in tolerances:
        low_cal = calorie_goal * (1 - tol)
        high_cal = calorie_goal * (1 + tol)
        low_pro = protein_goal * (1 - tol)
        high_pro = protein_goal * (1 + tol)

        # try combinations of 1..max_items items
        for r in range(1, min(max_items, len(names)) + 1):
            for combo in itertools.combinations(names, r):
                # determine per-item serving ranges honoring high-protein cap
                per_item_ranges: List[List[float]] = []
                skip_combo = False
                for name_i in combo:
                    info = foods[name_i]
                    options = serving_values_for_item(info)
                    if not options:
                        skip_combo = True
                        break
                    per_item_ranges.append(options)
                if skip_combo:
                    continue

                # iterate through possible servings for each item
                for servings in itertools.product(*per_item_ranges):
                    total_cal = 0.0
                    total_pro = 0.0
                    total_fat = 0.0
                    total_carbs = 0.0
                    total_fiber = 0.0
                    items = []
                    for name_i, s in zip(combo, servings):
                        qty = float(int(round(s)))
                        info = foods[name_i]
                        total_cal += info.get('calories', 0.0) * qty
                        total_pro += info.get('protein', 0.0) * qty
                        total_fat += info.get('fat', 0.0) * qty
                        total_carbs += info.get('carbs', 0.0) * qty
                        total_fiber += info.get('fiber', 0.0) * qty
                        items.append((name_i, qty))

                    # skip combos that violate simple pairing rules
                    if not pairs_ok(combo):
                        continue

                    # compute a score for tie-breaking (normalized distance)
                    cal_diff = abs(total_cal - calorie_goal) / (calorie_goal or 1)
                    pro_diff = abs(total_pro - protein_goal) / (protein_goal or 1)
                    score = cal_diff + pro_diff
                    within = low_cal <= total_cal <= high_cal and low_pro <= total_pro <= high_pro
                    sol = {
                        'items': items,
                        'total_calories': total_cal,
                        'total_protein': total_pro,
                        'total_fat': total_fat,
                        'total_carbs': total_carbs,
                        'total_fiber': total_fiber,
                        'tolerance_used': tol,
                        'score': score,
                        'within_tolerance': within,
                    }
                    all_candidates.append(sol)
                    if not within:
                        continue

                    solutions.append(sol)
                    if score < best_score:
                        best_score = score
                        best = sol
        if best:
            break

    def _dedupe(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best_by_sig: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        for entry in entries:
            sig = _solution_signature(entry)
            existing = best_by_sig.get(sig)
            if existing is None or entry.get('score', float('inf')) < existing.get('score', float('inf')):
                best_by_sig[sig] = entry
        return list(best_by_sig.values())

    solutions = _dedupe(solutions)
    all_candidates = _dedupe(all_candidates)

    pool: List[Dict[str, Any]]
    if solutions:
        pool = sorted(solutions, key=lambda x: x.get('score', float('inf')))
        best = pool[0]
    else:
        pool = sorted(all_candidates, key=lambda x: x.get('score', float('inf')))
        if not pool:
            return None
        best = pool[0]

    best_protein = best.get('total_protein', 0.0)
    best_signature = _solution_signature(best)
    seen_signatures = {best_signature}
    alternatives: List[Dict[str, Any]] = []
    for sol in pool:
        if sol is best:
            continue
        sig = _solution_signature(sol)
        if sig in seen_signatures:
            continue
        if abs(sol.get('total_protein', 0.0) - best_protein) > protein_window:
            continue
        alternatives.append(sol)
        seen_signatures.add(sig)
        if len(alternatives) >= max_alternatives:
            break

    best['alternatives'] = alternatives
    return best


def format_meal(meal: Dict[str, Any], foods: Dict[str, Dict[str, Any]]) -> str:
    if not meal:
        return 'No suitable meal found.'
    lines = []
    for name, servings in meal['items']:
        info = foods.get(name, {})
        qty = max(1, int(round(servings)))
        c = info.get('calories', 0.0) * qty
        p = info.get('protein', 0.0) * qty
        fat = info.get('fat', 0.0) * qty
        carbs = info.get('carbs', 0.0) * qty
        fiber = info.get('fiber', 0.0) * qty
        serving_desc = info.get('serving') or '1 serving'
        qty_label = 'serving' if qty == 1 else 'servings'
        lines.append(
            f"- <strong>{name}</strong> ({serving_desc}, {qty} {qty_label}) — {c:.0f} kcal, {p:.1f} g protein, {fat:.1f} g fat, {carbs:.1f} g carbs, {fiber:.1f} g fiber"
        )
    lines.append(
        f"Total: {meal['total_calories']:.0f} kcal, {meal['total_protein']:.1f} g protein, {meal.get('total_fat', 0.0):.1f} g fat, {meal.get('total_carbs', 0.0):.1f} g carbs, {meal.get('total_fiber', 0.0):.1f} g fiber"
    )
    return '\n'.join(lines)


def _progress_bar(value: float, target: float, width: int = 30) -> str:
    if target <= 0:
        return ''
    frac = min(max(value / target, 0.0), 1.0)
    filled = int(round(frac * width))
    return '[' + '#' * filled + '-' * (width - filled) + f'] {value:.0f}/{target:.0f}'


def pretty_print_meal(meal: Dict[str, Any], foods: Dict[str, Dict[str, Any]], calorie_goal: float = 0, protein_goal: float = 0, carbs_goal: float = 0, fat_goal: float = 0, fiber_goal: float = 0) -> None:
    """Print the meal in a neat table with progress bars for calories and protein."""
    if not meal:
        print('No suitable meal found.')
        return

    items = meal['items']
    # determine column widths
    name_w = max((len(n) for n, _ in items), default=4)
    qty_w = max((len(str(q)) for _, q in items), default=1)

    print('\nSuggested meal:')
    print(f"{'Qty':>{qty_w}}  {'Item':<{name_w}}  {'Serving':<12}  {'kcal':>6}  {'Protein(g)':>11}  {'Fat(g)':>8}  {'Carbs(g)':>9}  {'Fiber(g)':>9}")
    print('-' * (qty_w + name_w + 60))
    for name, servings in items:
        info = foods.get(name, {})
        serving_desc = info.get('serving') or '1 serving'
        c = info.get('calories', 0.0) * servings
        p = info.get('protein', 0.0) * servings
        fat = info.get('fat', 0.0) * servings
        carbs = info.get('carbs', 0.0) * servings
        fiber = info.get('fiber', 0.0) * servings
        print(f"{servings:>{qty_w}}  {name:<{name_w}}  {serving_desc:<12}  {c:6.0f}  {p:11.1f}  {fat:8.1f}  {carbs:9.1f}  {fiber:9.1f}")

    total_cal = meal.get('total_calories', 0.0)
    total_pro = meal.get('total_protein', 0.0)
    total_fat = meal.get('total_fat', 0.0)
    total_carbs = meal.get('total_carbs', 0.0)
    total_fiber = meal.get('total_fiber', 0.0)
    total_fat = meal.get('total_fat', 0.0)

    print('\nTotals:')
    print(f"  Calories: {total_cal:.0f} kcal   Protein: {total_pro:.1f} g   Fat: {total_fat:.1f} g   Carbs: {total_carbs:.1f} g   Fiber: {total_fiber:.1f} g")
    if calorie_goal:
        print('  Calorie progress: ' + _progress_bar(total_cal, calorie_goal))
    if protein_goal:
        print('  Protein progress: ' + _progress_bar(total_pro, protein_goal))
    if fat_goal:
        print('  Fat progress: ' + _progress_bar(total_fat, fat_goal))
    if carbs_goal:
        print('  Carbs progress: ' + _progress_bar(total_carbs, carbs_goal))
    if fiber_goal:
        print('  Fiber progress: ' + _progress_bar(total_fiber, fiber_goal))



def list_available_items(foods: Dict[str, Dict[str, Any]], vegan: bool = False, allergen: Optional[str] = None) -> List[str]:
    """Return a sorted list of available food item names after applying vegan/allergen filters."""
    candidates = _filter_candidates(foods, vegan, allergen)
    names = sorted([name for name, _ in candidates])
    for idx, n in enumerate(names, 1):
        info = foods.get(n, {})
        print(f"{idx}. {n} — {info.get('calories',0):.0f} kcal, {info.get('protein',0):.1f} g protein, serving: {info.get('serving')}")
    return names


def suggest_from_shortlist(foods: Dict[str, Dict[str, Any]], shortlist: List[str], calorie_goal: float, protein_goal: float,
                           excluded_meats: Optional[List[str]] = None,
                           tolerance: float = 0.07, max_items: int = 3, max_servings: int = 3) -> Optional[Dict[str, Any]]:
    """Similar to suggest_meal but restricts candidate set to the provided shortlist of names."""
    subfoods = {n: foods[n] for n in shortlist if n in foods}
    return suggest_meal(subfoods, calorie_goal, protein_goal, vegan=False, allergen=None,
                        excluded_meats=excluded_meats,
                        tolerance=tolerance, max_items=max_items, max_servings=max_servings, top_k=len(subfoods))


def _safe_float_input(prompt: str, default: Optional[float] = None) -> float:
    """Prompt for a float; accept Enter to use default if provided."""
    while True:
        try:
            v = input(prompt).strip()
            if v == '' and default is not None:
                return float(default)
            return float(v)
        except Exception:
            if v == '' and default is not None:
                return float(default)
            print('Please enter a number (e.g., 2000 or 50).')


def main():
    import os
    print('Meal suggestion assistant')
    # Offer the user a choice of dining court datasets to keep the interface common
    print('\nSelect dining court dataset:')
    print('  1) Windsor (Windsor-20250922.xlsx)')
    print('  2) Hillenbrand (Hillenbrand-Lunch20250922.xlsx)')
    print("  3) Custom path")
    choice = input('Choose 1/2/3 (press Enter for 1): ').strip() or '1'
    if choice == '2':
        path = 'Hillenbrand-Lunch20250922.xlsx'
    elif choice == '3':
        path = input('Path to Excel dataset: ').strip()
    else:
        path = 'Windsor-20250922.xlsx'
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

    # If demographics helper is available, offer to compute recommended daily macros
    per_meal_defaults = {}
    if calculate_nutrition_needs is not None:
        use_demo = input('\nWould you like to enter your demographics to get recommended daily macros? (y/n): ').strip().lower() in ('y', 'yes')
        if use_demo:
            try:
                age = int(input('Age (years): ').strip())
                weight = float(input('Weight (kg): ').strip())
                height = float(input('Height (cm): ').strip())
                gender = input("Gender ('male' or 'female'): ").strip().lower()
                activity = input("Activity level (sedentary, lightly_active, moderately_active, very_active, extremely_active): ").strip()
                demo = calculate_nutrition_needs(age, weight, height, gender, activity)
                daily_cal = demo.get('calories', 0)
                daily_pro = demo.get('protein_g', 0)
                daily_carbs = demo.get('carbohydrates_g', 0)
                daily_fat = demo.get('fat_g', 0)
                daily_fiber = demo.get('fiber_g', 0)
                per_meal_defaults = {
                    'calories': round(daily_cal / 3),
                    'protein': round(daily_pro / 3, 1),
                    'carbs': round(daily_carbs / 3, 1),
                    'fat': round(daily_fat / 3, 1),
                    'fiber': round(daily_fiber / 3, 1),
                    'daily_cal': daily_cal,
                    'daily_pro': daily_pro,
                }
                print(f"\nRecommended target for this meal (assuming 3 meals/day): {per_meal_defaults['calories']} kcal & {per_meal_defaults['protein']} g protein (daily estimate: {daily_cal} kcal, {daily_pro} g).\n")
                print(f"Daily requirement: {daily_cal} kcal & {daily_pro} g protein.")
            except Exception as e:
                print('Failed to compute demographics-based recommendations:', e)

    cal_goal = _safe_float_input('Enter calorie goal (kcal) [press Enter to use recommended]: ', default=per_meal_defaults.get('calories'))
    pro_goal = _safe_float_input('Enter protein goal (g) [press Enter to use recommended]: ', default=per_meal_defaults.get('protein'))
    veg = input('Are you vegan? (y/n): ').strip().lower() in ('y', 'yes')
    allergen = input('Allergen to avoid (leave blank if none): ').strip()

    # meat exclusion: allow user to exclude common meats (beef, chicken, pork, ham)
    print('\nDo you want to exclude any meats? You can enter multiple separated by comma (options: beef, chicken, pork, ham).')
    meats_in = input('Enter meat(s) to exclude (or press Enter for none): ').strip()
    excluded_meats = [m.strip().lower() for m in meats_in.split(',') if m.strip()] if meats_in else []

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
        meal = suggest_from_shortlist(foods, chosen_shortlist, cal_goal, pro_goal, excluded_meats=excluded_meats)
    else:
        # pass per-meal carb/fat/fiber defaults into suggestion if available
        meal = suggest_meal(foods, cal_goal, pro_goal, vegan=veg, allergen=allergen or None, excluded_meats=excluded_meats)

    if not meal:
        print('\nNo matching meal found.')
        return

    # Present alternatives if available
    alts = meal.get('alternatives', []) if isinstance(meal, dict) else []
    # display macro goals (use per-meal defaults if available)
    carbs_goal = per_meal_defaults.get('carbs', 0)
    fat_goal = per_meal_defaults.get('fat', 0)
    fiber_goal = per_meal_defaults.get('fiber', 0)
    pretty_print_meal(meal, foods, calorie_goal=cal_goal, protein_goal=pro_goal, carbs_goal=carbs_goal, fat_goal=fat_goal, fiber_goal=fiber_goal)
    if alts:
        print('\nOther close options:')
        for i, a in enumerate(alts, 1):
            print(f'\nOption {i}:')
            pretty_print_meal(a, foods, calorie_goal=cal_goal, protein_goal=pro_goal)
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
