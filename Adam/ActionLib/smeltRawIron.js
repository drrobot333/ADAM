async function smeltRawIron(bot) {
    const rawIronCount = bot.inventory.count(mcData.itemsByName.raw_iron.id);

    if (rawIronCount < 3) {
        bot.chat("No enough raw iron. Smelting failed");
        return;
    }

    const furnaceCount = bot.inventory.count(mcData.itemsByName.furnace.id);

    if (furnaceCount < 1) {
        bot.chat("No furnace. Smelting failed");
        return;
    }

    const logTypes = ["oak_log", "birch_log", "spruce_log", "jungle_log", "acacia_log", "dark_oak_log", "mangrove_log"];
    const plankTypes = logTypes.map(logType => logType.replace('_log', '_planks'));
    const position = bot.entity.position.offset(1, 0, 0);
    await placeItem(bot, "furnace", position);

    for (let plankType of plankTypes) {
        let plank = bot.inventory.findInventoryItem(mcData.itemsByName[plankType].id);
        if (plank) {
            await smeltItem(bot, "raw_iron", plankType, 3);
            bot.chat(`Smelted 3 raw iron into 3 iron ingots using ${plankType.replace('_', ' ')}.`);
        }
    }
}