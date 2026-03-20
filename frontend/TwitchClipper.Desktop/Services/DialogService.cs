using System.Windows;

namespace TwitchClipper.Desktop.Services;

public interface IDialogService
{
    bool ConfirmDiscardChanges();

    void ShowInfo(string message, string title = "TwitchClipper");

    void ShowError(string message, string title = "TwitchClipper");
}

public sealed class DialogService : IDialogService
{
    public bool ConfirmDiscardChanges()
    {
        var result = MessageBox.Show(
            "Discard unsaved changes?",
            "Confirm",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning);
        return result == MessageBoxResult.Yes;
    }

    public void ShowInfo(string message, string title = "TwitchClipper")
    {
        MessageBox.Show(message, title, MessageBoxButton.OK, MessageBoxImage.Information);
    }

    public void ShowError(string message, string title = "TwitchClipper")
    {
        MessageBox.Show(message, title, MessageBoxButton.OK, MessageBoxImage.Error);
    }
}
