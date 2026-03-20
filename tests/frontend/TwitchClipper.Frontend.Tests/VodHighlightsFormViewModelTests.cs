/*
Test Plan
- Partitions: valid submit, invalid submit, API validation error mapping
- Boundaries: empty required fields, min numeric constraints
- Failure modes: API validation response and blocked submit
# Covers: UI-IMPL-044
*/

using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;
using TwitchClipper.Desktop.ViewModels;
using TwitchClipper.Frontend.Tests.TestDoubles;
using System.Net.Http;

namespace TwitchClipper.Frontend.Tests;

public class VodHighlightsFormViewModelTests
{
    [Fact]
    public void Validate_with_missing_required_fields_sets_errors()
    {
        // Why: required fields must block submit before API call.
        var vm = new VodHighlightsFormViewModel(new FakeApiClient(), new TestDialogService())
        {
            VodUrl = "",
            OutputDir = "",
        };

        vm.Validate();

        Assert.True(vm.HasValidationErrors);
        Assert.False(vm.CanSubmit);
    }

    [Fact]
    public async Task Submit_with_valid_payload_raises_submitted_event()
    {
        // Why: successful submit should route app to queue via job id.
        var fakeApi = new FakeApiClient
        {
            VodSubmitFactory = _ => Task.FromResult(new JobSubmitResponseDto { JobId = "job-123" }),
        };
        var vm = new VodHighlightsFormViewModel(fakeApi, new TestDialogService())
        {
            VodUrl = "https://www.twitch.tv/videos/123",
            OutputDir = "vod_output",
        };

        string? submitted = null;
        vm.Submitted += jobId => submitted = jobId;

        vm.SubmitCommand.Execute(null);
        await Task.Delay(50);

        Assert.Equal("job-123", submitted);
        Assert.False(vm.HasValidationErrors);
    }

    [Fact]
    public async Task Submit_maps_api_validation_errors()
    {
        // Why: 422 should surface explicit field-level messages.
        var fakeApi = new FakeApiClient
        {
            VodSubmitFactory = _ => throw new ApiException(
                System.Net.HttpStatusCode.UnprocessableEntity,
                "Validation failed.",
                [new ApiValidationError { Field = "body.vod_url", Message = "Field required" }]),
        };
        var vm = new VodHighlightsFormViewModel(fakeApi, new TestDialogService())
        {
            VodUrl = "bad",
            OutputDir = "out",
        };

        vm.SubmitCommand.Execute(null);
        await Task.Delay(50);

        Assert.True(vm.HasValidationErrors);
        Assert.Contains(vm.ValidationErrors, err => err.Contains("Field required", StringComparison.Ordinal));
    }

    [Fact]
    public void Reset_defaults_restores_safe_numeric_defaults()
    {
        // Why: reset action should always restore conservative baseline settings.
        var vm = new VodHighlightsFormViewModel(new FakeApiClient(), new TestDialogService())
        {
            MinCount = 11,
            SpikeWindowSeconds = 9,
            SegmentPaddingSeconds = 0,
            MaxSegmentSeconds = 15,
            DiversityWindows = 2,
        };

        vm.ResetDefaults();

        Assert.Equal(3, vm.MinCount);
        Assert.Equal(30, vm.SpikeWindowSeconds);
        Assert.Equal(12, vm.SegmentPaddingSeconds);
        Assert.Equal(120, vm.MaxSegmentSeconds);
        Assert.Equal(8, vm.DiversityWindows);
    }

    [Fact]
    public void Apply_prefill_sets_vod_and_output_directory()
    {
        // Why: rerun prefill must hydrate core fields without requiring manual re-entry.
        var vm = new VodHighlightsFormViewModel(new FakeApiClient(), new TestDialogService());

        vm.ApplyPrefill(new Dictionary<string, string>
        {
            ["vod_url"] = "https://www.twitch.tv/videos/999",
            ["output_dir"] = "vod_output",
        });

        Assert.Equal("https://www.twitch.tv/videos/999", vm.VodUrl);
        Assert.Equal("vod_output", vm.OutputDir);
    }

    [Fact]
    public async Task Submit_network_failure_sets_network_alert()
    {
        // Why: network outage should present explicit retry guidance.
        var signal = new TaskCompletionSource();
        var fakeApi = new FakeApiClient
        {
            VodSubmitFactory = _ =>
            {
                signal.TrySetResult();
                throw new HttpRequestException("offline");
            },
        };
        var vm = new VodHighlightsFormViewModel(fakeApi, new TestDialogService())
        {
            VodUrl = "https://www.twitch.tv/videos/123",
            OutputDir = "vod_output",
        };

        vm.SubmitCommand.Execute(null);
        await signal.Task;
        await WaitUntilAsync(() => !vm.IsSubmitting);

        Assert.Equal("Network error while submitting VOD job.", vm.FormAlert);
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
