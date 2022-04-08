#!/usr/bin/python
from __future__ import annotations
import argparse
from functools import lru_cache
from urllib.request import urlopen

from lxml.etree import Element
from lxml.html import parse
from pydantic import BaseModel


BASE_URL = "https://dsp-wiki.com"


class ItemId(BaseModel):
    __root__: str

    def get(self) -> Item:
        return get_item(self.__root__)


class Recipe(BaseModel):
    input: list[tuple[ItemId, int | None]]
    output: list[tuple[ItemId, int | None]]
    duration: str


class Item(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None
    recipes: list[Recipe] = []


class ItemList(BaseModel):
    components: list[ItemId]
    buildings: list[ItemId]


def try_(fn, default, exc=Exception):
    try:
        return fn()
    except exc:
        return default


def get_recipe(el: Element) -> Recipe:
    return Recipe(
        input=[
            (
                ItemId.parse_obj(x.xpath("./a/@href")[0][1:]),
                try_(lambda: int(x.xpath("./div/text()")[0]), None),
            )
            for x in el.find_class("tt_recipe_item")
        ],
        output=[
            (
                ItemId.parse_obj(x.xpath("./a/@href")[0][1:]),
                int(x.xpath("./div/text()")[0]),
            )
            for x in el.find_class("tt_output_item")
        ],
        duration=el.find_class("tt_rec_arrow")[0].xpath("./div/text()")[0],
    )


def get_recipe_list(el: Element) -> list[Recipe]:
    tables = el.find_class("pc_table")
    if not tables:
        return []
    pc_table = tables[0]
    rows = pc_table.xpath("./tbody/tr[position()>1]")
    return [get_recipe(row.find_class("tt_recipe")[0]) for row in rows]


@lru_cache
def get_item(url: str) -> Item:
    if not url.startswith(BASE_URL):
        url = BASE_URL + "/" + url
    tree = parse(urlopen(url))
    root = tree.getroot()
    name = root.get_element_by_id("firstHeading").text_content().replace(" ", "_")
    panel = root.find_class("item_panel")
    if len(panel) > 0:
        panel = panel[0]
        return Item(
            name=name,
            category=panel.find_class("tt_category")[0].text_content(),
            description=panel.find_class("tt_desc")[0].text_content(),
            recipes=get_recipe_list(root),
        )
    else:
        return Item(name=name)


def list_items() -> ItemList:
    url = BASE_URL + "/Items"
    tree = parse(urlopen(url))
    root = tree.getroot()
    tables = root.xpath("//table")
    return ItemList(
        components=[ItemId.parse_obj(x[1:]) for x in tables[0].xpath(".//a/@href")],
        buildings=[ItemId.parse_obj(x[1:]) for x in tables[1].xpath(".//a/@href")],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list", action="store_true")
    parser.add_argument("item", nargs="?")
    args = parser.parse_args()
    if args.list:
        print(list_items().json())
    elif args.item is not None:
        print(get_item(args.item).json())
    else:
        parser.print_usage()


if __name__ == "__main__":
    main()
