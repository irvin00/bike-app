set bikeHome to do shell script "launchctl getenv BIKE_VIEW_HOME"
set uvBin to do shell script "launchctl getenv UV_BIN"
do shell script "pkill -f 'uvicorn app.main' 2>/dev/null; sleep 0.3"
do shell script "cd '" & bikeHome & "' && nohup " & uvBin & " run uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/bikeview.log 2>&1 &"
display notification "Bike View is starting up..." with title "Bike View"

-- Wait for the server to be ready (timeout after 15 seconds)
set attempts to 0
repeat
	try
		do shell script "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/"
		exit repeat
	on error
		set attempts to attempts + 1
		if attempts > 30 then exit repeat
		delay 0.5
	end try
end repeat

do shell script "open http://127.0.0.1:8000"
