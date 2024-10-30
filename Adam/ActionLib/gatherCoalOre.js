async function mineCoalOre(bot) {
    bot.chat('Gathering coal ore started');
    const woodenPickaxeCount = bot.inventory.count(mcData.itemsByName.wooden_pickaxe.id);

    if (woodenPickaxeCount < 1) {
        bot.chat("No wooden_pickaxe. Mining coal ore failed");
        return;
    }
    // Find an coal ore block
    const coalOreBlock = await exploreUntil(bot, new Vec3(0, -1, 0), 60, () => {
        const coalOre = bot.findBlock({
            matching: mcData.blocksByName["coal_ore"].id,
            maxDistance: 32
        });
        return coalOre;
    });
    if (!coalOreBlock) {
        bot.chat("No coal ore found.");
        return;
    }
    // Mine the coal ore block
    await mineBlock(bot, "coal_ore", 5);
    bot.chat("Mined 5 coal ore.");
}