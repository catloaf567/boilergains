# boiler-gains


## Inspiration

We noticed the lack of nutritional guidance on a daily basis for an average boilermaker who has a meal plan. Yes, the Purdue Menus provides detailed nutritional values for every food item, but what if you do not have the time to check all the values, 


## What it does




## How we built it




## Challenges we ran into



## Accomplishments that we're proud of




## What we learned





## What's next for Protein-Cult

Can add allergen specific to make it accessible for students with allergies
Have alternatives next for each dining court
save room for dessert? - saves calories
make it more nuanced with vegetarian options, dairy free, etc
Incorporating more niche sections such as salad bars, make your own pizza, sizzling pasta opions
Add individual meal  - divde by 2 if only 2 daily meals, divide by 3 if 3 meals
add meal time selection
add web scraping


## Built With

This small utility suggests meal combinations to meet calorie and protein goals using a provided Excel dataset.

How to run
1. Create a Python environment and install dependencies:

	pip install -r requirements.txt

2. Run the script and follow prompts:

	python protein.py

Notes
- The script expects an Excel file (default: `Windsor-20250922.xlsx`) containing food items and nutritional columns. Column names are flexibly detected (e.g., 'Protein', 'protein (g)', 'kcal', 'Calories').
- You can filter for vegan items and specify an allergen string to exclude rows containing that substring in the allergens column.

Pairing rules and customization
 - The suggestion logic uses a pairing map to prefer natural combinations (for example, burger + bun, yogurt + granola).
 - The repository includes `pairings.json` which contains the pairing rules. Edit that file to add or change pairings without changing code.
 - If you want to use a different pairing file, the script will prompt for a pairing file path when it runs; press Enter to use the default `pairings.json`.
