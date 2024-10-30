from Adam.ADAM import ADAM

with open("API_key.txt", 'r') as key_file:
    openai_api_key = key_file.read()

ADAM = ADAM(
    mc_port=52832,
    llm_model_type='gpt-4-turbo',
    use_local_llm_service=False,
    openai_api_key=openai_api_key,
    auto_load_ckpt=True,
    parallel=True
)

ADAM.explore(['iron_ingot'], ['grass'])
