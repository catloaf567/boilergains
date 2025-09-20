# The-Protein-Cult


## Inspiration



## What it does




## How we built it




## Challenges we ran into



## Accomplishments that we're proud of




## What we learned





## What's next for Protein-Cult





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