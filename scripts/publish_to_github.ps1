param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryUrl
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".git")) {
    throw "Run this script from the repository root."
}

$branch = (git branch --show-current).Trim()
if ($branch -ne "main") {
    throw "Expected branch 'main', found '$branch'."
}

$remotes = @(git remote)
if ($remotes -contains "origin") {
    git remote set-url origin $RepositoryUrl
} else {
    git remote add origin $RepositoryUrl
}

git push -u origin main
Write-Host "Published to $RepositoryUrl" -ForegroundColor Green
