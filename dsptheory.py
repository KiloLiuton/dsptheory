#!/home/kevin/.asdf/shims/python
import argparse
import os

from dspcli import Item, cache_item, get_item_cache


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


def num_factories(
    item: Item, target_speed: float, depth: int, cache: str, r: int = 0
) -> list:
    cache_item(item, cache)
    speed = base_speed(item)
    if speed is None:
        speed = -1.0
    num = target_speed / speed
    result = [{"name": item.name, "num": num, "depth": depth}]

    print(
        f"{num:.2f} {item.name} factories: {num * speed:.2f}/s and require:", flush=True
    )

    if (depth == 0) or is_basic(item):
        return result

    for i in item.recipes[r].input:
        ingredient = get_item_cache(i[0].__root__, cache)
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

    item = get_item_cache(args.item, index_file)

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
