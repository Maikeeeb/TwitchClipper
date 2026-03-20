param(
    [string]$Configuration = "Release",
    [string]$Runtime = "win-x64"
)

$ErrorActionPreference = "Stop"

$project = "../TwitchClipper.Desktop/TwitchClipper.Desktop.csproj"
$output = "../publish/$Runtime"

Write-Host "Publishing TwitchClipper desktop frontend ($Configuration, $Runtime)..."
dotnet publish $project -c $Configuration -r $Runtime --self-contained false -o $output
