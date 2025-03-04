#!/bin/bash

# run.py에 전달할 인수 확인 (기본값 설정 가능)
if [ $# -lt 2 ]; then
    echo "Usage: $0 <items> <environment>"
    echo "Example: $0 'wooden_pickaxe wooden_sword' 'grass'"
    exit 1
fi

# 인수 받기
ITEMS="$1"  # 첫 번째 인수: items (공백으로 구분된 문자열)
ENVIRONMENT="$2"  # 두 번째 인수: environment (공백으로 구분된 문자열)

# tmux 세션 시작
tmux new-session -d -s adam_session

# 첫 번째 창: 마인크래프트 서버 (인수 필요 없음)
tmux send-keys -t adam_session:0 "cd /workspace/ADAM/mine_server && sh run_server.sh" C-m

# 두 번째 창: run.py (인수 전달)
tmux new-window -t adam_session:1
tmux send-keys -t adam_session:1 "cd /workspace/ADAM && python run.py --items $ITEMS --environment $ENVIRONMENT" C-m

# 세 번째 창: visual_API.py (인수 필요 없음, 필요 시 추가 가능)
tmux new-window -t adam_session:2
tmux send-keys -t adam_session:2 "cd /workspace/ADAM/Adam && python visual_API.py" C-m

# tmux 세션에 붙기 (선택 사항, 주석 해제 시 즉시 세션 표시)
# tmux attach-session -t adam_session
