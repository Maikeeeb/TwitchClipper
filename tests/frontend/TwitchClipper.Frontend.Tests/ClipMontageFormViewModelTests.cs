/*
Test Plan
- Partitions: streamer parsing, valid submit, cancel behavior
- Boundaries: blank streamer names, nullable numeric tuning values
- Failure modes: dirty cancel rejection
# Covers: UI-IMPL-044
*/

using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.ViewModels;
using TwitchClipper.Frontend.Tests.TestDoubles;
using System.Net.Http;

namespace TwitchClipper.Frontend.Tests;

public class ClipMontageFormViewModelTests
{
    [Fact]
    public void ParseStreamerNames_trims_and_dedupes_values()
    {
        // Why: UI must normalize streamer inputs before submit.
        var vm = new ClipMontageFormViewModel(new FakeApiClient(), new TestDialogService())
        {
            StreamerNamesText = " ninja,  shroud\nNinja "
        };

        var names = vm.ParseStreamerNames();

        Assert.Equal(2, names.Count);
        Assert.Contains("ninja", names, StringComparer.OrdinalIgnoreCase);
        Assert.Contains("shroud", names, StringComparer.OrdinalIgnoreCase);
    }

    [Fact]
    public void Validate_empty_streamer_names_sets_error()
    {
        // Why: required list input must block submit command.
        var vm = new ClipMontageFormViewModel(new FakeApiClient(), new TestDialogService())
        {
            StreamerNamesText = "   ",
            CurrentVideosDir = "videos"
        };

        vm.Validate();

        Assert.True(vm.HasValidationErrors);
    }

    [Fact]
    public void HandleCancelRequest_returns_false_when_dirty_and_user_declines()
    {
        // Why: dirty form cancellation must require explicit confirmation.
        var dialog = new TestDialogService { ConfirmResult = false };
        var vm = new ClipMontageFormViewModel(new FakeApiClient(), dialog)
        {
            StreamerNamesText = "streamer"
        };

        var accepted = vm.HandleCancelRequest();

        Assert.False(accepted);
    }

    [Fact]
    public async Task Submit_valid_payload_raises_submitted_event()
    {
        // Why: submit flow should provide created job id for navigation.
        var fakeApi = new FakeApiClient
        {
            ClipSubmitFactory = _ => Task.FromResult(new JobSubmitResponseDto { JobId = "clip-job" }),
        };
        var vm = new ClipMontageFormViewModel(fakeApi, new TestDialogService())
        {
            StreamerNamesText = "ninja",
            CurrentVideosDir = "videos"
        };

        string? submitted = null;
        vm.Submitted += id => submitted = id;

        vm.SubmitCommand.Execute(null);
        await Task.Delay(50);

        Assert.Equal("clip-job", submitted);
    }

    [Fact]
    public void Validate_negative_optional_values_sets_boundary_errors()
    {
        // Why: optional numeric tunables must reject negative values.
        var vm = new ClipMontageFormViewModel(new FakeApiClient(), new TestDialogService())
        {
            StreamerNamesText = "ninja",
            CurrentVideosDir = "videos",
            MaxClips = -1,
            ScrapePoolSize = -1,
            PerStreamerK = -1,
        };

        vm.Validate();

        Assert.True(vm.HasValidationErrors);
        Assert.Contains(vm.ValidationErrors, error => error.Contains("Max clips", StringComparison.Ordinal));
        Assert.Contains(vm.ValidationErrors, error => error.Contains("Scrape pool size", StringComparison.Ordinal));
        Assert.Contains(vm.ValidationErrors, error => error.Contains("Per streamer K", StringComparison.Ordinal));
    }

    [Fact]
    public void Apply_prefill_sets_clip_fields()
    {
        // Why: rerun prefill should restore both streamers and current-videos path.
        var vm = new ClipMontageFormViewModel(new FakeApiClient(), new TestDialogService());

        vm.ApplyPrefill(new Dictionary<string, string>
        {
            ["streamer_names"] = "ninja, shroud",
            ["current_videos_dir"] = "currentVideos",
        });

        Assert.Equal("ninja, shroud", vm.StreamerNamesText);
        Assert.Equal("currentVideos", vm.CurrentVideosDir);
    }

    [Fact]
    public async Task Submit_network_failure_sets_network_alert()
    {
        // Why: transient connectivity failures should produce deterministic user feedback.
        var signal = new TaskCompletionSource();
        var fakeApi = new FakeApiClient
        {
            ClipSubmitFactory = _ =>
            {
                signal.TrySetResult();
                throw new HttpRequestException("offline");
            },
        };
        var vm = new ClipMontageFormViewModel(fakeApi, new TestDialogService())
        {
            StreamerNamesText = "ninja",
            CurrentVideosDir = "videos",
        };

        vm.SubmitCommand.Execute(null);
        await signal.Task;
        await WaitUntilAsync(() => !vm.IsSubmitting);

        Assert.Equal("Network error while submitting clip montage job.", vm.FormAlert);
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

        throw new TimeoutException("Timed out waiting for command completion.");
    }
}
