/*
Test Plan
- Partitions: back navigation, rerun-to-form routing, refresh command data hydration
- Boundaries: empty selected job id, rerun params with array/string values
- Failure modes: command-driven refresh still performs health update under queue/detail screens
# Covers: UI-IMPL-052
*/

using System.Text.Json;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;
using TwitchClipper.Desktop.ViewModels;
using TwitchClipper.Frontend.Tests.TestDoubles;

namespace TwitchClipper.Frontend.Tests;

public class AppShellCommandBehaviorTests
{
    [Fact]
    public void Back_command_routes_job_detail_to_jobs_and_other_screens_to_dashboard()
    {
        // Why: keyboard back behavior should be deterministic across screen contexts.
        var shell = BuildShell(new FakeApiClient());

        shell.NavigateTo(AppScreen.JobDetail);
        shell.BackCommand.Execute(null);
        Assert.Equal(AppScreen.Jobs, shell.CurrentScreen);

        shell.NavigateTo(AppScreen.NewVod);
        shell.BackCommand.Execute(null);
        Assert.Equal(AppScreen.Dashboard, shell.CurrentScreen);
    }

    [Fact]
    public void Rerun_vod_job_prefills_vod_form_and_navigates_to_vod_screen()
    {
        // Why: rerun should restore prior input values for fast retries.
        var shell = BuildShell(new FakeApiClient());
        shell.Detail.Job = new JobResponseDto
        {
            Type = "vod_highlights",
            Params = new Dictionary<string, JsonElement>
            {
                ["vod_url"] = JsonSerializer.SerializeToElement("https://twitch.tv/videos/1"),
                ["output_dir"] = JsonSerializer.SerializeToElement("vod_output")
            }
        };

        shell.Detail.RerunWithPrefillCommand.Execute(null);

        Assert.Equal(AppScreen.NewVod, shell.CurrentScreen);
        Assert.Equal("https://twitch.tv/videos/1", shell.VodForm.VodUrl);
        Assert.Equal("vod_output", shell.VodForm.OutputDir);
    }

    [Fact]
    public void Rerun_clip_job_prefills_clip_form_and_navigates_to_clip_screen()
    {
        // Why: clip reruns must preserve streamer and directory values.
        var shell = BuildShell(new FakeApiClient());
        shell.Detail.Job = new JobResponseDto
        {
            Type = "clip_montage",
            Params = new Dictionary<string, JsonElement>
            {
                ["streamer_names"] = JsonSerializer.SerializeToElement(new[] { "ninja", "shroud" }),
                ["current_videos_dir"] = JsonSerializer.SerializeToElement("currentVideos")
            }
        };

        shell.Detail.RerunWithPrefillCommand.Execute(null);

        Assert.Equal(AppScreen.NewClip, shell.CurrentScreen);
        Assert.Equal("ninja, shroud", shell.ClipForm.StreamerNamesText);
        Assert.Equal("currentVideos", shell.ClipForm.CurrentVideosDir);
    }

    [Fact]
    public async Task Refresh_current_screen_command_updates_queue_detail_and_health()
    {
        // Why: refresh shortcut should keep queue/detail and health indicators synchronized.
        var getHealthCalls = 0;
        var getJobCalls = 0;
        var listCalls = 0;
        var api = new FakeApiClient
        {
            HealthFactory = () =>
            {
                Interlocked.Increment(ref getHealthCalls);
                return Task.FromResult(new HealthResponseDto { Ok = true });
            },
            ListFactory = (_, _) =>
            {
                Interlocked.Increment(ref listCalls);
                return Task.FromResult<IReadOnlyList<JobResponseDto>>(
                [
                    new JobResponseDto { Id = "r1", Status = "running", CreatedAt = "2026-03-02" }
                ]);
            },
            JobFactory = id =>
            {
                Interlocked.Increment(ref getJobCalls);
                return Task.FromResult(new JobResponseDto { Id = id, Status = "running" });
            }
        };
        var shell = BuildShell(api);
        shell.NavigateTo(AppScreen.JobDetail);
        shell.SelectedJobId = "r1";

        shell.RefreshCurrentScreenCommand.Execute(null);
        await WaitUntilAsync(() => getHealthCalls > 0 && getJobCalls > 0 && listCalls > 0);

        Assert.Equal("API reachable", shell.Dashboard.HealthSummary);
        Assert.Equal("Worker running", shell.Dashboard.WorkerSummary);
        Assert.Equal("r1", shell.Detail.Job?.Id);
    }

    private static AppShellViewModel BuildShell(FakeApiClient fakeApi)
    {
        var settings = new AppSettings { DeveloperMode = true };
        var dialog = new TestDialogService();
        var nav = new NavigationService();
        var dashboard = new DashboardViewModel();
        var vod = new VodHighlightsFormViewModel(fakeApi, dialog);
        var clip = new ClipMontageFormViewModel(fakeApi, dialog);
        var queue = new JobsQueueViewModel(fakeApi, settings);
        var detail = new JobDetailViewModel(fakeApi, new PathOpener());

        return new AppShellViewModel(nav, fakeApi, settings, dashboard, vod, clip, queue, detail);
    }

    private static async Task WaitUntilAsync(Func<bool> predicate)
    {
        for (var i = 0; i < 200; i++)
        {
            if (predicate())
            {
                return;
            }

            await Task.Yield();
        }

        throw new TimeoutException("Timed out waiting for async command completion.");
    }
}
