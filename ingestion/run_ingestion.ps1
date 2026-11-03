# Rebuilds data/generated/ from the source files in data/.
#PSScript is the folder where the script is located

uv run --project $PSScriptRoot "$PSScriptRoot\ingest.py"
exit $LASTEXITCODE
