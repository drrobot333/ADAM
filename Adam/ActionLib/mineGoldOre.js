async function mineGoldOre(bot) {
    bot.chat('Gathering gold ore started');
    const ironPickaxeCount = bot.inventory.count(mcData.itemsByName.iron_pickaxe.id);

    if (ironPickaxeCount < 1) {
        bot.chat("No iron_pickaxe. Mining gold ore failed");
        return;
    }
    // Find an gold ore block
    const goldOreBlock = await exploreUntil(bot, new Vec3(0, -1, 0), 60, () => {
        const goldOre = bot.findBlock({
            matching: mcData.blocksByName["deepslate_gold_ore"].id,
            maxDistance: 32
        });
        return goldOre;
    });
    if (!goldOreBlock) {
        bot.chat("No gold ore found.");
        return;
    }
    // Mine the gold ore block
    await mineBlock(bot, "deepslate_gold_ore", 1);
    bot.chat("Mined 1 gold ore.");
}