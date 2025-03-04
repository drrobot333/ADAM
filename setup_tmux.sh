#!/bin/bash

# tmux session start
tmux new-session -d -s adam_session

# first: 마인크래프트 서버
tmux send-keys -t adam_session:0 "cd /workspace/ADAM/mine_server && sh run_server.sh" C-m

# second: run.py
tmux new-window -t adam_session:1
tmux send-keys -t adam_session:1 "cd /workspace/ADAM && python run.py" C-m

# third: visual_API.py
tmux new-window -t adam_session:2
tmux send-keys -t adam_session:2 "cd /workspace/ADAM/Adam && python visual_API.py" C-m

