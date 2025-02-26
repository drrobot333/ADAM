from Adam.ADAM import ADAM


ADAM = ADAM(
    mc_port=25565,
    llm_model_type='Qwen-v2.5-72B-AWQ',
    use_local_llm_service=True,
    openai_api_key="",
    auto_load_ckpt=True,
    parallel=False,
)

ADAM.explore(['wooden_pickaxe', 'wooden_sword', 'wooden_shovel', 'wooden_axe'], ['grass'])
# ADAM.explore(['diamond'], ['grass'])
