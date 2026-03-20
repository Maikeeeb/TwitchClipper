using TwitchClipper.Desktop.Services;

namespace TwitchClipper.Frontend.Tests.TestDoubles;

public sealed class TestDialogService : IDialogService
{
    public bool ConfirmResult { get; set; } = true;

    public bool ConfirmDiscardChanges() => ConfirmResult;

    public void ShowInfo(string message, string title = "TwitchClipper")
    {
    }

    public void ShowError(string message, string title = "TwitchClipper")
    {
    }
}
