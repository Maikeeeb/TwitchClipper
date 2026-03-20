# Frontend First Run Checklist

1. Start API: `uvicorn api.main:app --reload`
2. Build frontend: `dotnet build frontend/TwitchClipper.Frontend.sln`
3. Run desktop app: `dotnet run --project frontend/TwitchClipper.Desktop/TwitchClipper.Desktop.csproj`
4. Verify startup health banner is clear (`GET /health` reachable)
5. Submit one `vod_highlights` and one `clip_montage` job
6. Open queue and detail screens; verify `run-next` appears only when developer mode is true
