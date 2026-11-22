from .models import db, Recipe
from .schemas import RecipeInput, Personal


def seed(remove=False):
    demos = [r for r in db.session.scalars(db.select(Recipe)) if r.content.get("demo")]
    if remove:
        for r in demos:
            db.session.delete(r)
        db.session.commit()
        return f"Removed {len(demos)} demo recipes"
    if demos:
        return "Demo recipes are already loaded"
    specs = [
        (
            "Creamy lemon chicken pasta",
            "Bright lemon, tender chicken and a silky sauce. A comforting weeknight favourite.",
            "Italian",
            "Dinner",
            10,
            20,
            ["Chicken", "Pasta"],
            [
                ("chicken breast", 300, "g"),
                ("pasta", 200, "g"),
                ("cream", 150, "ml"),
                ("lemon", 1, ""),
                ("garlic", 2, "cloves"),
            ],
            [
                "Bring a saucepan of salted water to the boil. Cook the pasta following the packet instructions, reserving a mug of cooking water.",
                "Dice the chicken. Heat a little oil in a frying pan and fry until browned and cooked through, with no pink remaining.",
                "Add crushed garlic, cream and lemon zest. Simmer gently for 3 minutes.",
                "Toss in the drained pasta. Loosen with a splash of cooking water, add lemon juice to taste and serve.",
            ],
            ["Hob", "Frying pan", "Saucepan/pot"],
        ),
        (
            "Smoky chickpea & spinach stew",
            "A rich tomato stew with warming paprika. Simple pantry ingredients, plenty of flavour.",
            "Spanish",
            "Dinner",
            10,
            25,
            ["Vegetarian", "One pot"],
            [
                ("chickpeas", 400, "g"),
                ("chopped tomatoes", 400, "g"),
                ("spinach", 150, "g"),
                ("onion", 1, ""),
                ("smoked paprika", 2, "tsp"),
            ],
            [
                "Dice the onion and soften in a saucepan with a little oil.",
                "Stir in paprika, drained chickpeas and tomatoes. Simmer for 20 minutes, stirring occasionally.",
                "Fold in the spinach until wilted. Season to taste and serve with bread if you like.",
            ],
            ["Hob", "Saucepan/pot"],
        ),
        (
            "Ginger sesame noodle bowls",
            "Fresh, crunchy vegetables and glossy sesame noodles for a quick lunch.",
            "Asian-inspired",
            "Lunch",
            15,
            10,
            ["Vegetarian", "Quick"],
            [
                ("noodles", 180, "g"),
                ("carrot", 1, ""),
                ("pepper", 1, ""),
                ("soy sauce", 2, "tbsp"),
                ("sesame oil", 1, "tbsp"),
                ("fresh ginger", 15, "g"),
            ],
            [
                "Cook the noodles according to the packet, then drain.",
                "Slice the vegetables thinly and grate the ginger.",
                "Stir-fry the vegetables in sesame oil for 4 minutes. Add ginger and soy sauce.",
                "Add the noodles and toss together until hot.",
            ],
            ["Hob", "Frying pan", "Saucepan/pot"],
        ),
        (
            "Golden oven-roasted vegetables",
            "Crisp-edged seasonal vegetables with rosemary and a lemon finish.",
            "Mediterranean",
            "Side",
            10,
            35,
            ["Vegan", "Vegetables"],
            [
                ("potatoes", 350, "g"),
                ("courgette", 1, ""),
                ("carrot", 2, ""),
                ("olive oil", 2, "tbsp"),
                ("rosemary", None, "to taste"),
            ],
            [
                "Heat the oven to 200°C. Cut the vegetables into even pieces.",
                "Toss with oil and rosemary on a large baking tray. Spread into one layer.",
                "Roast for 35 minutes, turning halfway, until tender and golden.",
            ],
            ["Oven"],
        ),
        (
            "Fluffy weekend pancakes",
            "A small stack of soft pancakes, ready for your favourite toppings.",
            "American",
            "Breakfast",
            10,
            15,
            ["Vegetarian", "Breakfast"],
            [
                ("plain flour", 150, "g"),
                ("milk", 180, "ml"),
                ("egg", 1, ""),
                ("baking powder", 1, "tsp"),
                ("butter", 20, "g"),
            ],
            [
                "Whisk flour and baking powder together. Beat the egg with milk and add to the flour.",
                "Melt the butter and stir into the batter. Rest for 5 minutes.",
                "Heat a non-stick frying pan over medium heat. Cook small rounds of batter until bubbles form, flip and cook until golden.",
            ],
            ["Hob", "Frying pan"],
        ),
        (
            "Air fryer paprika salmon",
            "Tender salmon with smoky seasoning and a crisp finish.",
            "British",
            "Dinner",
            5,
            12,
            ["Fish", "Quick"],
            [
                ("salmon fillet", 2, ""),
                ("olive oil", 1, "tsp"),
                ("paprika", 1, "tsp"),
                ("lemon", 0.5, ""),
            ],
            [
                "Pat the salmon dry and rub with oil and paprika.",
                "Place in the air fryer basket with space between fillets. Cook at 190°C for 10–12 minutes, until the fish is opaque and flakes easily. Adjust for fillet thickness.",
                "Squeeze over the lemon and serve.",
            ],
            ["Air fryer"],
        ),
    ]
    for (
        title,
        description,
        cuisine,
        category,
        prep,
        cook,
        tags,
        ingredients,
        steps,
        equipment,
    ) in specs:
        content = RecipeInput(
            title=title,
            description=description,
            cuisine=cuisine,
            category=category,
            prep_time=prep,
            cook_time=cook,
            tags=tags,
            ingredients=[dict(name=n, quantity=q, unit=u) for n, q, u in ingredients],
            instructions=[dict(text=s) for s in steps],
            equipment=equipment,
            demo=True,
        ).model_dump()
        db.session.add(Recipe(content=content, personal=Personal().model_dump()))
    db.session.commit()
    return f"Loaded {len(specs)} demo recipes"
