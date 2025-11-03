import menu_generation as menu_generation
from io import StringIO

import pandas as pd


generator = menu_generation.MenuGenerator()
menu = generator.update_menu(menu = None, preferences = "high protein,low carb", allergens = "Peanuts,Shellfish", date = "2025-10-14", meal_number = 2)
print(menu)
menu = generator.update_menu(menu = menu, preferences = "high protein,low carb", allergens = "Peanuts,Shellfish", date = "2025-10-14", meal_number = 3)
print(menu)
menu = generator.update_menu(menu = menu, preferences = "high protein,low carb", allergens = "Peanuts,Shellfish", date = "2025-10-15", meal_number = 1)
print(menu)
menu = generator.update_menu(menu = menu, preferences = "high protein,low carb", allergens = "Peanuts,Shellfish", date = "2025-10-15", meal_number = 2)
print(menu)
menu = generator.update_menu(menu = menu, preferences = "high protein,low carb", allergens = "Peanuts,Shellfish", date = "2025-10-15", meal_number = 3)
print(menu)