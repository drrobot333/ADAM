from Adam.ADAM import ADAM
import argparse

def parse_arguments():
    # ArgumentParser 객체 생성
    parser = argparse.ArgumentParser(description="Run ADAM with custom items and environment goals.")
    
    # items 인수: 여러 항목을 리스트로 받음
    parser.add_argument(
        '--items',
        nargs='+',  # 여러 개의 값을 받음
        default=['wooden_pickaxe', 'wooden_sword', 'wooden_shovel', 'wooden_axe', 'wooden_hoe'],
        help="List of items to explore (e.g., --items wooden_pickaxe wooden_sword)"
    )
    
    # environment 인수: 여러 항목을 리스트로 받음
    parser.add_argument(
        '--environment',
        nargs='+',  # 여러 개의 값을 받음
        default=['grass'],
        help="List of environment goals (e.g., --environment grass)"
    )
    
    # 인수 파싱
    args = parser.parse_args()
    return args.items, args.environment

def main():
    # 명령줄에서 items와 environment 받기
    items, environment = parse_arguments()

    # ADAM 객체 초기화
    adam = ADAM(
        mc_port=25565,
        llm_model_type='Qwen-v2.5-72B-AWQ',
        use_local_llm_service=True,
        openai_api_key="",
        auto_load_ckpt=True,
        parallel=False,
        goal=[items, environment]  # goal을 리스트로 전달
    )

    # explore 실행
    adam.explore(items, environment)

if __name__ == "__main__":
    main()
