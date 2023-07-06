#!/bin/bash
curl -X POST http://127.0.0.1:50505/ask -H "Content-Type: application/x-www-form-urlencoded" \
	-d "token=$SLACK_TOKEN_ID&response_url=http://127.0.0.1:50505/dump&team_domain=qa&user_name=test&command=/askplivo&text=How+to+send+an+SMS"
