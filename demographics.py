def calculate_nutrition_needs(age, weight_kg, height_cm, gender, activity_level):
    """
    Calculate daily calorie and macronutrient needs based on personal characteristics.
    
    Parameters:
    - age: Age in years
    - weight_kg: Weight in kilograms
    - height_cm: Height in centimeters
    - gender: 'male' or 'female'
    - activity_level: 'sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extremely_active'
    
    Returns:
    - Dictionary with daily nutritional needs
    """
    
    # Calculate BMR using Mifflin-St Jeor Equation
    if gender.lower() == 'male':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    elif gender.lower() == 'female':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:
        raise ValueError("Gender must be 'male' or 'female'")
    
    # Activity level multipliers
    activity_multipliers = {
        'sedentary': 1.2,           # Little to no exercise
        'lightly_active': 1.375,    # Light exercise 1-3 days/week
        'moderately_active': 1.55,  # Moderate exercise 3-5 days/week
        'very_active': 1.725,       # Hard exercise 6-7 days/week
        'extremely_active': 1.9     # Very hard exercise, physical job
    }
    
    if activity_level not in activity_multipliers:
        raise ValueError(f"Activity level must be one of: {list(activity_multipliers.keys())}")
    
    # Calculate Total Daily Energy Expenditure (TDEE)
    calories = bmr * activity_multipliers[activity_level]
    
    # Calculate macronutrients based on standard recommendations
    # Protein: 0.8-1.2g per kg body weight (using 1.0g for balance)
    protein_g = weight_kg * 1.0
    
    # Carbohydrates: 45-65% of total calories (using 50%)
    carbs_calories = calories * 0.50
    carbs_g = carbs_calories / 4  # 4 calories per gram
    
    # Fat: 20-35% of total calories (using 25%)
    fat_calories = calories * 0.25
    fat_g = fat_calories / 9  # 9 calories per gram
    
    # Fiber: 14g per 1000 calories
    fiber_g = (calories / 1000) * 14
    
    # Round values for practical use
    return {
        'calories': round(calories),
        'protein_g': round(protein_g, 1),
        'carbohydrates_g': round(carbs_g, 1),
        'fat_g': round(fat_g, 1),
        'fiber_g': round(fiber_g, 1),
        'bmr': round(bmr),
        'activity_multiplier': activity_multipliers[activity_level]
    }

# Example usage and test function
def print_nutrition_plan(age, weight_kg, height_cm, gender, activity_level):
    """Print a formatted nutrition plan."""
    try:
        results = calculate_nutrition_needs(age, weight_kg, height_cm, gender, activity_level)
        
        print(f"\n--- Daily Nutrition Plan ---")
        print(f"Profile: {age}yr old {gender}, {weight_kg}kg, {height_cm}cm, {activity_level}")
        print(f"BMR: {results['bmr']} calories")
        print(f"Activity Multiplier: {results['activity_multiplier']}")
        print(f"\nDaily Targets:")
        print(f"  Calories: {results['calories']}")
        print(f"  Protein: {results['protein_g']}g")
        print(f"  Carbohydrates: {results['carbohydrates_g']}g") 
        print(f"  Fat: {results['fat_g']}g")
        print(f"  Fiber: {results['fiber_g']}g")
        
        return results
    except ValueError as e:
        print(f"Error: {e}")
        return None

# Example calculations
if __name__ == "__main__":
    # Test with different profiles
    
    # Example 1: 30-year-old moderately active male
    print("Example 1:")
    print_nutrition_plan(30, 75, 180, 'male', 'moderately_active')
    
    # Example 2: 25-year-old lightly active female  
    print("\nExample 2:")
    print_nutrition_plan(25, 60, 165, 'female', 'lightly_active')
    
    # Example 3: Direct function call
    print("\nDirect function call:")
    results = calculate_nutrition_needs(40, 80, 175, 'male', 'very_active')
    print(results)