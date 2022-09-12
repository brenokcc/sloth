docker run --rm --name sloth -it -p 8000:8000 -v $(pwd):/app -w /app -d sloth-test
alias python='docker exec sloth python'
