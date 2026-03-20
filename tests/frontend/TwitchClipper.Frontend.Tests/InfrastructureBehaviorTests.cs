/*
Test Plan
- Partitions: command execute/can-execute behavior, navigation eventing, converter transforms
- Boundaries: same-screen navigation, non-boolean converter input, empty validation location list
- Failure modes: async command re-entry protection and fallback conversion behavior
# Covers: UI-IMPL-051
*/

using System.Globalization;
using System.Text.Json;
using System.Windows;
using TwitchClipper.Desktop.Commands;
using TwitchClipper.Desktop.Converters;
using TwitchClipper.Desktop.Models;
using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Frontend.Tests;

public class InfrastructureBehaviorTests
{
    [Fact]
    public async Task Async_command_blocks_reentry_during_execution()
    {
        // Why: async command must prevent duplicate submits while an operation is active.
        var gate = new TaskCompletionSource();
        var started = new TaskCompletionSource();
        var executions = 0;
        var command = new AsyncRelayCommand(async _ =>
        {
            Interlocked.Increment(ref executions);
            started.TrySetResult();
            await gate.Task;
        });

        command.Execute(null);
        await started.Task;
        var canExecuteWhileRunning = command.CanExecute(null);
        command.Execute(null);
        gate.SetResult();
        await Task.Yield();

        Assert.False(canExecuteWhileRunning);
        Assert.Equal(1, executions);
    }

    [Fact]
    public void Relay_command_respects_can_execute_and_runs_action()
    {
        // Why: command binding predicates are critical for enable/disable UI states.
        var executed = false;
        var command = new RelayCommand(_ => executed = true, _ => true);

        var canExecute = command.CanExecute(null);
        command.Execute(null);

        Assert.True(canExecute);
        Assert.True(executed);
    }

    [Fact]
    public void Navigation_service_emits_only_for_actual_screen_changes()
    {
        // Why: duplicate events on same-screen navigation would trigger unnecessary reloads.
        var nav = new NavigationService();
        var events = new List<AppScreen>();
        nav.ScreenChanged += (_, screen) => events.Add(screen);

        nav.NavigateTo(AppScreen.Dashboard);
        nav.NavigateTo(AppScreen.NewVod);

        Assert.Single(events);
        Assert.Equal(AppScreen.NewVod, events[0]);
    }

    [Fact]
    public void Inverse_boolean_converter_handles_bool_and_fallback_inputs()
    {
        // Why: converter fallback path protects bindings with unexpected runtime values.
        var converter = new InverseBooleanToVisibilityConverter();
        var culture = CultureInfo.InvariantCulture;

        var visible = converter.Convert(false, typeof(Visibility), null!, culture);
        var collapsed = converter.Convert(true, typeof(Visibility), null!, culture);
        var fallback = converter.Convert("not-a-bool", typeof(Visibility), null!, culture);
        var convertBack = converter.ConvertBack(Visibility.Visible, typeof(bool), null!, culture);

        Assert.Equal(Visibility.Visible, visible);
        Assert.Equal(Visibility.Collapsed, collapsed);
        Assert.Equal(Visibility.Visible, fallback);
        Assert.Equal(false, convertBack);
    }

    [Fact]
    public void Validation_error_detail_maps_only_string_location_segments()
    {
        // Why: mixed-type location arrays should still produce stable field mapping.
        var detail = new ApiValidationErrorDetail
        {
            Loc =
            [
                JsonSerializer.SerializeToElement("body"),
                JsonSerializer.SerializeToElement(0),
                JsonSerializer.SerializeToElement("vod_url")
            ],
            Msg = "invalid",
        };

        var mapped = detail.ToMappedError();

        Assert.Equal("body.vod_url", mapped.Field);
        Assert.Equal("invalid", mapped.Message);
    }

    [Fact]
    public void Path_opener_rejects_empty_path_with_clear_message()
    {
        // Why: empty output path should fail safely before shell invocation.
        var opener = new PathOpener();

        var ok = opener.TryOpenPath(null, out var error);

        Assert.False(ok);
        Assert.Equal("No output path is available for this job.", error);
    }

    [Fact]
    public void Path_opener_rejects_nonexistent_path_with_clear_message()
    {
        // Why: missing files should report access issue and avoid process launch.
        var opener = new PathOpener();

        var ok = opener.TryOpenPath("Z:/definitely-not-real/path.mp4", out var error);

        Assert.False(ok);
        Assert.Equal("The output path does not exist or cannot be accessed.", error);
    }
}
