# boiler*gains*
Eating well simplified for the everyday boilermaker.
https://devpost.com/software/boilergains

## Inspiration

boiler*gains* was inspired from our own struggles as college students to incorporate healthy food choices into our daily busy schedules. We noticed a lack of daily nutritional guidance for an average boilermaker with a meal plan. Yes, the Purdue Menus provides detailed nutritional values for every food item, but what if you do not have the time to toggle through 5 dining courts and every food item. Moreover, the importance of dietary choices in college is backed by many researchers. "University life is a critical period for establishing healthy eating habits and attitudes. However, university students are at risk of developing poor eating habits due to various factors, including **economic conditions, academic stress, and lack of information about nutritional concepts** ( AH, A.N.N. W.-A., 15 Feb 2024). 

So, we wanted to design an interactive website that could take nutritional info directly from the Purdue Menus website, your personal dietary preferences, and suggest meal ideas for any dining court.

## What it does

boiler*gains* first takes your personal information such as age, gender, weight, height, and goal, and shows your daily macro-nutritional recommendations (calories, carbohydrates, protein, fiber and fats). You can either choose to use the recommendations or alter them to your liking. Next, you can choose a dining court and select your dietary preferences. For example, selecting 'Yes' for Vegan only shows you vegan food choices. We also allow excluding certain animal products. Finally, it shows you suggested meal options for that dining court that meets your goal! 


## How we built it
We built a small, focused nutrition suggestion app using Python (Flask) on the backend and plain HTML/CSS/JavaScript on the frontend. The core idea: ingest dining-court Excel menus, compute per-item macronutrients, then search for small meal combinations that meet a user’s per-meal calorie and protein goals (with optional carbs/fat/fiber reporting and dietary exclusions). The app supports both a multi-page guided flow (Page1→Page5) and an interactive single-page UI


## Challenges we ran into
Firstly, we were not able to make dynamic web scraping from the Purdue Menus work, and had to fall back on manually obtained datasets of nutritional values for each of the five dining halls. Next, we have major issues merging our frontend with the backend. There were several other minor setbacks, but we were able to sail through them.


## Accomplishments that we're proud of
We are extremely proud of how boiler*gains* takes your personal information and preferences and uses scientific formulae to calculate the recommended nutritional values AND tailors it to you. We are also proud of how we have actual data from the Purdue Menus, which reflects its usefulness to students. We also love our frontend color palette and theme, and how our project has come together in the end.


## What we learned
Throughout the 24 hours we worked on boiler*gains*, we learned several things: how to use HTML, CSS, and JS to create an interactive website, how to use Python to generate the backend, and how to tie both together. 


## What's next for boiler*gains*

We plan to enhance boiler*gains* by using web scraping to build a dynamic database that updates daily with menu items, including meal period, ingredients, sodium, cholesterol, and other nutritional details. We want it to be more accessible by incorporating allergen-specific filters and offering nuanced dietary options such as vegetarian, halal, and other alternatives at each dining court. It should support niche options like make-your-own bars, salad stations, and sizzling pasta. Customization features such as selecting the number of meals per day, meal times, and saving room for dessert would make planning more flexible. Finally, a stronger combinatorial algorithm could better balance nutrition while supplementing the Purdue Dining Menus.


References:
AH;, A. N. N. W.-A. (15 Feb, 2024). Addressing nutritional issues and eating behaviours among university students: A narrative review. Nutrition research reviews. https://pubmed.ncbi.nlm.nih.gov/38356364/ 

