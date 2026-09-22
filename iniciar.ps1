$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$avscopeEnvironment = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $avscopeEnvironment)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv .venv
    } else {
        & python -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Instale Python 3.12 e tente novamente.' }
}
& $avscopeEnvironment -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel instalar as dependencias.' }
& $avscopeEnvironment -m streamlit run app.py --server.address=127.0.0.1
