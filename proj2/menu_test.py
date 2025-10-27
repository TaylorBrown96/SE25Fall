import menu_generation as menu_generation

generator = menu_generation.MenuGenerator()
menu = generator.pick_menu_item(preferences = "high protein,low carb", allergens = "Peanuts,Shellfish", date = "2025-10-14", meal_number = 2)
print(menu)