async function gatherWoodLog(bot) {
  bot.chat('Gathering wood logs started');

  // Find a wood log block
  const woodLogBlock = await exploreUntil(bot, new Vec3(1, 0, 1), 120, () => {
    const woodLog = bot.findBlock({
      matching: block => ["oak_log", "birch_log", "spruce_log", "jungle_log", "acacia_log", "dark_oak_log", "mangrove_log"].includes(block.name),
      maxDistance: 32
    });
    return woodLog;
  });

  if (!woodLogBlock) {
    bot.chat("No wood log found.");
    return;
  }
  // Mine the wood log block
  await mineBlock(bot, woodLogBlock.name, 12);
  bot.chat("Gathered 12 wood logs.");
}