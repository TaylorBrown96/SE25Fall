import menu_generation as menu_generation

generator = menu_generation.MenuGenerator()
menu = generator.generate_weekly_menu(preferences = "high protein, low carb", allergens = "peanuts, shellfish")
print(menu)