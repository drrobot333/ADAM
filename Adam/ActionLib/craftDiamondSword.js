async function craftDiamondSword(bot) {
    const position = bot.entity.position.offset(1, 0, 0);
    await placeItem(bot, "crafting_table", position);
    await craftItem(bot, "diamond_sword", 1);
    bot.chat("Crafted a diamond sword.");
}
