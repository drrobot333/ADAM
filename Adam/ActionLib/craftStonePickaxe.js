async function craftStonePickaxe(bot) {
    const position = bot.entity.position.offset(1, 0, 0);
    await placeItem(bot, "crafting_table", position);
    await craftItem(bot, "stone_pickaxe", 1);
    bot.chat("Crafted a stone pickaxe.");
}
