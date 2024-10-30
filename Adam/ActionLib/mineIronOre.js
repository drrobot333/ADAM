async function mineIronOre(bot) {
    bot.chat('Gathering iron ore started');
    const stonePickaxeCount = bot.inventory.count(mcData.itemsByName.stone_pickaxe.id);

    if (stonePickaxeCount < 1) {
        bot.chat("No stone_pickaxe. Mining iron ore failed");
        return;
    }
    // Find an iron ore block
    const ironOreBlock = await exploreUntil(bot, new Vec3(0, -1, 0), 120, () => {
        const ironOre = bot.findBlock({
            matching: mcData.blocksByName["iron_ore"].id,
            maxDistance: 32
        });
        return ironOre;
    });
    if (!ironOreBlock) {
        bot.chat("No iron ore found.");
        return;
    }
    // Mine the iron ore block
    await mineBlock(bot, "iron_ore", 3);
    bot.chat("Mined 3 iron ore.");
}