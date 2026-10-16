# start-dev-servers.ps1
# Launches Firestore emulator, Cloud Storage emulator, and the Streamlit app
# each in their own window, for local development.

$projectRoot = "C:\Users\james\PycharmProjects\PythonProject\Startup_Kit"
$gcsServerPath = "C:\Users\james\Downloads\fake-gcs-server"

Write-Host "Starting Firestore emulator..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; firebase emulators:start --only firestore"

Write-Host "Starting Cloud Storage emulator..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$gcsServerPath'; .\fake-gcs-server.exe -scheme http -port 4443"

Write-Host "Starting Streamlit app..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; streamlit run src/review_ui/app.py"

Write-Host "All three dev servers launching in separate windows."