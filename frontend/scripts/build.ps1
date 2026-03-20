param(
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

Write-Host "Building TwitchClipper desktop frontend ($Configuration)..."
dotnet build "../TwitchClipper.Frontend.sln" -c $Configuration
