#!/home/kevin/.asdf/shims/python
import argparse
import json
import os

import dspcli
from dspcli import Item, ItemId, Recipe


def get_item(name: str, cache: str) -> Item:
    index = {}
    if os.path.isfile(cache):
        with open(cache, "r") as f:
            index.update(json.load(f))

    if name in index:
        item = deserialize_item(index[name])
    else:
        item = dspcli.get_item(name)
        cache_item(item, cache)
    return item


def cache_item(item: Item, cachefile: str) -> None:
    recipes = [
        {
            "input": [(x[0].__root__, x[1]) for x in r.input],
            "output": [(x[0].__root__, x[1]) for x in r.output],
            "duration": r.duration,
        }
        for r in item.recipes
    ]
    item_data = {
        item.name: {
            "name": item.name,
            "category": item.category,
            "description": item.description,
            "recipes": recipes,
        }
    }

    if os.path.isfile(cachefile):
        with open(cachefile, "r") as f:
            data = json.load(f)
            data.update(item_data)
        with open(cachefile, "w") as f:
            json.dump(data, f, indent=2)
    else:
        with open(cachefile, "w") as f:
            json.dump(item_data, f, indent=2)


def cache_all(cache_file: str):
    items = dspcli.list_items()
    for id in items.components + items.buildings:
        name = id.__root__
        print("Caching ", name)
        try:
            item = dspcli.get_item(name)
            cache_item(item, cache_file)
        except:
            continue


def deserialize_recipe(r: dict) -> Recipe:
    return Recipe(
        input=[(ItemId.parse_obj(x[0]), x[1]) for x in r["input"]],
        output=[(ItemId.parse_obj(x[0]), x[1]) for x in r["output"]],
        duration=r["duration"],
    )


def deserialize_item(item: dict) -> Item:
    return Item(
        name=item["name"],
        category=item["category"],
        description=item["description"],
        recipes=[deserialize_recipe(r) for r in item["recipes"]],
    )


def find_ingredient(item: Item, item_name: str) -> tuple[ItemId, int | None] | None:
    for x in item.recipes[0].input:
        if ItemId.parse_obj(item_name) in x:
            return x


def is_basic(item: Item) -> bool:
    if item.category is None:
        raise ValueError(f"Item {item.name} has 'None' category!")

    if "Natural Resource" in item.category:
        return True

    if any(["?" in recipe.duration for recipe in item.recipes]):
        return True

    return False


def base_speed(item: Item, r: int = 0) -> float | None:
    duration = item.recipes[r].duration.strip(" s")
    quantity = item.recipes[r].output[0][1]
    if (quantity is None) or ("?" in duration) or ("%" in duration):
        return
    else:
        return float(quantity) / float(duration)


def base_quantity(item: Item, r: int = 0) -> float:
    qty = item.recipes[r].output[0][1]
    if qty is not None:
        return qty
    else:
        return -1.0


def num_factories(item: Item, target_speed: float, depth: int, cache: str, r: int = 0) -> list:
    cache_item(item, cache)
    speed = base_speed(item)
    if speed is None:
        speed = -1.0
    result = [{"name": item.name, "num": target_speed / speed, "depth": depth}]

    if (depth == 0) or is_basic(item):
        return result

    for i in item.recipes[r].input:
        ingredient = get_item(i[0].__root__, cache)
        n_consumed = i[1]
        if n_consumed is None:
            n_consumed = 0.0
        consumption_speed = n_consumed * target_speed
        result = result + num_factories(ingredient, consumption_speed, depth - 1, cache)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num", type=int, default=1)
    parser.add_argument("-d", "--depth", type=int, default=1)
    parser.add_argument("item")

    args = parser.parse_args()

    home = os.getenv("HOME")
    if home is None:
        home = input("Where would you like to cache .dsptheory item data?")
    index_file = os.path.join(home, ".dsptheory", "index.json")
    if not os.path.isdir(os.path.dirname(index_file)):
        os.makedirs(os.path.dirname(index_file))

    item = get_item(args.item, index_file)

    speed = args.num * base_speed(item)
    if speed is None:
        print(args.item, "has no base speed!")
        return
    print(f"{args.num} {item.name} Factories produce {speed}/s and require:")
    requirements = num_factories(item, speed, args.depth, index_file)
    for item in requirements:
        depth = item["depth"]
        num = item["num"]
        name = item["name"]
        print(" " * (4 * args.depth - 4 * depth), f"{num:.2f}", name, "factories.")


if __name__ == "__main__":
    main()
